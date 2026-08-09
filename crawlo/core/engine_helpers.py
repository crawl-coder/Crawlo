#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Engine 辅助组件 — 从 engine.py 拆分的独立类和函数

将不依赖 Engine 内部状态的辅助组件物理分离，
减少 engine.py 体积，便于独立测试和维护。

Components:
- safe_queue_size / has_pending_enqueues: 队列工具函数
- GenerationStats: 请求生成统计 dataclass
- EngineBackpressureAdapter: Engine 级背压适配器
- resolve_start_requests / process_callback_output: 请求生成工具函数
"""
import time
from dataclasses import dataclass
from inspect import isasyncgen, iscoroutine, isgenerator
from typing import Any, Dict, Optional, Tuple

from crawlo import Request, Item
from crawlo.utils.func_tools import transform
from crawlo.queue.backpressure.interfaces import BackpressureStrategyConfig
from crawlo.queue.backpressure.strategies import QueueSizeStrategy, AdaptiveStrategy
from crawlo.queue.backpressure import BackpressureController as _UnifiedController

__all__ = [
    'safe_queue_size',
    'has_pending_enqueues',
    'GenerationStats',
    'EngineBackpressureAdapter',
    'resolve_start_requests',
    'process_callback_output',
]


def safe_queue_size(scheduler) -> int:
    """同步获取队列大小（仅内存队列有效，非内存队列返回 -1）。

    v2.0：Scheduler.__len__ 已删除，内存队列大小通过 queue_manager 内部 qsize() 获取。
    """
    if scheduler is None:
        return 0
    try:
        if not scheduler._is_memory_queue():
            return -1
        inner = getattr(scheduler.queue_manager, '_queue', None)
        if inner and hasattr(inner, 'qsize'):
            return inner.qsize()
        return 0
    except Exception:
        return -1


def has_pending_enqueues(scheduler) -> bool:
    """检查 scheduler 是否有阻塞等待中的入队请求。

    用于 Engine idle 判定：若 > 0 表示有 put 在 block 等待，
    Engine 不应提前退出（否则消费者停了 → 入队永远等不到消费 → 死锁）。

    Returns:
        True 表示有 pending enqueue（不应退出）；False 表示无（可以退出）。
    """
    if scheduler is None:
        return False
    return getattr(scheduler, 'pending_enqueue_count', 0) > 0


@dataclass
class GenerationStats:
    """
    Request generation statistics tracker

    Tracks statistics for request generation.

    Attributes:
        total_generated: Total number of requests generated
        backpressure_events: Number of backpressure trigger events
        batches_processed: Number of batches processed
        start_time: Start time
        end_time: End time
    """
    total_generated: int = 0
    backpressure_events: int = 0
    batches_processed: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def increment_generated(self, count: int = 1) -> None:
        """Increment generation count"""
        self.total_generated += count

    def increment_backpressure(self) -> None:
        """Increment backpressure event count"""
        self.backpressure_events += 1

    def increment_batch(self) -> None:
        """Increment batch count"""
        self.batches_processed += 1

    def mark_start(self) -> None:
        """Mark generation start time"""
        self.start_time = time.time()

    def mark_end(self) -> None:
        """Mark generation end time"""
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def generation_rate(self) -> float:
        """Calculate generation rate (requests/second)"""
        duration = self.duration
        if duration > 0:
            return self.total_generated / duration
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'total_generated': self.total_generated,
            'backpressure_events': self.backpressure_events,
            'batches_processed': self.batches_processed,
            'duration': round(self.duration, 2),
            'generation_rate': round(self.generation_rate, 2),
        }

    def reset(self) -> None:
        """Reset statistics"""
        self.total_generated = 0
        self.backpressure_events = 0
        self.batches_processed = 0
        self.start_time = None
        self.end_time = None

    def __repr__(self) -> str:
        return (
            f"<GenerationStats: generated={self.total_generated}, "
            f"backpressure={self.backpressure_events}, "
            f"rate={self.generation_rate:.1f}/s>"
        )


class EngineBackpressureAdapter:
    """
    Engine-level backpressure adapter — bridges Engine primitives (scheduler,
    task_manager) to the generic backpressure strategy module.

    Controls request generation speed by checking both queue capacity
    and task concurrency. Internally delegates to crawlo.backpressure module
    for unified strategy management.

    Example:
        adapter = EngineBackpressureAdapter(
            max_queue_size=200,
            backpressure_ratio=0.9,
            strategy='queue_size'
        )

        if adapter.should_pause(scheduler, task_manager):
            await adapter.wait_for_capacity(scheduler, task_manager)
    """

    def __init__(
        self,
        max_queue_size: int = 200,
        backpressure_ratio: float = 0.9,
        initial_wait: float = 0.01,
        max_wait: float = 1.0,
        strategy: str = 'queue_size',
    ):
        """
        Initialize backpressure adapter

        Args:
            max_queue_size: Maximum queue size
            backpressure_ratio: Backpressure trigger ratio
            initial_wait: Initial wait time in seconds
            max_wait: Maximum wait time in seconds
            strategy: Strategy name ('queue_size' | 'adaptive')
        """
        self.max_queue_size = max_queue_size
        self.backpressure_ratio = backpressure_ratio
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.strategy_name = strategy

        # Statistics
        self._pause_count = 0
        self._total_wait_time = 0.0

        # Internal: create backpressure strategy from config
        config = BackpressureStrategyConfig(
            threshold=backpressure_ratio,
            base_delay=initial_wait,
            max_delay=max_wait,
        )
        strategy_cls = self._resolve_strategy(strategy)(config=config)
        self._unified = _UnifiedController(strategy=strategy_cls)

    @staticmethod
    def _resolve_strategy(name: str) -> type:
        """Resolve strategy class from name"""
        _map = {
            'queue_size': QueueSizeStrategy,
            'adaptive': AdaptiveStrategy,
        }
        return _map.get(name, QueueSizeStrategy)

    @property
    def pause_count(self) -> int:
        """Number of pauses"""
        return self._pause_count

    @property
    def total_wait_time(self) -> float:
        """Total wait time"""
        return self._total_wait_time

    def is_queue_full(self, scheduler) -> bool:
        """
        Check if queue is full (delegates to unified backpressure strategy)

        Args:
            scheduler: Scheduler instance

        Returns:
            bool: True if queue utilization >= strategy threshold
        """
        if scheduler is None:
            return False

        try:
            queue_size = safe_queue_size(scheduler)
            if queue_size < 0:
                # 非内存队列无法同步获取大小，背压由 QueueManager 层处理
                return False
        except Exception:
            return False
        # Use unified controller's strategy threshold for consistency with QueueManager
        threshold = self.max_queue_size * self._unified.strategy._config.threshold
        return queue_size >= threshold

    def is_overloaded(self, task_manager) -> bool:
        """
        Check if task manager is overloaded

        Args:
            task_manager: Task manager instance

        Returns:
            bool: True if overloaded
        """
        if not task_manager:
            return False

        current_tasks = len(task_manager.current_task)
        semaphore = getattr(task_manager, 'semaphore', None)

        if semaphore:
            max_concurrency = getattr(semaphore, '_initial_value', 8)
            return current_tasks >= max_concurrency * self.backpressure_ratio

        return False

    def should_pause(self, scheduler, task_manager=None) -> bool:
        """
        Check if should pause

        Args:
            scheduler: Scheduler instance
            task_manager: Task manager instance (optional)

        Returns:
            bool: True if should pause
        """
        # Check if queue is full
        if self.is_queue_full(scheduler):
            return True

        # Check if task manager is overloaded
        if task_manager and self.is_overloaded(task_manager):
            return True

        return False

    async def wait_for_capacity(
        self,
        scheduler,
        task_manager=None,
        running_check: callable = None
    ) -> bool:
        """
        Wait for system to have enough capacity

        Args:
            scheduler: Scheduler instance
            task_manager: Task manager instance
            running_check: Callback to check if still running

        Returns:
            bool: True if capacity was successfully waited for (False if interrupted)
        """
        import asyncio

        self._pause_count += 1
        start_wait = time.time()

        wait_time = self.initial_wait

        while self.should_pause(scheduler, task_manager):
            # Check if still running
            if running_check and not running_check():
                return False

            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, self.max_wait)

        self._total_wait_time += time.time() - start_wait
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            'pause_count': self._pause_count,
            'total_wait_time': round(self._total_wait_time, 3),
            'max_queue_size': self.max_queue_size,
            'backpressure_ratio': self.backpressure_ratio,
        }

    def reset(self) -> None:
        """Reset statistics"""
        self._pause_count = 0
        self._total_wait_time = 0.0

    def __repr__(self) -> str:
        return (
            f"<EngineBackpressureAdapter: max_queue={self.max_queue_size}, "
            f"ratio={self.backpressure_ratio}, "
            f"strategy={self.strategy_name}, "
            f"pauses={self._pause_count}>"
        )


async def resolve_start_requests(spider, logger) -> Tuple[Optional[Any], bool]:
    """
    通用 start_requests 返回值解析器

    统一处理同步生成器、异步生成器、协程、列表/元组、
    单个 Request/Item 等多种返回类型，返回 (source, is_async)。

    Returns:
        (source, is_async): source 为可迭代对象或 None，is_async 标识是否为异步
    """
    logger.debug("开始解析 start_requests")
    result = spider.start_requests()

    if isasyncgen(result):
        logger.debug("start_requests 类型: 异步生成器（流式）")
        return result, True

    if iscoroutine(result):
        awaited = await result
        if isasyncgen(awaited):
            logger.debug("start_requests 类型: 协程→异步生成器（流式）")
            return awaited, True
        if isgenerator(awaited):
            logger.debug("start_requests 类型: 协程→同步生成器（流式）")
            return awaited, False
        if awaited is None:
            return None, False
        if isinstance(awaited, (Request, Item)):
            logger.debug("start_requests 类型: 协程→单个值")
            return iter([awaited]), False
        if isinstance(awaited, (list, tuple)):
            logger.debug(f"start_requests 类型: 协程→列表({len(awaited)}个)")
            return iter(awaited), False
        logger.warning(
            f"start_requests 协程返回了未知类型 {type(awaited).__name__}，已作为单元素包装"
        )
        return iter([awaited]), False

    # 同步返回值
    if isgenerator(result):
        logger.debug("start_requests 类型: 同步生成器（流式）")
        return result, False
    if isinstance(result, (list, tuple)):
        logger.debug(f"start_requests 类型: 同步列表({len(result)}个)")
        return iter(result), False
    if isinstance(result, (Request, Item)):
        logger.debug("start_requests 类型: 同步单值")
        return iter([result]), False
    if result is None:
        return None, False
    # 未知可迭代类型
    try:
        source = iter(result)
        logger.debug("start_requests 类型: 同步可迭代对象（流式）")
        return source, False
    except TypeError:
        logger.warning(f"start_requests 返回了不可迭代的类型 {type(result).__name__}")
        return None, False


async def process_callback_output(spider, callback, cb_kwargs, response, logger):
    """
    通用 callback 返回值处理器

    将 callback(response, **cb_kwargs) 的返回值标准化为
    transform() 可消费的异步生成器。

    Returns:
        异步生成器对象或 None
    """
    if spider is None:
        return None

    _outputs = callback(response, **cb_kwargs)
    if _outputs is None:
        return None

    if isasyncgen(_outputs):
        return transform(_outputs, response)

    if isgenerator(_outputs):
        return transform(_outputs, response)

    if iscoroutine(_outputs):
        result = await _outputs
        if result is None:
            return None
        if isasyncgen(result):
            return transform(result, response)
        if isgenerator(result):
            return transform(result, response)
        if isinstance(result, (Request, Item)):
            async def _single_output():
                yield result
            return transform(_single_output(), response)
        if isinstance(result, (list, tuple)):
            async def _list_output():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            return transform(_list_output(), response)
        logger.warning(
            f"Callback {callback.__name__} returned unexpected type "
            f"{type(result).__name__} from coroutine. "
            f"Use 'yield' instead of 'return' for producing output."
        )
        return None

    if isinstance(_outputs, (Request, Item)):
        async def _sync_single_output():
            yield _outputs
        return transform(_sync_single_output(), response)

    if isinstance(_outputs, (list, tuple)):
        async def _sync_list_output():
            for item in _outputs:
                if isinstance(item, (Request, Item)):
                    yield item
        return transform(_sync_list_output(), response)

    logger.warning(
        f"Callback {callback.__name__} returned unexpected type "
        f"{type(_outputs).__name__}. Expected generator, async generator, "
        f"Request, Item, or list/tuple of them."
    )
    return None
