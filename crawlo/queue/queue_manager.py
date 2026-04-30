#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一的队列管理器

提供简洁、一致的队列接口，自动处理不同队列类型的差异。

重新设计的队列和背压系统：
- 支持多种队列类型：内存、Redis
- 内置背压控制机制
- 统一的接口设计
"""
import asyncio
import time
import traceback
from typing import Optional, Dict, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo import Request

from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo.queue.queue_types import QueueType
from crawlo.queue.config import QueueConfig
from crawlo.queue.intelligent_scheduler import IntelligentScheduler
from crawlo.utils.error_handler import ErrorHandler
from crawlo.logging import get_logger
from crawlo.utils.request.request_serializer import RequestSerializer
from crawlo.utils.misc import safe_get_config

try:
    # 使用完整版Redis队列
    from crawlo.queue.redis_priority_queue import RedisPriorityQueue

    REDIS_AVAILABLE = True
except ImportError:
    RedisPriorityQueue = None
    REDIS_AVAILABLE = False


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
        
        # 初始化新的背压策略系统
        from crawlo.backpressure import (
            BackpressureController,
            QueueSizeStrategy,
            BackpressureStrategyConfig
        )
        
        # 获取背压策略类型配置
        strategy_type = safe_get_config(
            self.config.settings,
            'BACKPRESSURE_STRATEGY',
            'queue_size'
        )
        
        # 创建策略配置
        bp_config = BackpressureStrategyConfig(
            threshold=config.backpressure_ratio,
            base_delay=config.backpressure_delay_base,
            max_delay=config.backpressure_delay_max,
        )
        
        # 根据配置创建对应策略
        if strategy_type == 'adaptive':
            from crawlo.backpressure import AdaptiveStrategy
            strategy = AdaptiveStrategy(config=bp_config)
        elif strategy_type == 'composite':
            from crawlo.backpressure import CompositeStrategy
            strategy = CompositeStrategy([
                QueueSizeStrategy(config=bp_config)
            ])
        else:  # 默认使用queue_size策略
            strategy = QueueSizeStrategy(config=bp_config)
        
        # 创建背压控制器
        self._backpressure_controller = BackpressureController(
            strategy=strategy,
            enabled=True
        )
        
        self._backpressure_strategy_type = strategy_type

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
            
            # 输出背压策略初始化信息（仅在未重新创建时输出，避免与 recreated 日志重复）
            if hasattr(self, '_backpressure_controller') and self._backpressure_controller:
                # 检查是否是重新创建过的（通过比较 config 和 controller 的配置是否一致）
                config_ratio = self.config.backpressure_ratio
                controller_ratio = self._backpressure_controller._strategy._config.threshold
                
                if abs(config_ratio - controller_ratio) < 0.001:  # 配置一致，说明可能被 recreated 过
                    # 配置一致，但仍需输出关键信息（INFO 级别）
                    self.logger.info(
                        f"Backpressure initialized with strategy: {self._backpressure_strategy_type} "
                        f"(threshold: {self._backpressure_controller._strategy._config.threshold:.0%}, "
                        f"base_delay: {self._backpressure_controller._strategy._config.base_delay}s, "
                        f"max_delay: {self._backpressure_controller._strategy._config.max_delay}s)"
                    )
                else:
                    # 配置不一致，说明已经被 recreated 过，详细日志已在 recreated 中输出
                    self.logger.debug(
                        f"Backpressure initialized with strategy: {self._backpressure_strategy_type} "
                        f"(threshold: {self._backpressure_controller._strategy._config.threshold:.0%})"
                    )

            # 如果健康检查返回True，表示队列类型发生了切换，需要更新配置
            if health_check_result:
                return True

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
            
            # 获取配置的最大队列大小
            max_size = self.config.max_queue_size if hasattr(self, 'config') else 1000
            
            # ===== 硬限制：队列满时拒绝请求 =====
            if current_queue_size >= max_size:
                self.logger.warning(
                    f"Queue full ({current_queue_size}/{max_size}), "
                    f"rejecting request: {request.url}"
                )
                return False
            
            # ===== 软限制：队列超过阈值时延迟入队 =====
            if hasattr(self, '_backpressure_controller') and self._backpressure_controller.enabled:
                # 使用新的背压策略系统检查是否需要应用背压
                if await self._backpressure_controller.should_apply(self):
                    # 计算背压延迟
                    delay = await self._backpressure_controller.calculate_delay(self)
                    
                    if delay > 0:
                        # 记录背压激活日志（仅在状态变更时）
                        if not self._backpressure_controller.active:
                            metrics = await self._backpressure_controller.get_metrics(self)
                            self.logger.info(
                                f"Backpressure activated: queue={metrics.queue_size}/{metrics.max_queue_size} "
                                f"(utilization: {metrics.utilization:.0%}, delay: {delay:.2f}s, "
                                f"level: {metrics.level.value})"
                            )
                        
                        # 应用背压延迟
                        self.logger.debug(
                            f"Backpressure delay: {delay:.2f}s "
                            f"(queue={current_queue_size}/{max_size})"
                        )
                        await asyncio.sleep(delay)

            # 背压控制（仅对内存队列）
            if self._queue_semaphore:
                # 对于大量请求，使用阻塞式等待而不是跳过
                # 这样可以确保不会丢失任何请求
                await self._queue_semaphore.acquire()

            # 统一的入队操作
            success = False
            # 使用明确的类型检查来确定调用哪个方法
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
    
    @property
    def max_size(self) -> int:
        """返回最大队列大小（IQueue接口）"""
        return self.config.max_queue_size

    def empty(self) -> bool:
        """Check if queue is empty (synchronous version, for compatibility)
        
        对于 Redis 队列使用保守策略返回 False，避免 Engine 过早退出。
        上层应通过 async_empty() 获取精确结果。
        """
        try:
            # 对于内存队列，可以同步检查
            if self._queue and self._queue_type == QueueType.MEMORY:
                # 确保正确检查队列大小
                if hasattr(self._queue, 'qsize'):
                    return self._queue.qsize() == 0
                else:
                    # 如果没有qsize方法，假设队列为空
                    return True
            # 对于 Redis 队列：无法同步确定，使用保守策略返回 False
            # 防止 Engine._exit() 同步检查时误判为空闲而过早退出
            return False
        except Exception:
            return False

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
        if hasattr(self, '_backpressure_controller') and self._backpressure_controller:
            performance_stats.update(self._backpressure_controller.get_stats())
        
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
        if hasattr(self, '_backpressure_controller') and self._backpressure_controller:
            stats['backpressure_status'] = self._backpressure_controller.get_stats()
        
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
                    test_queue = RedisPriorityQueue(
                        redis_url=self.config.redis_url,
                        project_name="default"
                    )
                    await test_queue.connect()
                    await test_queue.close()
                    self.logger.info("Auto-detection: Redis available, using Redis queue")
                    # 重要：AUTO模式检测到Redis后，更新背压配置为Redis配置
                    self._apply_redis_backpressure_config()
                    return QueueType.REDIS
                except Exception as e:
                    self.logger.info(f"Auto-detection: Redis unavailable ({e}), falling back to memory queue")
                    # 重要：AUTO模式Redis不可用时，更新背压配置为Memory配置
                    self._apply_memory_backpressure_config()
                    return QueueType.MEMORY
            else:
                self.logger.info("Auto-detection: Redis not configured, using memory queue")
                # 重要：AUTO模式无Redis配置时，更新背压配置为Memory配置
                self._apply_memory_backpressure_config()
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
            # RedisPriorityQueue 已在文件顶部导入
            if not REDIS_AVAILABLE:
                raise RuntimeError(f"Redis队列不可用：未能导入RedisPriorityQueue")

            # 统一使用RedisKeyManager.from_settings来解析项目名称和爬虫名称
            project_name = "default"
            spider_name = None
            
            if hasattr(self.config, 'settings') and self.config.settings:
                try:
                    from crawlo.utils.redis import RedisKeyManager
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
                # 重要：更新背压配置为Memory配置
                self._apply_memory_backpressure_config()
                self._queue_semaphore = asyncio.Semaphore(self.config.max_queue_size)
                self._health_status = "healthy"
                self.logger.info("Switched to memory queue with memory backpressure config")
                # 返回一个信号，表示需要更新过滤器和去重管道配置
                return True
        return False

    def _apply_redis_backpressure_config(self):
        """应用Redis队列的背压配置（用于AUTO模式）"""
        from crawlo.utils.misc import safe_get_config
        
        settings = self.config.settings if hasattr(self.config, 'settings') and self.config.settings else {}
        
        # 更新QueueConfig的背压参数为Redis配置
        self.config.max_queue_size = safe_get_config(
            settings, 'REDIS_SCHEDULER_MAX_QUEUE_SIZE',
            safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 50000), int
        )
        self.config.backpressure_ratio = safe_get_config(
            settings, 'REDIS_BACKPRESSURE_RATIO',
            safe_get_config(settings, 'BACKPRESSURE_RATIO', 0.6)
        )
        self.config.backpressure_delay_base = safe_get_config(
            settings, 'REDIS_BACKPRESSURE_DELAY_BASE',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_BASE', 0.5)
        )
        self.config.backpressure_delay_max = safe_get_config(
            settings, 'REDIS_BACKPRESSURE_DELAY_MAX',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_MAX', 5.0)
        )
        
        # 更新extra_config中的阈值
        if hasattr(self.config, 'extra_config') and self.config.extra_config:
            self.config.extra_config['backpressure_warning_threshold'] = safe_get_config(
                settings, 'REDIS_BACKPRESSURE_WARNING_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_WARNING_THRESHOLD', 0.5)
            )
            self.config.extra_config['backpressure_critical_threshold'] = safe_get_config(
                settings, 'REDIS_BACKPRESSURE_CRITICAL_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_CRITICAL_THRESHOLD', 0.8)
            )
        
        self.logger.debug(
            f"Applied Redis backpressure config: "
            f"max_size={self.config.max_queue_size}, "
            f"ratio={self.config.backpressure_ratio}, "
            f"delay_base={self.config.backpressure_delay_base}s, "
            f"delay_max={self.config.backpressure_delay_max}s"
        )
        
        # 重要：重新创建背压控制器以应用新配置
        self._recreate_backpressure_controller()

    def _apply_memory_backpressure_config(self):
        """应用内存队列的背压配置（用于AUTO模式）"""
        from crawlo.utils.misc import safe_get_config
        
        settings = self.config.settings if hasattr(self.config, 'settings') and self.config.settings else {}
        
        # 更新QueueConfig的背压参数为Memory配置
        self.config.max_queue_size = safe_get_config(
            settings, 'MEMORY_SCHEDULER_MAX_QUEUE_SIZE',
            safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 5000), int
        )
        self.config.backpressure_ratio = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_RATIO',
            safe_get_config(settings, 'BACKPRESSURE_RATIO', 0.8)
        )
        self.config.backpressure_delay_base = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_DELAY_BASE',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_BASE', 0.2)
        )
        self.config.backpressure_delay_max = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_DELAY_MAX',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_MAX', 2.0)
        )
        
        # 更新extra_config中的阈值
        if hasattr(self.config, 'extra_config') and self.config.extra_config:
            self.config.extra_config['backpressure_warning_threshold'] = safe_get_config(
                settings, 'MEMORY_BACKPRESSURE_WARNING_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_WARNING_THRESHOLD', 0.7)
            )
            self.config.extra_config['backpressure_critical_threshold'] = safe_get_config(
                settings, 'MEMORY_BACKPRESSURE_CRITICAL_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_CRITICAL_THRESHOLD', 0.9)
            )
        
        self.logger.debug(
            f"Applied Memory backpressure config: "
            f"max_size={self.config.max_queue_size}, "
            f"ratio={self.config.backpressure_ratio}, "
            f"delay_base={self.config.backpressure_delay_base}s, "
            f"delay_max={self.config.backpressure_delay_max}s"
        )
        
        # 重要：重新创建背压控制器以应用新配置
        self._recreate_backpressure_controller()

    def _recreate_backpressure_controller(self):
        """
        重新创建背压控制器以应用更新后的配置
        
        当AUTO模式检测到Redis可用或不可用时，会更新self.config的背压参数，
        需要重新创建背压控制器才能使新配置生效。
        """
        from crawlo.backpressure import (
            BackpressureController,
            QueueSizeStrategy,
            BackpressureStrategyConfig
        )
        
        # 获取背压策略类型配置
        strategy_type = safe_get_config(
            self.config.settings,
            'BACKPRESSURE_STRATEGY',
            'queue_size'
        )
        
        # 使用更新后的配置创建新的策略配置
        bp_config = BackpressureStrategyConfig(
            threshold=self.config.backpressure_ratio,
            base_delay=self.config.backpressure_delay_base,
            max_delay=self.config.backpressure_delay_max,
        )
        
        # 根据配置创建对应策略
        if strategy_type == 'adaptive':
            from crawlo.backpressure import AdaptiveStrategy
            strategy = AdaptiveStrategy(config=bp_config)
        elif strategy_type == 'composite':
            from crawlo.backpressure import CompositeStrategy
            strategy = CompositeStrategy([
                QueueSizeStrategy(config=bp_config)
            ])
        else:  # 默认使用queue_size策略
            strategy = QueueSizeStrategy(config=bp_config)
        
        # 创建新的背压控制器
        self._backpressure_controller = BackpressureController(
            strategy=strategy,
            enabled=True
        )
        
        self._backpressure_strategy_type = strategy_type
        
        self.logger.info(
            f"Backpressure controller recreated with strategy: {strategy_type} "
            f"(threshold: {bp_config.threshold:.0%}, "
            f"base_delay: {bp_config.base_delay}s, "
            f"max_delay: {bp_config.max_delay}s)"
        )

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


