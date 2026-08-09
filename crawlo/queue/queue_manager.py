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
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from crawlo import Request

from crawlo.queue.backends.memory import SpiderPriorityQueue
from crawlo.queue.queue_types import QueueType
from crawlo.queue.config import QueueConfig
from crawlo.queue.priority_calculator import PriorityCalculator
from crawlo.utils.errors import ErrorHandler
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.queue.exceptions import QueueFullTimeout

try:
    # 使用完整版Redis队列
    from crawlo.queue.backends.redis_priority import RedisPriorityQueue
    from crawlo.queue.backends.redis_stream import RedisStreamQueue

    REDIS_AVAILABLE = True
except ImportError:
    RedisPriorityQueue = None
    RedisStreamQueue = None
    REDIS_AVAILABLE = False


from crawlo.queue.queue_status import QueueStatusMixin
from crawlo.queue.queue_backpressure import QueueBackpressureMixin


class QueueManager(QueueStatusMixin, QueueBackpressureMixin):
    """Unified queue manager"""

    def __init__(self, config: QueueConfig):
        self.config = config
        # 延迟初始化logger和error_handler避免循环依赖
        self._logger = None
        self._error_handler = None
        self._queue = None
        self._queue_semaphore = None
        self._queue_type = None
        self._health_status = "unknown"
        self._priority_calculator = PriorityCalculator()  # 优先级计算器
        # Phase 2：队列不满的条件变量，put 阻塞等待 / get 唤醒
        # 替代原 Scheduler 层的 _queue_not_full，统一由 QueueManager 管理
        self._queue_not_full = asyncio.Condition()
        # Phase 2：正在阻塞等待入队的请求数（防死锁：idle 判定需检查此值）
        # 若 > 0 表示有 put 在 block 等待，Engine 不应提前退出
        self._pending_enqueue_count = 0
        
        # 初始化新的背压策略系统
        from crawlo.queue.backpressure import (
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
            from crawlo.queue.backpressure import AdaptiveStrategy
            strategy = AdaptiveStrategy(config=bp_config)
        elif strategy_type == 'composite':
            from crawlo.queue.backpressure import CompositeStrategy
            strategy = CompositeStrategy([
                QueueSizeStrategy(config=bp_config)
            ])
        else:  # 默认使用queue_size策略
            strategy = QueueSizeStrategy(config=bp_config)
        
        # 创建背压控制器（可选集成智能计算器增强精度）
        intelligent_calc = None
        if safe_get_config(self.config.settings, 'MEMORY_MONITOR_ENABLED', False, bool):
            try:
                from crawlo.queue.backpressure import IntelligentBackpressureCalculator
                intelligent_calc = IntelligentBackpressureCalculator(base_delay=0.5)
            except ImportError:
                pass

        self._backpressure_controller = BackpressureController(
            strategy=strategy,
            enabled=True,
            intelligent_calculator=intelligent_calc,
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

            # Test queue health status
            health_check_result = await self._health_check()

            # Only output queue init log in debug mode to avoid noise
            self.logger.debug(f"Queue initialized successfully Type: {queue_type.value}")
            # Output detailed config in debug mode
            self.logger.debug(f"Queue configuration: {self._get_queue_info()}")

            # B-08：打印 dedup filter + dedup pipeline 信息（排障 2 行就能确认三模式配置）
            self._log_dedup_config()
            
            # Backpressure initialization log is already output in _recreate_backpressure_controller()
            # Skip duplicate log here to avoid redundancy

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

    async def put(self, request: "Request", priority: int = 0, *, timeout: Optional[float] = None) -> bool:
        """Unified enqueue interface

        Phase 2：队列满时阻塞等待，超时抛 ``QueueFullTimeout``。
        把"丢弃"从隐式 ``return False`` 变成显式异常，由调用方（Scheduler）按
        ``ENQUEUE_FULL_POLICY`` 决策。

        Args:
            request: 请求对象
            priority: 优先级
            timeout: 阻塞等待超时（秒）。``None`` = 无限等待；超时抛 ``QueueFullTimeout``。

        Returns:
            True 表示入队成功

        Raises:
            QueueFullTimeout: 队列满且等待超时
            RuntimeError: 队列未初始化
        """
        if not self._queue:
            raise RuntimeError("队列未初始化")

        semaphore_acquired = False  # 跟踪信号量状态

        try:
            # 应用智能调度算法计算优先级
            # 分布式模式下跳过：Domain throttle 由 DistributedRateLimiter 处理，
            # PriorityCalculator 的负值修正会将所有请求路由到高优 Stream
            if self._queue_type == QueueType.REDIS_STREAM:
                final_priority = priority
            else:
                intelligent_priority = self._priority_calculator.calculate_priority(request)
                final_priority = priority + intelligent_priority

            # 更新统计信息
            self._priority_calculator.update_stats(request)

            # 获取当前队列大小用于背压控制
            current_queue_size = await self.size() if self._queue else 0

            # 获取配置的最大队列大小
            max_size = self.config.max_queue_size if hasattr(self, 'config') else 1000

            # ===== Phase 2：硬限制改为阻塞等待（替代原 return False）=====
            # 队列满时用 Condition 等待消费者腾出空间，超时抛 QueueFullTimeout
            if current_queue_size >= max_size:
                if not self._backpressure_controller.active:
                    self.logger.info(
                        f"Queue full ({current_queue_size}/{max_size}), "
                        f"blocking enqueue (timeout={timeout}): {request.url}"
                    )
                # Phase 2：标记有 put 在阻塞等待，防止 Engine 误判 idle 提前退出
                self._pending_enqueue_count += 1
                try:
                    waited = await self._wait_for_space(max_size, timeout)
                finally:
                    self._pending_enqueue_count -= 1
                if not waited:
                    raise QueueFullTimeout(
                        queue_name=self.config.queue_name,
                        waited_seconds=timeout if timeout is not None else 0.0,
                        queue_size=await self.size(),
                        max_size=max_size,
                    )
                # 重新获取队列大小（腾出空间后）
                current_queue_size = await self.size()

            # ===== 软限制：队列超过阈值时延迟入队（流量整形，非阻塞）=====
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

                        # 喂入实际延迟供自适应策略学习
                        if hasattr(self._backpressure_controller.strategy, 'record_delay'):
                            self._backpressure_controller.strategy.record_delay(delay)

            # 背压控制（仅对内存队列）
            if self._queue_semaphore:
                # 对于大量请求，使用阻塞式等待而不是跳过
                # 这样可以确保不会丢失任何请求
                await self._queue_semaphore.acquire()
                semaphore_acquired = True

            # 统一的入队操作
            success = False
            # 使用明确的类型检查来确定调用哪个方法
            if isinstance(self._queue, RedisStreamQueue):
                # Stream 队列：put(request, priority)
                success = await self._queue.put(request, final_priority)
            elif isinstance(self._queue, RedisPriorityQueue):
                # Redis队列需要两个参数（Request 对象，队列内部会序列化）
                success = await self._queue.put(request, final_priority)
            else:
                # 对于内存队列，我们需要手动处理优先级
                # 在SpiderPriorityQueue中，元素应该是(priority, item)的元组
                await self._queue.put((final_priority, request))
                success = True

            # 修复信号量泄漏：如果 put 返回 False（请求未真正入队），
            # 必须释放已 acquire 的信号量，否则会造成永久泄漏
            # （get 时不会 release，因为队列里没有对应元素）
            if not success and semaphore_acquired and self._queue_semaphore:
                try:
                    self._queue_semaphore.release()
                except ValueError:
                    pass

            return success

        except QueueFullTimeout:
            # 队列满超时：不在此处理，向上抛给 Scheduler 按 policy 决策
            raise
        except Exception as e:
            self.logger.error(f"Failed to enqueue request: {e}")
            # 只在已获取信号量时才释放
            if semaphore_acquired and self._queue_semaphore:
                try:
                    self._queue_semaphore.release()
                except ValueError:
                    pass
            return False

    async def _wait_for_space(self, max_size: int, timeout: Optional[float]) -> bool:
        """等待队列腾出空间。

        Phase 2：队列满时阻塞等待，由 ``get`` 成功取出后通过
        ``_notify_space_available`` 唤醒。

        Args:
            max_size: 队列最大容量
            timeout: 等待超时（秒）。``None`` = 无限等待。

        Returns:
            True 表示队列已有空位；False 表示超时。
        """
        start = time.monotonic()
        async with self._queue_not_full:
            while await self.size() >= max_size:
                if timeout is None:
                    await self._queue_not_full.wait()
                else:
                    elapsed = time.monotonic() - start
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        return False
                    try:
                        await asyncio.wait_for(self._queue_not_full.wait(), timeout=remaining)
                    except asyncio.TimeoutError:
                        # 超时后继续循环检查，可能刚好有空位
                        pass
            return True

    async def _notify_space_available(self) -> None:
        """通知所有等待入队的协程：队列有空间了。

        在 ``get`` / ``get_blocking`` 成功取出元素后调用，唤醒阻塞的 ``put``。
        """
        async with self._queue_not_full:
            self._queue_not_full.notify_all()

    async def get(self) -> Optional["Request"]:
        """Unified dequeue interface"""
        if not self._queue:
            raise RuntimeError("队列未初始化")

        try:
            # 修复：原 timeout = 0.01 if MEMORY else 0.01 两分支同值，简化为常量
            timeout = 0.01
            result = await self._queue.get(timeout=timeout)

            # 修复信号量泄漏：只要从队列取出元素（无论后续校验是否通过），
            # 都必须释放信号量。原实现只在 result 真值时 release，
            # 导致反序列化异常返回 None 时信号量永不释放。
            # 使用 try/finally 确保对称释放。
            if self._queue_semaphore and result is not None:
                try:
                    self._queue_semaphore.release()
                except ValueError:
                    # 信号量可能已被其他路径释放，忽略下溢
                    pass

            # Phase 2：成功取出元素后通知等待入队的 put（队列腾出了空间）
            if result is not None:
                await self._notify_space_available()

            # 反序列化处理（仅对 Redis 队列）
            if result and self._queue_type in (QueueType.REDIS, QueueType.REDIS_STREAM):
                # 这里需要 spider 实例，暂时返回原始请求
                # 实际的 callback 恢复在 scheduler 中处理
                # 确保返回类型是Request或None
                if hasattr(result, 'url'):  # 简单检查是否为Request对象
                    return result
                else:
                    # 无效结果，记录但不影响信号量（已释放）
                    self.logger.warning("Dequeued non-Request object from Redis queue, discarding")
                    return None

            # 如果是内存队列，需要解包(priority, request)元组
            if result and self._queue_type == QueueType.MEMORY:
                if isinstance(result, tuple) and len(result) == 2:
                    request_obj = result[1]  # 取元组中的请求对象
                    # 确保返回类型是Request或None
                    if hasattr(request_obj, 'url'):  # 简单检查是否为Request对象
                        return request_obj
                    else:
                        self.logger.warning("Dequeued non-Request object from memory queue, discarding")
                        return None

            return None
        except Exception as e:
            self.logger.error(f"Failed to dequeue request: {e}")
            return None

    async def get_blocking(self, timeout: float = 30.0) -> Optional["Request"]:
        """阻塞式获取（仅 Redis 队列支持，内存队列 fallback 到普通 get）"""
        if not self._queue:
            raise RuntimeError("队列未初始化")

        if self._queue_type in (QueueType.REDIS, QueueType.REDIS_STREAM) and hasattr(self._queue, 'get_blocking'):
            result = await self._queue.get_blocking(timeout=timeout)
            if result and hasattr(result, 'url'):
                # Phase 2：成功取出后通知等待入队的 put
                await self._notify_space_available()
                return result
            return None

        # 内存队列 fallback（get 内部已处理 notify）
        return await self.get()

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

    @property
    def pending_enqueue_count(self) -> int:
        """Phase 2：正在阻塞等待入队的请求数。

        Engine 的 idle 判定需检查此值：若 > 0 表示有 put 在 block 等待，
        Engine 不应提前退出（否则消费者停了 → 入队永远等不到消费 → 死锁）。
        """
        return self._pending_enqueue_count

    async def async_empty(self) -> bool:
        """Check if queue is empty (asynchronous version, more accurate)
        
        对于 Redis Stream：消费后消息不会被删除（由 maxlen 控制淘汰），
        因此必须使用后端的 empty() 方法，而不是 size()==0（xinfo_stream.length 返回历史总数）。
        """
        try:
            # 优先使用后端自带 empty() 实现（尤其是 Stream 需要特殊语义判断）
            if self._queue and hasattr(self._queue, 'empty') and callable(self._queue.empty):
                try:
                    res = self._queue.empty()
                    if hasattr(res, '__await__'):
                        return await res
                    return bool(res)
                except Exception:
                    pass  # 后端 empty() 出错，fallback 到 size 判断

            # 对于内存队列
            if self._queue and self._queue_type == QueueType.MEMORY:
                if hasattr(self._queue, 'size'):
                    size = await self._queue.size()
                    return size == 0
                return True
            # 对于 Redis 队列（ZSET），大小即未消费数；Stream 已在上方 empty() 分支处理
            elif self._queue and self._queue_type in (QueueType.REDIS, QueueType.REDIS_STREAM):
                size = await self.size()
                return size == 0
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

    # ------------------------------------------------------------------
    # 配置排障辅助：Dedup / Filter 信息打印（P3-B-08）
    # ------------------------------------------------------------------

    def _log_dedup_config(self) -> None:
        """
        打印当前生效的去重配置。
        让排障时一眼确认三模式配置（例如 Auto 模式是否真的切到了 AioRedisFilter）。
        """
        try:
            settings = self.config.settings or {}
            filter_cls = settings.get('FILTER_CLASS') if isinstance(settings, dict) else getattr(settings, 'FILTER_CLASS', None)
            dedup_pipe = settings.get('DEFAULT_DEDUP_PIPELINE') if isinstance(settings, dict) else getattr(settings, 'DEFAULT_DEDUP_PIPELINE', None)
            # 兜底也从 safe_get_config 里读（部分旧路径 settings 是 dict-like 对象需 dict 访问）
            if not filter_cls:
                filter_cls = safe_get_config(self.config.settings, 'FILTER_CLASS', None)
            if not dedup_pipe:
                dedup_pipe = safe_get_config(self.config.settings, 'DEFAULT_DEDUP_PIPELINE', None)

            # 判断是否跨运行持久化
            persistence_tag = "OFF (memory-only)"
            if filter_cls and ('Redis' in str(filter_cls) or 'redis' in str(filter_cls).lower()):
                persistence_tag = "ON (Redis-backed, cross-run dedup)"
            self.logger.info(
                f"Dedup filter:  {filter_cls or '<not configured>'}   (persistence={persistence_tag})"
            )

            pipe_persistence = "OFF (memory-only)"
            if dedup_pipe and ('Redis' in str(dedup_pipe) or 'redis' in str(dedup_pipe).lower()):
                pipe_persistence = "ON (Redis-backed)"
            self.logger.info(
                f"Dedup pipeline: {dedup_pipe or '<not configured>'}   (persistence={pipe_persistence})"
            )
        except Exception as e:
            # 日志辅助函数必须不影响主流程
            self.logger.debug(f"Log dedup config skipped: {e}")






    async def _test_redis_connection(self) -> bool:
        """测试 Redis 连接是否可用（纯 ping，不创建任何队列/stream/key）"""
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(self.config.redis_url, socket_connect_timeout=3)
            await r.ping()
            await r.aclose()
            return True
        except Exception:
            return False

    async def _determine_queue_type(self) -> QueueType:
        """Determine queue type"""
        if self.config.queue_type == QueueType.AUTO:
            # 自动选择：Redis 可用时使用 Redis ZSET 队列（与 master 分支行为一致）
            # ZSET 语义：消费完消息立即从集合移除 → empty 即空队列 → 完美匹配 auto 单机退出判断
            # Redis Stream 仅用于 distributed 模式（需要 Consumer Group / Pending / Claim 多 Worker 机制）
            if REDIS_AVAILABLE and self.config.redis_url:
                if await self._test_redis_connection():
                    self.logger.info(
                        "Queue type: redis (auto-detected, Redis available, ZSET queue)"
                    )
                    self._apply_redis_backpressure_config()
                    return QueueType.REDIS
                else:
                    self.logger.info("Queue type: memory (auto-detected, Redis unavailable)")
                    self._apply_memory_backpressure_config()
                    return QueueType.MEMORY
            else:
                self.logger.info("Queue type: memory (auto-detected, Redis not configured)")
                self._apply_memory_backpressure_config()
                return QueueType.MEMORY

        elif self.config.queue_type == QueueType.REDIS:
            if self.config.run_mode == 'distributed':
                # distributed 模式：用户显式 QUEUE_TYPE=redis，但 distributed 语义必须用 Stream
                # （因为 ZSET 无法做 pending 消息回收和多消费者分配）
                self.logger.info(
                    "Distributed mode: upgrading QUEUE_TYPE=redis → redis_stream "
                    "(Stream is required for multi-worker coordination & pending claim)"
                )
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
                if not await self._test_redis_connection():
                    error_msg = (
                        f"Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。\n"
                        f"Redis URL: {self.config.redis_url}\n"
                        f"请检查：\n"
                        f"  1. Redis 服务是否正在运行\n"
                        f"  2. Redis 连接配置是否正确\n"
                        f"  3. 网络连接是否正常"
                    )
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                self.logger.debug("Distributed mode: Redis connection verified")
                return QueueType.REDIS_STREAM
            else:
                if REDIS_AVAILABLE and self.config.redis_url:
                    if await self._test_redis_connection():
                        self.logger.debug("Redis mode: Redis available, using ZSET queue")
                        return QueueType.REDIS
                    else:
                        self.logger.warning("Redis mode: Redis unavailable, falling back to memory queue")
                        return QueueType.MEMORY
                else:
                    self.logger.warning("Redis mode: Redis not configured, falling back to memory queue")
                    return QueueType.MEMORY

        elif self.config.queue_type == QueueType.REDIS_STREAM:
            # 修复：移除调试残留 `or True` 恒真分支
            # REDIS_STREAM 模式对所有 run_mode 都要求 Redis 可用
            if not REDIS_AVAILABLE:
                error_msg = (
                    "REDIS_STREAM 模式要求 Redis 客户端库已安装。\n"
                    "请安装: pip install redis"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            if not self.config.redis_url:
                error_msg = (
                    "REDIS_STREAM 模式要求配置 Redis 连接信息。\n"
                    "请在 settings.py 中配置 REDIS_HOST、REDIS_PORT 等参数"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            if not await self._test_redis_connection():
                error_msg = (
                    f"REDIS_STREAM 模式无法连接到 Redis 服务器。\n"
                    f"Redis URL: {self.config.redis_url}"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            self.logger.debug("REDIS_STREAM mode: Redis connection verified")
            return QueueType.REDIS_STREAM

        elif self.config.queue_type == QueueType.MEMORY:
            return QueueType.MEMORY

        else:
            raise ValueError(f"不支持的队列类型: {self.config.queue_type}")

    async def _create_queue(self, queue_type: QueueType):
        """Create queue instance"""
        if queue_type == QueueType.REDIS_STREAM:
            # RedisStreamQueue
            if not REDIS_AVAILABLE:
                raise RuntimeError("REDIS_STREAM队列不可用：未能导入RedisStreamQueue")

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
                    project_name = "default"
                    spider_name = None

            if not spider_name and hasattr(self.config, 'settings') and self.config.settings:
                try:
                    spider_name = self.config.settings.get('SPIDER_NAME', None)
                except Exception:
                    pass

            # 读取 Stream 配置
            stream_max_length = safe_get_config(
                self.config.settings if hasattr(self.config, 'settings') else None,
                'STREAM_MAX_LENGTH', 100000
            )
            stream_consumer_idle_timeout = safe_get_config(
                self.config.settings if hasattr(self.config, 'settings') else None,
                'STREAM_CONSUMER_IDLE_TIMEOUT', 60000
            )
            stream_delivery_count_limit = safe_get_config(
                self.config.settings if hasattr(self.config, 'settings') else None,
                'STREAM_DELIVERY_COUNT_LIMIT', 3
            )
            stream_block_timeout = safe_get_config(
                self.config.settings if hasattr(self.config, 'settings') else None,
                'STREAM_BLOCK_TIMEOUT', 5000
            )

            queue = RedisStreamQueue(
                redis_url=self.config.redis_url,
                project_name=project_name,
                spider_name=spider_name,
                max_length=stream_max_length,
                consumer_idle_timeout=stream_consumer_idle_timeout,
                delivery_count_limit=stream_delivery_count_limit,
                block_timeout=stream_block_timeout,
                serialization_format=safe_get_config(
                    self.config.settings if hasattr(self.config, 'settings') else None,
                    'STREAM_SERIALIZATION_FORMAT', 'json'
                ),
                stream_compact=safe_get_config(
                    self.config.settings if hasattr(self.config, 'settings') else None,
                    'STREAM_COMPACT', True, bool
                ),
                priority_enabled=safe_get_config(
                    self.config.settings if hasattr(self.config, 'settings') else None,
                    'STREAM_PRIORITY_ENABLED', True, bool
                ),
                sentinel_urls=safe_get_config(
                    self.config.settings if hasattr(self.config, 'settings') else None,
                    'REDIS_SENTINEL_URLS', []
                ),
                sentinel_service=safe_get_config(
                    self.config.settings if hasattr(self.config, 'settings') else None,
                    'REDIS_SENTINEL_SERVICE', 'mymaster'
                ),
            )
            # Stream queue 需要立即 connect 以创建 Consumer Group
            await queue.connect()
            return queue

        elif queue_type == QueueType.REDIS:
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
            # 注入统一背压控制器，避免 Mixin 内部重复计算
            if hasattr(queue, '_bp_delegate') and self._backpressure_controller is not None:
                queue._bp_delegate = self._backpressure_controller
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
            
            # 非 Distributed 模式：如果是 Redis（REDIS 或 REDIS_STREAM）队列且健康检查失败，
            # 尝试切换到内存队列；AUTO 模式允许回退
            if (
                self._queue_type in (QueueType.REDIS, QueueType.REDIS_STREAM)
                and self.config.queue_type == QueueType.AUTO
            ):
                self.logger.info("Redis queue unavailable, attempting to switch to memory queue...")
                try:
                    if self._queue:
                        await self._queue.close()
                except Exception:
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






