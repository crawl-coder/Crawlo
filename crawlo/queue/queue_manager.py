#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一的队列管理器
提供简洁、一致的队列接口，自动处理不同队列类型的差异
"""
import asyncio
import time
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Union, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from crawlo import Request

from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo.utils.error_handler import ErrorHandler
from crawlo.logging import get_logger
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
            run_mode: Optional[str] = None,  # 新增：运行模式
            settings=None,  # 新增：保存settings引用
            **kwargs
    ):
        self.queue_type = QueueType(queue_type) if isinstance(queue_type, str) else queue_type
        self.run_mode = run_mode  # 保存运行模式
        self.settings = settings  # 保存settings引用

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
        from crawlo.utils.misc import safe_get_config
        
        # 安全获取项目名称，用于生成默认队列名称
        project_name = safe_get_config(settings, 'PROJECT_NAME', 'default')
        default_queue_name = f"crawlo:{project_name}:queue:requests"
        
        # 安全获取队列名称
        queue_name = safe_get_config(settings, 'SCHEDULER_QUEUE_NAME', default_queue_name)
        
        # 安全获取其他配置参数
        queue_type = safe_get_config(settings, 'QUEUE_TYPE', QueueType.AUTO)
        redis_url = safe_get_config(settings, 'REDIS_URL')
        redis_host = safe_get_config(settings, 'REDIS_HOST', '127.0.0.1')
        redis_password = safe_get_config(settings, 'REDIS_PASSWORD')
        run_mode = safe_get_config(settings, 'RUN_MODE')
        
        # 获取整数配置
        redis_port = safe_get_config(settings, 'REDIS_PORT', 6379, int)
        redis_db = safe_get_config(settings, 'REDIS_DB', 0, int)
        max_queue_size = safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 1000, int)
        max_retries = safe_get_config(settings, 'QUEUE_MAX_RETRIES', 3, int)
        timeout = safe_get_config(settings, 'QUEUE_TIMEOUT', 300, int)
        
        return cls(
            queue_type=queue_type,
            redis_url=redis_url,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            redis_db=redis_db,
            queue_name=queue_name,
            max_queue_size=max_queue_size,
            max_retries=max_retries,
            timeout=timeout,
            run_mode=run_mode,
            settings=settings  # 传递settings
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

        except RuntimeError as e:
            # Distributed 模式下的 RuntimeError 必须重新抛出
            if self.config.run_mode == 'distributed':
                self.logger.error(f"Queue initialization failed: {e}")
                self._health_status = "error"
                raise  # 重新抛出异常
            # 其他模式记录错误但不抛出
            self.logger.error(f"Queue initialization failed: {e}")
            self.logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
            self._health_status = "error"
            return False
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
            success = False
            # 使用明确的类型检查来确定调用哪个方法
            from crawlo.queue.redis_priority_queue import RedisPriorityQueue
            if isinstance(self._queue, RedisPriorityQueue):
                # Redis队列需要两个参数
                success = await self._queue.put(request, final_priority)
            else:
                # 对于内存队列，我们需要手动处理优先级
                # 在SpiderPriorityQueue中，元素应该是(priority, item)的元组
                await self._queue.put((final_priority, request))
                success = True

            if success:
                self.logger.debug(f"Request enqueued successfully: {request.url} with priority {final_priority}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to enqueue request: {e}")
            if self._queue_semaphore:
                self._queue_semaphore.release()
            return False

    async def get(self) -> Optional["Request"]:
        """Unified dequeue interface"""
        if not self._queue:
            raise RuntimeError("队列未初始化")

        try:
            # 内存队列使用0.01秒的超时，Redis队列使用较短的超时时间
            # 不再使用配置的超时时间，避免长时间等待
            timeout = 0.01 if self._queue_type == QueueType.MEMORY else 0.01
            result = await self._queue.get(timeout=timeout)

            # 释放信号量（仅对内存队列）
            if self._queue_semaphore and result:
                self._queue_semaphore.release()

            # 反序列化处理（仅对 Redis 队列）
            if result and self._queue_type == QueueType.REDIS:
                # 这里需要 spider 实例，暂时返回原始请求
                # 实际的 callback 恢复在 scheduler 中处理
                # 确保返回类型是Request或None
                if hasattr(result, 'url'):  # 简单检查是否为Request对象
                    return result
                else:
                    return None

            # 如果是内存队列，需要解包(priority, request)元组
            if result and self._queue_type == QueueType.MEMORY:
                if isinstance(result, tuple) and len(result) == 2:
                    request_obj = result[1]  # 取元组中的请求对象
                    # 确保返回类型是Request或None
                    if hasattr(request_obj, 'url'):  # 简单检查是否为Request对象
                        return request_obj
                    else:
                        return None

            return None
        except Exception as e:
            self.logger.error(f"Failed to dequeue request: {e}")
            return None

    async def size(self) -> int:
        """Get queue size"""
        if not self._queue:
            return 0

        try:
            if hasattr(self._queue, 'qsize'):
                qsize_func = self._queue.qsize
                if asyncio.iscoroutinefunction(qsize_func):
                    result = await qsize_func()  # type: ignore
                    # 确保结果是整数
                    if isinstance(result, int):
                        return result
                    else:
                        return int(str(result))
                else:
                    result = qsize_func()
                    # 确保结果是整数
                    if isinstance(result, int):
                        return result
                    else:
                        return int(str(result))
            return 0
        except Exception as e:
            self.logger.warning(f"Failed to get queue size: {e}")
            return 0

    def empty(self) -> bool:
        """Check if queue is empty (synchronous version, for compatibility)"""
        try:
            # 对于内存队列，可以同步检查
            if self._queue and self._queue_type == QueueType.MEMORY:
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
            if self._queue and self._queue_type == QueueType.MEMORY:
                # 确保正确检查队列大小
                if hasattr(self._queue, 'qsize'):
                    if asyncio.iscoroutinefunction(self._queue.qsize):
                        size = await self._queue.qsize()  # type: ignore
                    else:
                        size = self._queue.qsize()
                    return size == 0
                else:
                    # 如果没有qsize方法，假设队列为空
                    return True
            # 对于 Redis 队列，使用异步检查
            elif self._queue and self._queue_type == QueueType.REDIS:
                # 对于 Redis 队列，使用异步检查
                # 直接使用Redis队列的qsize方法，它会同时检查主队列和处理中队列
                from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                if isinstance(self._queue, RedisPriorityQueue):
                    try:
                        size = await self._queue.qsize()
                        is_empty = size == 0
                        return is_empty
                    except Exception:
                        # 检查失败，回退到只检查主队列大小
                        size = await self.size()
                        is_empty = size == 0
                        return is_empty
                else:
                    size = await self.size()
                    is_empty = size == 0
                    return is_empty
            return True
        except Exception as e:
            self.logger.error(f"检查队列是否为空时出错: {e}")
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
                    test_queue = RedisPriorityQueue(
                        redis_url=self.config.redis_url,
                        project_name="default"
                    )
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
            # Distributed 模式：必须使用 Redis，不允许降级
            if self.config.run_mode == 'distributed':
                # 分布式模式必须确保 Redis 可用
                if not REDIS_AVAILABLE:
                    error_msg = (
                        "Distributed 模式要求 Redis 可用，但 Redis 客户端库未安装。\n"
                        "请安装 Redis 支持: pip install redis"
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                if not self.config.redis_url:
                    error_msg = (
                        "Distributed 模式要求配置 Redis 连接信息。\n"
                        "请在 settings.py 中配置 REDIS_HOST、REDIS_PORT 等参数"
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                # 测试 Redis 连接
                try:
                    from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                    test_queue = RedisPriorityQueue(
                        redis_url=self.config.redis_url,
                        project_name="default"
                    )
                    await test_queue.connect()
                    await test_queue.close()
                    self.logger.debug("Distributed mode: Redis connection verified")
                    return QueueType.REDIS
                except Exception as e:
                    error_msg = (
                        f"Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。\n"
                        f"错误信息: {e}\n"
                        f"Redis URL: {self.config.redis_url}\n"
                        f"请检查：\n"
                        f"  1. Redis 服务是否正在运行\n"
                        f"  2. Redis 连接配置是否正确\n"
                        f"  3. 网络连接是否正常"
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg) from e
            else:
                # 非 distributed 模式：QUEUE_TYPE='redis' 时允许降级到 memory
                # 这提供了向后兼容性和更好的容错性
                if REDIS_AVAILABLE and self.config.redis_url:
                    # 测试 Redis 连接
                    try:
                        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                        test_queue = RedisPriorityQueue(
                            redis_url=self.config.redis_url,
                            project_name="default"
                        )
                        await test_queue.connect()
                        await test_queue.close()
                        self.logger.debug("Redis mode: Redis available, using distributed queue")
                        return QueueType.REDIS
                    except Exception as e:
                        self.logger.warning(f"Redis mode: Redis unavailable ({e}), falling back to memory queue")
                        return QueueType.MEMORY
                else:
                    self.logger.warning("Redis mode: Redis not configured, falling back to memory queue")
                    return QueueType.MEMORY

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

            # 统一使用RedisKeyManager.from_settings来解析项目名称和爬虫名称
            project_name = "default"
            spider_name = None
            
            if hasattr(self.config, 'settings') and self.config.settings:
                try:
                    from crawlo.utils.redis_manager import RedisKeyManager
                    key_manager = RedisKeyManager.from_settings(self.config.settings)
                    project_name = key_manager.project_name
                    spider_name = key_manager.spider_name
                except Exception as e:
                    self.logger.warning(f"无法从配置中解析项目名称和爬虫名称: {e}")
                    # 回退到默认值
                    project_name = "default"
                    spider_name = None
            
            # 如果没有从extra_config获取到，尝试从settings中获取
            if not spider_name and hasattr(self.config, 'settings') and self.config.settings:
                try:
                    spider_name = self.config.settings.get('SPIDER_NAME', None)
                except Exception:
                    pass

            queue = RedisPriorityQueue(
                redis_url=self.config.redis_url,
                queue_name=None,  # 不再使用config.queue_name，让RedisPriorityQueue自动生成
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
                project_name=project_name,  # 使用解析后的project_name参数
                spider_name=spider_name,    # 使用解析后的spider_name参数
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
            if self._queue_type == QueueType.REDIS and self._queue:
                # 测试 Redis 连接
                # 使用明确的类型检查确保只对Redis队列调用connect方法
                from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                if isinstance(self._queue, RedisPriorityQueue):
                    await self._queue.connect()
                self._health_status = "healthy"
            else:
                # 内存队列总是健康的
                self._health_status = "healthy"
                return False  # 内存队列不需要更新配置
        except Exception as e:
            self.logger.warning(f"Queue health check failed: {e}")
            self._health_status = "unhealthy"
            
            # Distributed 模式下 Redis 健康检查失败应该报错
            if self.config.run_mode == 'distributed':
                error_msg = (
                    f"Distributed 模式下 Redis 健康检查失败。\n"
                    f"错误信息: {e}\n"
                    f"Redis URL: {self.config.redis_url}\n"
                    f"分布式模式不允许降级到内存队列，请修复 Redis 连接问题。"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            
            # 非 Distributed 模式：如果是Redis队列且健康检查失败，尝试切换到内存队列
            # 对于 AUTO 模式允许回退
            if self._queue_type == QueueType.REDIS and self.config.queue_type == QueueType.AUTO:
                self.logger.info("Redis queue unavailable, attempting to switch to memory queue...")
                try:
                    if self._queue:
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