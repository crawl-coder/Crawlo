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
from typing import Optional, Dict, Any, Union, TYPE_CHECKING

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
        self.response_times = {}  # 响应时间统计
        self.error_counts = {}  # 错误计数
        self.content_type_preferences = {}  # 内容类型偏好
        self.crawl_frequency = {}  # 抓取频率统计

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

        # 基于响应时间调整优先级
        if domain in self.response_times:
            avg_response_time = sum(self.response_times[domain]) / len(self.response_times[domain])
            # 如果响应时间较长，适当降低优先级
            if avg_response_time > 5.0:  # 超过5秒
                priority -= 1
            elif avg_response_time < 1.0:  # 响应很快，提高优先级
                priority += 1

        # 基于错误计数调整优先级
        if domain in self.error_counts and self.error_counts[domain] > 3:
            # 如果错误较多，降低优先级
            priority -= min(self.error_counts[domain], 5)

        # 基于内容类型偏好调整优先级
        content_type = getattr(request, 'meta', {}).get('content_type', '')
        if content_type in ['html', 'json', 'xml']:
            # 这些内容类型通常更重要，提高优先级
            priority += 1

        # 基于抓取频率调整优先级
        if domain in self.crawl_frequency:
            freq_info = self.crawl_frequency[domain]
            if 'last_hour_count' in freq_info and freq_info['last_hour_count'] > 100:
                # 如果过去一小时抓取过多，降低优先级
                priority -= 1

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

    def update_response_time(self, request: "Request", response_time: float):
        """更新响应时间统计"""
        domain = self._extract_domain(request.url)
        if domain not in self.response_times:
            self.response_times[domain] = []
        self.response_times[domain].append(response_time)
        # 只保留最近10次响应时间
        if len(self.response_times[domain]) > 10:
            self.response_times[domain] = self.response_times[domain][-10:]

    def update_error_count(self, request: "Request", has_error: bool = True):
        """更新错误计数"""
        domain = self._extract_domain(request.url)
        if domain not in self.error_counts:
            self.error_counts[domain] = 0
        if has_error:
            self.error_counts[domain] += 1
        else:
            # 成功时减少错误计数
            self.error_counts[domain] = max(0, self.error_counts[domain] - 1)

    def update_crawl_frequency(self, request: "Request"):
        """更新抓取频率统计"""
        domain = self._extract_domain(request.url)
        if domain not in self.crawl_frequency:
            self.crawl_frequency[domain] = {'last_hour_count': 0, 'last_update': time.time()}
        
        current_time = time.time()
        # 每小时重置计数器
        if current_time - self.crawl_frequency[domain]['last_update'] > 3600:
            self.crawl_frequency[domain]['last_hour_count'] = 0
            self.crawl_frequency[domain]['last_update'] = current_time
        
        self.crawl_frequency[domain]['last_hour_count'] += 1

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
            redis_user: Optional[str] = None,  # 新增：Redis用户名
            redis_db: int = 0,
            queue_name: str = "crawlo:requests",
            max_queue_size: int = 1000,
            max_retries: int = 3,
            timeout: int = 300,
            run_mode: Optional[str] = None,  # 新增：运行模式
            settings=None,  # 新增：保存settings引用
            serialization_format: str = 'pickle',  # 新增：序列化格式
            **kwargs
    ):
        self.queue_type = QueueType(queue_type) if isinstance(queue_type, str) else queue_type
        self.run_mode = run_mode  # 保存运行模式
        self.settings = settings  # 保存settings引用
        self.serialization_format = serialization_format  # 新增：保存序列化格式

        # Redis 配置
        if redis_url:
            self.redis_url = redis_url
        else:
            # 根据是否有用户名和密码构建URL
            if redis_user and redis_password:
                # 包含用户名和密码的格式
                self.redis_url = f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            elif redis_password:
                # 仅包含密码的格式（标准Redis认证）
                self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                # 无认证格式
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
        redis_user = safe_get_config(settings, 'REDIS_USER')  # 获取用户名配置
        run_mode = safe_get_config(settings, 'RUN_MODE')
        
        # 获取整数配置
        redis_port = safe_get_config(settings, 'REDIS_PORT', 6379, int)
        redis_db = safe_get_config(settings, 'REDIS_DB', 0, int)
        max_queue_size = safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 1000, int)
        max_retries = safe_get_config(settings, 'QUEUE_MAX_RETRIES', 3, int)
        timeout = safe_get_config(settings, 'QUEUE_TIMEOUT', 300, int)
        
        # 新增：获取序列化格式配置
        serialization_format = safe_get_config(settings, 'SERIALIZATION_FORMAT', 'pickle')
        
        return cls(
            queue_type=queue_type,
            redis_url=redis_url,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            redis_user=redis_user,
            redis_db=redis_db,
            queue_name=queue_name,
            max_queue_size=max_queue_size,
            max_retries=max_retries,
            timeout=timeout,
            run_mode=run_mode,
            settings=settings,  # 传递settings
            serialization_format=serialization_format  # 新增：传递序列化格式
        )


