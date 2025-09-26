#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一的队列管理器
提供简洁、一致的队列接口，自动处理不同队列类型的差异
"""
import asyncio
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
import time
import random

if TYPE_CHECKING:
    from crawlo import Request

from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo.utils.error_handler import ErrorHandler
from crawlo.utils.log import get_logger
from crawlo.utils.request_serializer import RequestSerializer

try:
    # 使用完整版Redis队列
    from crawlo.queue.redis_priority_queue import RedisPriorityQueue

    REDIS_AVAILABLE = True
except ImportError:
    RedisPriorityQueue = None
    REDIS_AVAILABLE = False


class QueueType(Enum):
    """Queue type enumeration"""
    MEMORY = "memory"
    REDIS = "redis"
    AUTO = "auto"  # 自动选择


class IntelligentScheduler:
    """智能调度器"""

    def __init__(self):
        self.domain_stats = {}  # 域名统计信息
        self.url_stats = {}  # URL统计信息
        self.last_request_time = {}  # 最后请求时间

    def calculate_priority(self, request: "Request") -> int:
        """计算请求的智能优先级"""
        priority = getattr(request, 'priority', 0)

        # 获取域名
        domain = self._extract_domain(request.url)

        # 基于域名访问频率调整优先级
        if domain in self.domain_stats:
            domain_access_count = self.domain_stats[domain]['count']
            last_access_time = self.domain_stats[domain]['last_time']

            # 如果最近访问过该域名，降低优先级（避免过度集中访问同一域名）
            time_since_last = time.time() - last_access_time
            if time_since_last < 5:  # 5秒内访问过
                priority -= 2
            elif time_since_last < 30:  # 30秒内访问过
                priority -= 1

            # 如果该域名访问次数过多，进一步降低优先级
            if domain_access_count > 10:
                priority -= 1

        # 基于URL访问历史调整优先级
        if request.url in self.url_stats:
            url_access_count = self.url_stats[request.url]
            if url_access_count > 1:
                # 重复URL降低优先级
                priority -= url_access_count

        # 基于深度调整优先级
        depth = getattr(request, 'meta', {}).get('depth', 0)
        priority -= depth  # 深度越大，优先级越低

        return priority

    def update_stats(self, request: "Request"):
        """更新统计信息"""
        domain = self._extract_domain(request.url)

        # 更新域名统计
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {'count': 0, 'last_time': 0}

        self.domain_stats[domain]['count'] += 1
        self.domain_stats[domain]['last_time'] = time.time()

        # 更新URL统计
        if request.url not in self.url_stats:
            self.url_stats[request.url] = 0
        self.url_stats[request.url] += 1

        # 更新最后请求时间
        self.last_request_time[domain] = time.time()

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"


class QueueConfig:
    """Queue configuration class"""

    def __init__(
            self,
            queue_type: Union[QueueType, str] = QueueType.AUTO,
            redis_url: Optional[str] = None,
            redis_host: str = "127.0.0.1",
            redis_port: int = 6379,
            redis_password: Optional[str] = None,
            redis_db: int = 0,
            queue_name: str = "crawlo:requests",
            max_queue_size: int = 1000,
            max_retries: int = 3,
            timeout: int = 300,
            **kwargs
    ):
        self.queue_type = QueueType(queue_type) if isinstance(queue_type, str) else queue_type

        # Redis 配置
        if redis_url:
            self.redis_url = redis_url
        else:
            if redis_password:
                self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        self.queue_name = queue_name
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.extra_config = kwargs

    @classmethod
    def from_settings(cls, settings) -> 'QueueConfig':
        """Create configuration from settings"""
        # 获取项目名称，用于生成默认队列名称
        project_name = settings.get('PROJECT_NAME', 'default')
        default_queue_name = f"crawlo:{project_name}:queue:requests"
        
        # 如果设置了SCHEDULER_QUEUE_NAME，则使用该值，否则使用基于项目名称的默认值
        scheduler_queue_name = settings.get('SCHEDULER_QUEUE_NAME')
        if scheduler_queue_name is not None:
            queue_name = scheduler_queue_name
        else:
            queue_name = default_queue_name
        
        return cls(
            queue_type=settings.get('QUEUE_TYPE', QueueType.AUTO),
            redis_url=settings.get('REDIS_URL'),
            redis_host=settings.get('REDIS_HOST', '127.0.0.1'),
            redis_port=settings.get_int('REDIS_PORT', 6379),
            redis_password=settings.get('REDIS_PASSWORD'),
            redis_db=settings.get_int('REDIS_DB', 0),
            queue_name=queue_name,
            max_queue_size=settings.get_int('SCHEDULER_MAX_QUEUE_SIZE', 1000),
            max_retries=settings.get_int('QUEUE_MAX_RETRIES', 3),
            timeout=settings.get_int('QUEUE_TIMEOUT', 300)
        )


class QueueManager:
    """Unified queue manager"""

    def __init__(self, config: QueueConfig):
        self.config = config
        # 延迟初始化logger和error_handler避免循环依赖
        self._logger = None
        self._error_handler = None
        self.request_serializer = RequestSerializer()
        self._queue = None
        self._queue_semaphore = None
        self._queue_type = None
        self._health_status = "unknown"
        self._intelligent_scheduler = IntelligentScheduler()  # 智能调度器

    @property
    def logger(self):
        if self._logger is None:
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

    @property
    def error_handler(self):
        if self._error_handler is None:
            self._error_handler = ErrorHandler(self.__class__.__name__)
        return self._error_handler

    async def initialize(self) -> bool:
        """初始化队列"""
        try:
            queue_type = await self._determine_queue_type()
            self._queue = await self._create_queue(queue_type)
            self._queue_type = queue_type

            # 测试队列健康状态
            health_check_result = await self._health_check()

            self.logger.info(f"Queue initialized successfully Type: {queue_type.value}")
            # 只在调试模式下输出详细配置信息
            self.logger.debug(f"Queue configuration: {self._get_queue_info()}")

            # 如果健康检查返回True，表示队列类型发生了切换，需要更新配置
            if health_check_result:
                return True

            # 如果队列类型是Redis，检查是否需要更新配置
            if queue_type == QueueType.REDIS:
                # 这个检查需要在调度器中进行，因为队列管理器无法访问crawler.settings
                # 但我们不需要总是返回True，只有在确实需要更新时才返回True
                # 调度器会进行更详细的检查
                pass

            return False  # 默认不需要更新配置

        except Exception as e:
            # 记录详细的错误信息和堆栈跟踪
            self.logger.error(f"Queue initialization failed: {e}")
            self.logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
            self._health_status = "error"
            return False

    async def put(self, request: "Request", priority: int = 0) -> bool:
        """Unified enqueue interface"""
        if not self._queue:
            raise RuntimeError("队列未初始化")

        try:
            # 应用智能调度算法计算优先级
            intelligent_priority = self._intelligent_scheduler.calculate_priority(request)
            # 结合原始优先级和智能优先级
            final_priority = priority + intelligent_priority

            # 更新统计信息
            self._intelligent_scheduler.update_stats(request)

            # 序列化处理（仅对 Redis 队列）
            if self._queue_type == QueueType.REDIS:
                request = self.request_serializer.prepare_for_serialization(request)

            # 背压控制（仅对内存队列）
            if self._queue_semaphore:
                # 对于大量请求，使用阻塞式等待而不是跳过
                # 这样可以确保不会丢失任何请求
                await self._queue_semaphore.acquire()

            # 统一的入队操作
            if hasattr(self._queue, 'put'):
                if self._queue_type == QueueType.REDIS:
                    success = await self._queue.put(request, final_priority)
                else:
                    # 对于内存队列，我们需要手动处理优先级
                    # 在SpiderPriorityQueue中，元素应该是(priority, item)的元组
                    await self._queue.put((final_priority, request))
                    success = True
            else:
                raise RuntimeError(f"队列类型 {self._queue_type} 不支持 put 操作")

            if success:
                self.logger.debug(f"Request enqueued successfully: {request.url} with priority {final_priority}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to enqueue request: {e}")
            if self._queue_semaphore:
                self._queue_semaphore.release()
            return False

    async def get(self, timeout: float = 5.0) -> Optional["Request"]:
        """Unified dequeue interface"""
        if not self._queue:
            raise RuntimeError("队列未初始化")

        try:
            request = await self._queue.get(timeout=timeout)

            # 释放信号量（仅对内存队列）
            if self._queue_semaphore and request:
                self._queue_semaphore.release()

            # 反序列化处理（仅对 Redis 队列）
            if request and self._queue_type == QueueType.REDIS:
                # 这里需要 spider 实例，暂时返回原始请求
                # 实际的 callback 恢复在 scheduler 中处理
                pass

            # 如果是内存队列，需要解包(priority, request)元组
            if request and self._queue_type == QueueType.MEMORY:
                if isinstance(request, tuple) and len(request) == 2:
                    request = request[1]  # 取元组中的请求对象

            return request

        except Exception as e:
            self.logger.error(f"Failed to dequeue request: {e}")
            return None

    async def size(self) -> int:
        """Get queue size"""
        if not self._queue:
            return 0

        try:
            if hasattr(self._queue, 'qsize'):
                if asyncio.iscoroutinefunction(self._queue.qsize):
                    return await self._queue.qsize()
                else:
                    return self._queue.qsize()
            return 0
        except Exception as e:
            self.logger.warning(f"Failed to get queue size: {e}")
            return 0

    def empty(self) -> bool:
        """Check if queue is empty (synchronous version, for compatibility)"""
        try:
            # 对于内存队列，可以同步检查
            if self._queue_type == QueueType.MEMORY:
                # 确保正确检查队列大小
                if hasattr(self._queue, 'qsize'):
                    return self._queue.qsize() == 0
                else:
                    # 如果没有qsize方法，假设队列为空
                    return True
            # 对于 Redis 队列，由于需要异步操作，这里返回近似值
            # 为了确保程序能正常退出，我们返回True，让上层通过更精确的异步检查来判断
            return True
        except Exception:
            return True

    async def async_empty(self) -> bool:
        """Check if queue is empty (asynchronous version, more accurate)"""
        try:
            # 对于内存队列
            if self._queue_type == QueueType.MEMORY:
                # 确保正确检查队列大小
                if hasattr(self._queue, 'qsize'):
                    if asyncio.iscoroutinefunction(self._queue.qsize):
                        size = await self._queue.qsize()
                    else:
                        size = self._queue.qsize()
                    return size == 0
                else:
                    # 如果没有qsize方法，假设队列为空
                    return True
            # 对于 Redis 队列，使用异步检查
            elif self._queue_type == QueueType.REDIS:
                size = await self.size()
                return size == 0
            return True
        except Exception:
            return True

    async def close(self) -> None:
        """Close queue"""
        if self._queue and hasattr(self._queue, 'close'):
            try:
                await self._queue.close()
                # Change INFO level log to DEBUG level to avoid redundant output
                self.logger.debug("Queue closed")
            except Exception as e:
                self.logger.warning(f"Error closing queue: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        return {
            "type": self._queue_type.value if self._queue_type else "unknown",
            "health": self._health_status,
            "config": self._get_queue_info(),
            "initialized": self._queue is not None
        }

    async def _determine_queue_type(self) -> QueueType:
        """Determine queue type"""
        if self.config.queue_type == QueueType.AUTO:
            # 自动选择：优先使用 Redis（如果可用）
            if REDIS_AVAILABLE and self.config.redis_url:
                # 测试 Redis 连接
                try:
                    from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                    test_queue = RedisPriorityQueue(self.config.redis_url)
                    await test_queue.connect()
                    await test_queue.close()
                    self.logger.debug("Auto-detection: Redis available, using distributed queue")
                    return QueueType.REDIS
                except Exception as e:
                    self.logger.debug(f"Auto-detection: Redis unavailable ({e}), using memory queue")
                    return QueueType.MEMORY
            else:
                self.logger.debug("Auto-detection: Redis not configured, using memory queue")
                return QueueType.MEMORY

        elif self.config.queue_type == QueueType.REDIS:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis 队列不可用：未安装 redis 依赖")
            if not self.config.redis_url:
                raise RuntimeError("Redis 队列不可用：未配置 REDIS_URL")
            # 测试 Redis 连接
            try:
                from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                test_queue = RedisPriorityQueue(self.config.redis_url)
                await test_queue.connect()
                await test_queue.close()
                return QueueType.REDIS
            except Exception as e:
                # 如果强制使用Redis但连接失败，则抛出异常
                raise RuntimeError(f"Redis 队列不可用：无法连接到 Redis ({e})")

        elif self.config.queue_type == QueueType.MEMORY:
            return QueueType.MEMORY

        else:
            raise ValueError(f"不支持的队列类型: {self.config.queue_type}")

    async def _create_queue(self, queue_type: QueueType):
        """Create queue instance"""
        if queue_type == QueueType.REDIS:
            # 延迟导入Redis队列
            try:
                from crawlo.queue.redis_priority_queue import RedisPriorityQueue
            except ImportError as e:
                raise RuntimeError(f"Redis队列不可用：未能导入RedisPriorityQueue ({e})")

            # 修复项目名称提取逻辑，严格按照测试文件中的逻辑实现
            project_name = "default"
            if ':' in self.config.queue_name:
                parts = self.config.queue_name.split(':')
                if len(parts) >= 2:
                    # 处理可能的双重 crawlo 前缀
                    if parts[0] == "crawlo" and parts[1] == "crawlo":
                        # 双重 crawlo 前缀，取"crawlo"作为项目名称
                        project_name = "crawlo"
                    elif parts[0] == "crawlo":
                        # 正常的 crawlo 前缀，取第二个部分作为项目名称
                        project_name = parts[1]
                    else:
                        # 没有 crawlo 前缀，使用第一个部分作为项目名称
                        project_name = parts[0]
                else:
                    project_name = self.config.queue_name or "default"
            else:
                project_name = self.config.queue_name or "default"

            queue = RedisPriorityQueue(
                redis_url=self.config.redis_url,
                queue_name=self.config.queue_name,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
                module_name=project_name  # 传递项目名称作为module_name
            )
            # 不需要立即连接，使用 lazy connect
            return queue

        elif queue_type == QueueType.MEMORY:
            queue = SpiderPriorityQueue()
            # 为内存队列设置背压控制
            self._queue_semaphore = asyncio.Semaphore(self.config.max_queue_size)
            return queue

        else:
            raise ValueError(f"不支持的队列类型: {queue_type}")

    async def _health_check(self) -> bool:
        """Health check"""
        try:
            if self._queue_type == QueueType.REDIS:
                # 测试 Redis 连接
                await self._queue.connect()
                self._health_status = "healthy"
            else:
                # 内存队列总是健康的
                self._health_status = "healthy"
                return False  # 内存队列不需要更新配置
        except Exception as e:
            self.logger.warning(f"Queue health check failed: {e}")
            self._health_status = "unhealthy"
            # 如果是Redis队列且健康检查失败，尝试切换到内存队列
            if self._queue_type == QueueType.REDIS and self.config.queue_type == QueueType.AUTO:
                self.logger.info("Redis queue unavailable, attempting to switch to memory queue...")
                try:
                    await self._queue.close()
                except:
                    pass
                self._queue = None
                # 重新创建内存队列
                self._queue = await self._create_queue(QueueType.MEMORY)
                self._queue_type = QueueType.MEMORY
                self._queue_semaphore = asyncio.Semaphore(self.config.max_queue_size)
                self._health_status = "healthy"
                self.logger.info("Switched to memory queue")
                # 返回一个信号，表示需要更新过滤器和去重管道配置
                return True
        return False

    def _get_queue_info(self) -> Dict[str, Any]:
        """Get queue configuration information"""
        info = {
            "queue_name": self.config.queue_name,
            "max_queue_size": self.config.max_queue_size
        }

        if self._queue_type == QueueType.REDIS:
            info.update({
                "redis_url": self.config.redis_url,
                "max_retries": self.config.max_retries,
                "timeout": self.config.timeout
            })

        return info