class QueueManager:
    """Unified queue manager"""

    def __init__(self, config: QueueConfig):
        self.config = config
        # 延迟初始化logger和error_handler避免循环依赖
        self._logger = None
        self._error_handler = None
        # 使用配置的序列化格式初始化RequestSerializer
        self.request_serializer = RequestSerializer(serialization_format=config.serialization_format)
        self._queue = None
        self._queue_semaphore = None
        self._queue_type = None
        self._health_status = "unknown"
        self._intelligent_scheduler = IntelligentScheduler()  # 智能调度器
        
        # 初始化背压控制
        self._backpressure_controller = BackPressureController(
            max_queue_size=config.max_queue_size,
            backpressure_ratio=getattr(config, 'backpressure_ratio', 0.8),
            concurrency_limit=getattr(config, 'max_concurrency', 8)
        )

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

            # 获取当前队列大小用于背压控制
            current_queue_size = await self.size() if self._queue else 0
            
            # 更新背压控制器的统计信息
            if hasattr(self, '_backpressure_controller'):
                # 获取当前并发数（模拟，实际需要从task_manager获取）
                current_concurrency = 0  # 这里需要根据实际情况获取
                self._backpressure_controller.update_stats(current_queue_size, current_concurrency)
                
                # 检查是否需要应用背压
                if self._backpressure_controller.should_apply_backpressure(current_queue_size, current_concurrency):
                    # 获取背压延迟时间
                    delay = self._backpressure_controller.get_backpressure_delay()
                    if delay > 0:
                        self.logger.debug(f"应用背压控制，延迟 {delay} 秒")
                        await asyncio.sleep(delay)

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
        status = {
            "type": self._queue_type.value if self._queue_type else "unknown",
            "health": self._health_status,
            "config": self._get_queue_info(),
            "initialized": self._queue is not None
        }
        
        # 添加性能统计信息
        performance_stats = {}
        if hasattr(self, '_backpressure_controller'):
            performance_stats.update(self._backpressure_controller.get_status())
        
        status['performance'] = performance_stats
        return status

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列性能统计信息
        
        Returns:
            dict: 队列性能统计信息
        """
        stats = {
            'queue_type': self._queue_type.value if self._queue_type else 'unknown',
            'health_status': self._health_status,
            'current_queue_size': 0,
            'max_queue_size': self.config.max_queue_size,
            'backpressure_status': {},
            'intelligent_scheduler_stats': {}
        }
        
        # 获取队列大小
        try:
            if self._queue:
                if hasattr(self._queue, 'qsize'):
                    if asyncio.iscoroutinefunction(self._queue.qsize):
                        # 异步获取队列大小
                        async def get_size():
                            return await self._queue.qsize()
                        # 注意：这里不能直接调用异步函数，需要在适当上下文中使用
                        stats['current_queue_size'] = 'async_required'  # 需要在异步上下文中获取
                    else:
                        stats['current_queue_size'] = self._queue.qsize()
                elif hasattr(self._queue, '__len__'):
                    stats['current_queue_size'] = len(self._queue)
        except Exception:
            stats['current_queue_size'] = 'error'
        
        # 获取背压控制器状态
        if hasattr(self, '_backpressure_controller'):
            stats['backpressure_status'] = self._backpressure_controller.get_status()
        
        # 获取智能调度器统计信息
        if hasattr(self, '_intelligent_scheduler'):
            stats['intelligent_scheduler_stats'] = {
                'domain_count': len(getattr(self._intelligent_scheduler, 'domain_stats', {})),
                'url_count': len(getattr(self._intelligent_scheduler, 'url_stats', {})),
                'response_time_count': len(getattr(self._intelligent_scheduler, 'response_times', {})),
                'error_count': len(getattr(self._intelligent_scheduler, 'error_counts', {})),
                'crawl_frequency_count': len(getattr(self._intelligent_scheduler, 'crawl_frequency', {}))
            }
        
        # 如果队列是Redis队列，获取其统计信息
        if self._queue_type == QueueType.REDIS and hasattr(self._queue, 'get_stats'):
            try:
                redis_stats = self._queue.get_stats()
                stats['redis_queue_stats'] = redis_stats
            except Exception:
                stats['redis_queue_stats'] = 'error'
        
        # 添加背压控制器的详细状态
        if hasattr(self, '_backpressure_controller'):
            back_pressure_stats = {
                'back_pressure_status': {
                    'enabled': True,
                    'current_threshold': self._backpressure_controller.backpressure_ratio,
                    'max_concurrency': self._backpressure_controller.concurrency_limit,
                    'current_concurrency': self._backpressure_controller.current_concurrency,
                    'last_adjustment_time': getattr(self._backpressure_controller, 'last_check_time', 0),
                    'pressure_level': 'high' if self._backpressure_controller.backpressure_active else 'normal'
                }
            }
            stats.update(back_pressure_stats)
        
        # 添加智能调度器的详细统计信息
        if hasattr(self, '_intelligent_scheduler'):
            intelligent_stats = {
                'intelligent_scheduler_stats_detail': {
                    'domain_frequencies': dict(getattr(self._intelligent_scheduler, 'domain_stats', {})),
                    'url_patterns': dict(getattr(self._intelligent_scheduler, 'url_stats', {})),
                    'crawl_depths': {},  # 爬取深度统计（如果有的话）
                    'response_times': dict(getattr(self._intelligent_scheduler, 'response_times', {})),
                    'error_counts': dict(getattr(self._intelligent_scheduler, 'error_counts', {})),
                    'content_type_preferences': dict(getattr(self._intelligent_scheduler, 'content_type_preferences', {}))
                }
            }
            stats.update(intelligent_stats)
        
        return stats

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
                serialization_format=self.config.serialization_format,  # 传递序列化格式
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


class BackPressureController:
    """
    背压控制器
    用于实现更精细的背压控制机制
    """
    
    def __init__(self, max_queue_size: int = 1000, backpressure_ratio: float = 0.8, concurrency_limit: int = 8):
        """
        初始化背压控制器
        
        Args:
            max_queue_size: 最大队列大小
            backpressure_ratio: 触发背压的比例
            concurrency_limit: 并发限制
        """
        self.max_queue_size = max_queue_size
        self.backpressure_ratio = backpressure_ratio
        self.concurrency_limit = concurrency_limit
        self.current_queue_size = 0
        self.current_concurrency = 0
        self.backpressure_active = False
        self.last_check_time = 0
        self.check_interval = 0.1  # 检查间隔（秒）
        
        # 统计信息
        self.throttling_events = 0
        self.recovery_events = 0
    
    def should_apply_backpressure(self, current_queue_size: int = None, current_concurrency: int = None) -> bool:
        """
        判断是否需要应用背压
        
        Args:
            current_queue_size: 当前队列大小
            current_concurrency: 当前并发数
            
        Returns:
            bool: 是否需要应用背压
        """
        import time
        current_time = time.time()
        
        # 限制检查频率
        if current_time - self.last_check_time < self.check_interval:
            return self.backpressure_active
        
        self.last_check_time = current_time
        
        # 使用传入的值或当前值
        queue_size = current_queue_size if current_queue_size is not None else self.current_queue_size
        concurrency = current_concurrency if current_concurrency is not None else self.current_concurrency
        
        # 计算队列使用率
        queue_utilization = queue_size / self.max_queue_size if self.max_queue_size > 0 else 0
        
        # 判断是否需要应用背压
        should_throttle = (
            queue_utilization >= self.backpressure_ratio or  # 队列使用率过高
            concurrency >= self.concurrency_limit  # 并发数过高
        )
        
        if should_throttle and not self.backpressure_active:
            # 开始背压控制
            self.backpressure_active = True
            self.throttling_events += 1
        elif not should_throttle and self.backpressure_active:
            # 恢复正常状态
            self.backpressure_active = False
            self.recovery_events += 1
        
        return self.backpressure_active
    
    def get_backpressure_delay(self) -> float:
        """
        获取背压延迟时间
        
        Returns:
            float: 延迟时间（秒）
        """
        if not self.backpressure_active:
            return 0.0
        
        # 根据队列使用率计算延迟时间
        queue_utilization = self.current_queue_size / self.max_queue_size if self.max_queue_size > 0 else 0
        base_delay = 0.01  # 基础延迟
        
        # 队列越满，延迟越大
        if queue_utilization > 0.95:
            return base_delay * 10  # 队列接近满时大幅增加延迟
        elif queue_utilization > 0.9:
            return base_delay * 5   # 队列很满时增加延迟
        elif queue_utilization > 0.85:
            return base_delay * 2   # 队列较满时小幅增加延迟
        else:
            return base_delay       # 正常延迟
    
    def update_stats(self, queue_size: int, concurrency: int):
        """
        更新统计信息
        
        Args:
            queue_size: 当前队列大小
            concurrency: 当前并发数
        """
        self.current_queue_size = queue_size
        self.current_concurrency = concurrency
    
    def get_status(self) -> dict:
        """
        获取背压控制器状态
        
        Returns:
            dict: 状态信息
        """
        return {
            'backpressure_active': self.backpressure_active,
            'queue_utilization': self.current_queue_size / self.max_queue_size if self.max_queue_size > 0 else 0,
            'throttling_events': self.throttling_events,
            'recovery_events': self.recovery_events,
            'recommended_delay': self.get_backpressure_delay(),
            'current_queue_size': self.current_queue_size,
            'max_queue_size': self.max_queue_size
        }
