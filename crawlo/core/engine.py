#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 模块 — 爬虫引擎核心

Scrapy 设计原则：引擎只有一个 engine.py，不需要拆 4 个文件。
Phase 3.2：将 engine_main.py / generation.py / helpers.py 合并为单文件。

Core Components:
- Engine: 爬虫引擎主类（继承 RequestGenerationMixin + ClusterMixin）
- RequestGenerationMixin: 请求生成 Mixin（传统/受控两种流式生成模式）
- resolve_start_requests / process_callback_output: 请求生成工具函数
- GenerationStats: 生成统计
- EngineBackpressureAdapter: 背压适配器
- safe_queue_size / has_pending_enqueues: 队列工具函数
"""
import asyncio
import sys
import time
from dataclasses import dataclass, field
from inspect import isasyncgen, iscoroutine, isgenerator
from typing import Any, Callable, Dict, Iterator, Optional, Tuple, Union

from crawlo import Request, Item
from crawlo.spider import Spider
from crawlo.event import CrawlerEvent
from crawlo.project import common_call
from crawlo.core.errors import Failure, OutputError, ErrorClassifier
from crawlo.logging import get_logger
from crawlo.core.scheduling.task_manager import TaskManager
from crawlo.downloader import DownloaderBase
from crawlo.core.processor import Processor
from crawlo.core.scheduling.task_scheduler import Scheduler
from crawlo.core.checkpoint_coordinator import CheckpointCoordinator
from crawlo.utils.misc import load_object, safe_get_config
from crawlo.utils.func_tools import transform
from crawlo.__version__ import __version__
from crawlo.queue.task_tracker import TaskTracker, TaskResult
from crawlo.cluster.coordinator import ClusterMixin, ClusterState, _ack_message
from crawlo.queue.backpressure.interfaces import BackpressureStrategyConfig, IBackpressureStrategy
from crawlo.queue.backpressure.strategies import QueueSizeStrategy, AdaptiveStrategy
from crawlo.queue.backpressure import BackpressureController as _UnifiedController

__all__ = [
    'Engine',
    'RequestGenerationMixin',
    'resolve_start_requests',
    'process_callback_output',
    'GenerationStats',
    'EngineBackpressureAdapter',
    'safe_queue_size',
    'has_pending_enqueues',
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
    """Phase 2：检查 scheduler 是否有阻塞等待中的入队请求。

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


class RequestGenerationMixin:
    """请求生成 Mixin，提供传统/受控两种流式生成模式"""

    async def _traditional_request_generation(self):
        """流式请求生成方法（支持 sync/async 生成器，带背压控制）

        背压策略：当调度器队列积压超过阈值时暂停生成，
        让下载器先消费已有请求（包括列表页产出的详情页），
        避免大量列表页全部入队后才处理详情页的"先列后详"问题。
        """
        self.logger.debug("开始流式请求生成（带背压控制）")
        processed_count = 0

        # 背压阈值：响应 BACKPRESSURE_RATIO 配置
        # ratio 越低 → 阈值越低 → 更积极暂停生成
        concurrency = self.task_manager._concurrency_limit if self.task_manager else 8
        ratio = getattr(self, 'backpressure_ratio', 0.9)
        backpressure_high = max(int(concurrency * 3 * ratio), 20)
        backpressure_low = max(int(concurrency * 1 * ratio), 10)

        try:
            while self.running and self._start_requests_source is not None:
                try:
                    # 背压检查：队列积压过多时暂停生成，让下载器消费
                    if self.scheduler is not None:
                        queue_size = await self.scheduler.async_size()
                        if queue_size >= backpressure_high:
                            self.logger.debug(
                                f"背压暂停生成: 队列 {queue_size} >= {backpressure_high}，"
                                f"等待下载器消费"
                            )
                            self._generation_stats.increment_backpressure()
                            # 等待队列降到低水位
                            while self.running and await self.scheduler.async_size() > backpressure_low:
                                await asyncio.sleep(0.1)
                            queue_size = await self.scheduler.async_size()
                            self.logger.debug(f"背压恢复生成: 队列降至 {queue_size}")

                    if self._start_requests_is_async:
                        start_request = await self._start_requests_source.__anext__()
                    else:
                        start_request = next(self._start_requests_source)

                    # 请求入队
                    await self.enqueue_request(start_request)
                    processed_count += 1
                except (StopIteration, StopAsyncIteration):
                    self.logger.debug(f"所有起始请求处理完成，共 {processed_count} 个")
                    break
                except Exception as exp:
                    self.logger.error(f"处理请求时发生异常: {exp}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    if not await self._exit():
                        continue
                    self.running = False
                    if self._start_requests_source is not None:
                        self.logger.error(f"Error occurred while starting request: {str(exp)}")
                # 短暂让出控制权
                await asyncio.sleep(0.00001)
        finally:
            # 确保异步生成器被正确关闭，避免资源泄露
            if self._start_requests_is_async and self._start_requests_source is not None:
                try:
                    await self._start_requests_source.aclose()
                except Exception:
                    pass
            self._start_requests_source = None
        self.logger.debug(f"流式请求生成完成，总共处理了 {processed_count} 个请求")

    async def _controlled_request_generation(self):
        """受控流式请求生成（支持 sync/async 生成器，背压控制生效）"""
        self.logger.debug("开始受控流式请求生成")

        if self._start_requests_source is None:
            return

        batch = []
        total_generated = 0

        try:
            if self._start_requests_is_async:
                async for request in self._start_requests_source:
                    batch.append(request)
                    if len(batch) >= self.generation_batch_size:
                        generated = await self._process_generation_batch(batch)
                        total_generated += generated
                        batch = []
                    if await self._should_pause_generation():
                        await self._wait_for_capacity()
            else:
                for request in self._start_requests_source:
                    batch.append(request)
                    if len(batch) >= self.generation_batch_size:
                        generated = await self._process_generation_batch(batch)
                        total_generated += generated
                        batch = []
                    if await self._should_pause_generation():
                        await self._wait_for_capacity()

            # 处理剩余请求
            if batch:
                generated = await self._process_generation_batch(batch)
                total_generated += generated

        except Exception as e:
            self.logger.error(f"受控请求生成失败: {e}")

        finally:
            # 确保异步生成器被正确关闭，避免资源泄露
            if self._start_requests_is_async and self._start_requests_source is not None:
                try:
                    await self._start_requests_source.aclose()
                except Exception:
                    pass
            self._start_requests_source = None
            self.logger.debug(f"受控请求生成完成，总计: {total_generated}")

    async def _process_generation_batch(self, batch) -> int:
        """
        处理一批请求

        优化点：
        - 使用 asyncio.gather 并发入队，减少串行等待
        - 动态调整生成间隔，避免过度限流
        - 添加批量统计信息
        """
        generated = 0

        # 优化：如果队列有足够空间，批量并发入队
        queue_size = await self.scheduler.async_size() if self.scheduler else 0
        available_space = self.max_queue_size - queue_size

        if available_space >= len(batch):
            # 队列有足够空间，并发入队
            tasks = []
            for request in batch:
                if not self.running:
                    break
                tasks.append(self._enqueue_single_request(request))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, bool) and result:
                        generated += 1
                        self._generation_stats.increment_generated()
        else:
            # 队列空间不足，逐个入队并等待
            for request in batch:
                if not self.running:
                    break

                # 等待队列有空间
                wait_count = 0
                while await self._is_queue_full() and self.running:
                    await asyncio.sleep(0.005)  # 减少等待间隔
                    wait_count += 1
                    if wait_count > 200:  # 最多等待1秒
                        self.logger.warning("Queue full timeout, skipping remaining requests")
                        break

                if self.running:
                    success = await self._enqueue_single_request(request)
                    if success:
                        generated += 1
                        self._generation_stats.increment_generated()

                # 动态调整生成间隔：根据队列使用率调整
                if self.generation_interval > 0:
                    queue_usage = queue_size / max(1, self.max_queue_size)
                    # 队列使用率高时增加间隔，低时减少间隔
                    adaptive_interval = self.generation_interval * (0.5 + queue_usage)
                    await asyncio.sleep(adaptive_interval)

        return generated

    async def _enqueue_single_request(self, request) -> bool:
        """
        单个请求入队

        Returns:
            bool: 是否成功入队
        """
        try:
            await self.enqueue_request(request)
            return True
        except Exception as e:
            self.logger.debug(f"Failed to enqueue request {request.url}: {e}")
            return False

    async def _should_pause_generation(self) -> bool:
        """Determine whether generation should be paused"""
        # 使用背压控制器检查
        return self._backpressure_ctrl.should_pause(
            self.scheduler,
            self.task_manager
        )

    async def _is_queue_full(self) -> bool:
        """Check if queue is full"""
        return self._backpressure_ctrl.is_queue_full(self.scheduler)

    async def _wait_for_capacity(self):
        """Wait for system to have sufficient capacity"""
        self._generation_stats.increment_backpressure()
        self.logger.debug("Backpressure triggered, pausing request generation")
        await self._backpressure_ctrl.wait_for_capacity(
            self.scheduler,
            self.task_manager,
            running_check=lambda: self.running
        )

    # ========================================================================
    # Spider 输出处理（Phase 3 从 Engine 迁入，属于请求生成/输出处理职责）
    # ========================================================================

    async def _handle_spider_output(self, outputs, parent_request=None):
        """处理 spider 回调输出，自动为子 Request 传播 depth

        框架级 depth 传播机制：
        - 从 parent_request 获取当前 depth（默认 0）
        - 子 Request 的 depth 自动设为 parent_depth + 1
        - 配合 DEPTH_PRIORITY 配置，实现广度优先或深度优先策略

        Args:
            outputs: spider 回调的输出（异步生成器）
            parent_request: 产生此输出的原始请求（用于获取 depth）
        """
        # 获取父请求的 depth
        parent_depth = 0
        if parent_request is not None and hasattr(parent_request, 'meta'):
            parent_depth = parent_request.meta.get('depth', 0)

        if self.processor is None:
            return
        async for spider_output in outputs:
            if isinstance(spider_output, Request):
                # 框架级 depth 传播：子请求 depth = 父请求 depth + 1
                # 仅在子请求未手动设置 depth 时自动注入
                if 'depth' not in spider_output.meta:
                    spider_output.meta['depth'] = parent_depth + 1
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Item):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                if self.crawler is not None and self.spider is not None:
                    self._create_background_task(
                        self.crawler.subscriber.notify(CrawlerEvent.SPIDER_ERROR, spider_output, self.spider)
                    )
                raise spider_output
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`.')

    async def _handle_errback_output(self, result, parent_request=None):
        """
        处理 errback 的返回值，包装后委托给 _handle_spider_output。

        支持与 callback 相同的返回类型：
        - 单个 Request / Item
        - 列表 / 元组
        - 异步生成器
        - 同步生成器
        - 协程
        """
        if isinstance(result, (Request, Item)):
            async def _gen():
                yield result
            await self._handle_spider_output(_gen(), parent_request)
        elif isinstance(result, (list, tuple)):
            async def _gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_gen(), parent_request)
        elif isasyncgen(result):
            await self._handle_spider_output(result, parent_request)
        elif isgenerator(result):
            async def _wrap_sync_gen():
                for item in result:
                    if isinstance(item, (Request, Item)):
                        yield item
            await self._handle_spider_output(_wrap_sync_gen(), parent_request)
        elif iscoroutine(result):
            awaited = await result
            if awaited is not None:
                await self._handle_errback_output(awaited, parent_request)
        else:
            self.logger.warning(
                f"errback returned unexpected type {type(result).__name__}, ignored"
            )


class Engine(RequestGenerationMixin, ClusterMixin):

    # 关键错误类型配置，从 error_types 模块导入
    CRITICAL_EXCEPTIONS = ErrorClassifier.CRITICAL_EXCEPTIONS

    def __init__(self, crawler):
        self.running = False
        self.normal = True
        self.crawler = crawler
        self.settings: Union[Dict[str, Any], Any] = crawler.settings if crawler.settings is not None else {}
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderBase] = None
        self.scheduler: Optional[Scheduler] = None
        self.processor: Optional[Processor] = None
        self._start_requests_source = None  # Original generator (sync gen / async gen / iter)
        self._start_requests_is_async = False  # Whether it's an async generator
        self._seed_lock_key = None  # 种子锁 key（分布式模式）
        self._seed_renewal_task = None  # 种子锁续期任务
        self._close_reason: str = 'finished'  # Close reason: finished / shutdown
        self._spider_closed: bool = False  # Prevent duplicate close_spider calls
        self._background_tasks: set = set()  # Track fire-and-forget tasks to prevent leaks
        self._request_available = asyncio.Event()  # 事件驱动：新请求可用时唤醒主循环
        self._idle_since: Optional[float] = None  # 空闲起始时间（使用 time.monotonic()，分布式模式用）
        self._cluster_state = ClusterState()  # Phase 3 Step 2：集群组件状态容器

        # Initialize configurations
        self._init_configs()

        # Initialize helper utilities
        self._generation_stats = GenerationStats()
        self._backpressure_ctrl = EngineBackpressureAdapter(
            max_queue_size=self.max_queue_size,
            backpressure_ratio=self.backpressure_ratio,
            strategy=self.backpressure_strategy,
        )

        self.logger = get_logger(name=self.__class__.__name__)

    def _create_background_task(self, coro):
        """创建带引用追踪的后台任务，防止 fire-and-forget 任务泄漏"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def _init_configs(self) -> None:
        """
        Initialize all configurations from settings

        Centralized configuration extraction for better maintainability
        """
        # Concurrency control configuration
        concurrency = safe_get_config(self.settings, 'CONCURRENCY', 8, int)
        self.task_manager: Optional[TaskManager] = TaskManager(concurrency)

        # Request generation configuration
        self.days = safe_get_config(self.settings, 'LOG_RETENTION_DAYS', 1, int)
        self.max_queue_size = safe_get_config(self.settings, 'SCHEDULER_MAX_QUEUE_SIZE', 10000, int)
        self.generation_batch_size = safe_get_config(self.settings, 'REQUEST_GENERATION_BATCH_SIZE', 10, int)
        self.generation_interval = safe_get_config(self.settings, 'REQUEST_GENERATION_INTERVAL', 0.01, float)
        self.backpressure_ratio = safe_get_config(self.settings, 'BACKPRESSURE_RATIO', 0.9, float)
        self.backpressure_strategy = safe_get_config(
            self.settings, 'BACKPRESSURE_STRATEGY', 'queue_size', str
        )
        self.enable_controlled_generation = safe_get_config(
            self.settings, 'ENABLE_CONTROLLED_REQUEST_GENERATION', False, bool
        )

        # Version configuration (directly from __version__.py, not from config file)
        self.version = __version__

        # Checkpoint configuration
        self.checkpoint_save_on_signal = safe_get_config(
            self.settings, 'CHECKPOINT_SAVE_ON_SIGNAL', False, bool
        )

        # Distributed worker configuration
        self._worker_idle_timeout = safe_get_config(
            self.settings, 'DISTRIBUTED_WORKER_IDLE_TIMEOUT', 300, int
        )

        # Coordinated shutdown via leader election
        self._cluster_state.coordinated_shutdown_enabled = safe_get_config(
            self.settings, 'DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED', True, bool
        )

        # Downloader configuration
        self.downloader_type = safe_get_config(self.settings, 'DOWNLOADER_TYPE')
        self.downloader_path = safe_get_config(self.settings, 'DOWNLOADER')

        # Phase 3：检查点协调器（组合，替代原 Engine 内三个检查点方法）
        # 放在 _init_configs 末尾以兼容 Engine.__new__ + _init_configs 的测试模式
        self._checkpoint = CheckpointCoordinator(self.settings)

    def _get_downloader_cls(self):
        """
        获取下载器类

        Returns:
            Type[DownloaderBase]: 下载器类
        """
        # 方式1: 使用 DOWNLOADER_TYPE 配置（推荐）
        if self.downloader_type:
            try:
                from crawlo.downloader import get_downloader_class
                downloader_cls = get_downloader_class(self.downloader_type)
                self.logger.debug(f"使用下载器类型: {self.downloader_type} -> {downloader_cls.__name__}")
                return downloader_cls
            except (ImportError, ValueError) as e:
                self.logger.warning(f"无法使用下载器类型 '{self.downloader_type}': {e}，回退到默认配置")

        # 方式2: 使用 DOWNLOADER 完整类路径（兼容旧版本）
        # 如果没有配置下载器，使用默认下载器
        if not self.downloader_path:
            from crawlo.downloader import HttpXDownloader
            return HttpXDownloader

        downloader_cls = load_object(self.downloader_path)
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'下载器 {downloader_cls.__name__} 不是 DownloaderBase 的子类。')
        return downloader_cls

    def engine_start(self):
        self.running = True
        # 使用初始化时获取的版本配置
        self.logger.debug(f"Crawlo框架已启动 {self.version}")

    async def start_spider(self, spider, resume=None):
        """启动单个 Spider。

        Args:
            spider: Spider 实例
            resume: 检查点恢复策略
                - ``None``（默认）：跟随 settings 的 ``CHECKPOINT_ENABLED`` 配置
                - ``True``：强制尝试恢复检查点（即使 CHECKPOINT_ENABLED=False）
                - ``False``：强制不从检查点恢复，忽略已有检查点文件
        """
        self.spider = spider

        # 解析 resume 默认值：跟随 CHECKPOINT_ENABLED，只有显式 True/False 才覆盖
        if resume is None:
            resume = bool(safe_get_config(self.settings, 'CHECKPOINT_ENABLED', False, bool))

        self.scheduler = Scheduler.create_instance(self.crawler)
        if hasattr(self.scheduler, 'open'):
            if asyncio.iscoroutinefunction(self.scheduler.open):
                await self.scheduler.open()
            else:
                # 确保同步方法被正确调用
                result = self.scheduler.open()
                # 只有在result是协程时才await
                if result is not None and asyncio.iscoroutine(result):
                    await result

        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            self.downloader.open()

        # 注册下载器到资源管理器
        if hasattr(self.crawler, '_resource_manager') and self.downloader is not None:
            from crawlo.utils.resource_manager import ResourceType
            self.crawler._resource_manager.register(
                self.downloader,
                lambda d: d.close() if hasattr(d, 'close') else None,
                ResourceType.DOWNLOADER,
                name=f"downloader.{downloader_cls.__name__}"
            )
            self.logger.debug(f"Downloader registered to resource manager: {downloader_cls.__name__}")

        self.processor = Processor(self.crawler)
        if hasattr(self.processor, 'open'):
            await self.processor.open()
        # 在处理器初始化之后初始化扩展管理器，确保日志输出顺序正确
        # 中间件 -> 管道 -> 扩展
        if not hasattr(self.crawler, 'extension') or not self.crawler.extension:
            self.crawler.extension = self.crawler._create_extension()

        # 启动引擎
        self.engine_start()

        # 初始化集群组件（distributed 模式）
        await self._init_cluster()

        # 检查点恢复：如果存在检查点且 resume=True，从检查点恢复
        checkpoint_resumed = False
        if resume:
            checkpoint_resumed = await self._checkpoint.resume_from_checkpoint(spider, self.scheduler)
            if checkpoint_resumed:
                # 跳过 start_requests（检查点中已包含未完成的请求）
                self._start_requests_source = None

        if not checkpoint_resumed:
            # 正常流程：从 start_requests 开始（流式，不物化）
            # 分布式模式：SETNX 选举种子生成器 + 锁续期 + 崩溃恢复
            is_seed_generator = True
            run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
            if run_mode == 'distributed' and self._cluster_state.redis:
                project = safe_get_config(self.settings, 'PROJECT_NAME', 'crawlo')
                spider_name = safe_get_config(self.settings, 'SPIDER_NAME', 'default')
                seed_lock_key = f"crawlo:{project}:{spider_name}:seed:generator"

                # 修复：原实现 get-check-delete-set 三步非原子，两个 Worker 可能同时清锁同时抢锁
                # 改用 Lua 脚本：若锁 owner 不在 registry 中（死锁），则删除并尝试 SETNX
                # Lua 脚本在 Redis 单实例上是原子执行的，消除竞态窗口
                acquired = await self._try_acquire_seed_lock_atomic(
                    seed_lock_key, project, spider_name
                )

                if not acquired:
                    is_seed_generator = False
                    self._start_requests_source = None
                    self.logger.info(
                        f"Worker {self._cluster_state.worker_id}: another Worker is generating "
                        f"seed URLs, skipping start_requests"
                    )
                else:
                    # 启动锁续期任务：每 60 秒延长 TTL
                    self._seed_lock_key = seed_lock_key
                    self._seed_renewal_task = asyncio.create_task(self._renew_seed_lock())

            if is_seed_generator:
                try:
                    source, is_async = await resolve_start_requests(spider, self.logger)
                    self._start_requests_source = source
                    self._start_requests_is_async = is_async
                    self.logger.debug("start_requests 解析成功")
                except Exception as e:
                    self.logger.error(f"解析 start_requests 失败: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

        await self._open_spider()

    async def crawl(self):
        """智能请求生成 + 背压控制的主爬取流程"""
        generation_task = self._setup_generation()
        await self._start_cluster_tasks()
        self._request_available.set()

        try:
            await self._run_main_loop()
        finally:
            await self._cleanup_crawl(generation_task)

    def _setup_generation(self):
        """创建请求生成后台任务"""
        if self._start_requests_source is not None and self.enable_controlled_generation:
            self.logger.debug("创建受控请求生成任务")
            return asyncio.create_task(self._controlled_request_generation())
        self.logger.debug("创建传统请求生成任务")
        return asyncio.create_task(self._traditional_request_generation())

    async def _run_main_loop(self):
        """主爬取循环：获取请求 → 流控 → 派发 → 空闲检测"""
        loop_count = 0
        last_exit_check = 0
        last_component_states = None
        batch_size = max(self.task_manager._concurrency_limit, 10)
        idle_count = 0
        max_inflight = self.task_manager._concurrency_limit + 3
        exit_check_interval, min_ci, max_ci = 10, 5, 20

        while self.running:
            loop_count += 1

            if self._cluster_state.messenger and self._cluster_state.dynamic_config:
                if not await self._check_control_state():
                    break
                if self._cluster_state.paused:
                    await asyncio.sleep(0.5)
                    continue

            # 批量获取请求
            requests = []
            for _ in range(batch_size):
                if request := await self._get_next_request():
                    requests.append(request)
                else:
                    break

            if requests:
                idle_count = 0
                await self._dispatch_requests(requests, max_inflight)
                exit_check_interval = min(exit_check_interval + 1, max_ci)
            else:
                idle_count += 1
                run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
                if run_mode == 'distributed' and self._start_requests_source is None:
                    if await self._handle_distributed_idle(idle_count):
                        break
                    continue

                if idle_count == 1:
                    should_exit, last_component_states = await self._should_exit(last_component_states)
                    if should_exit:
                        await asyncio.sleep(0.001)
                        if await self._check_all_idle():
                            break
                    last_exit_check = loop_count
                exit_check_interval = max(exit_check_interval - 1, min_ci)

            if loop_count - last_exit_check >= exit_check_interval:
                should_exit, last_component_states = await self._should_exit(last_component_states)
                if should_exit:
                    break
                last_exit_check = loop_count

            if requests:
                await asyncio.sleep(0.000001)
            else:
                try:
                    await asyncio.wait_for(
                        self._request_available.wait(),
                        timeout=0.5 if idle_count > 10 else 0.1
                    )
                    self._request_available.clear()
                except asyncio.TimeoutError:
                    pass

        self.logger.debug(f"主爬取循环结束，总共执行了 {loop_count} 次")

    async def _check_control_state(self) -> bool:
        """检查集群控制状态，返回 True 继续运行"""
        try:
            state = await self._cluster_state.dynamic_config.get_control_state()
            if state == "paused":
                self._cluster_state.paused = True
            elif state == "running":
                self._cluster_state.paused = False
            elif state == "shutdown":
                self.logger.warning("Persistent shutdown state detected, exiting")
                self.running = False
                return False
        except Exception:
            pass
        return True

    async def _dispatch_requests(self, requests, max_inflight):
        """派发请求，控制并发流控"""
        self._request_available.clear()
        for req in requests:
            if len(self._background_tasks) >= max_inflight:
                if not getattr(self, '_fc_logged', False):
                    self.logger.debug(
                        f"[流控] 在途={len(self._background_tasks)}/{max_inflight}，等待释放后派发"
                    )
                    self._fc_logged = True
                while len(self._background_tasks) >= max_inflight:
                    await asyncio.sleep(0.01)
            else:
                self._fc_logged = False
            self._create_background_task(self._crawl(req))

    async def _handle_distributed_idle(self, idle_count: int) -> bool:
        """分布式模式下的空闲处理，返回 True 表示应退出"""
        if self._worker_idle_timeout > 0:
            if self._idle_since is not None:
                remaining = self._worker_idle_timeout - (time.monotonic() - self._idle_since)
            else:
                remaining = self._worker_idle_timeout
            if remaining <= 0:
                self.logger.info(f"Worker idle for {self._worker_idle_timeout}s, exiting")
                return True
        else:
            remaining = 30.0

        request = await self.scheduler.next_request_blocking(
            timeout=min(30.0, max(1.0, remaining))
        )
        if request:
            self._idle_since = None
            self._create_background_task(self._crawl(request))
        else:
            if self._idle_since is None:
                self._idle_since = time.monotonic()
            if self._worker_idle_timeout > 0:
                if time.monotonic() - self._idle_since >= self._worker_idle_timeout:
                    self.logger.info(
                        f"Distributed worker idle for {self._worker_idle_timeout}s, exiting"
                    )
                    return True
        return False

    async def _cleanup_crawl(self, generation_task):
        """crawl() 退出后的清理工作"""
        self.running = False

        # 停止种子锁续期
        if self._seed_renewal_task and not self._seed_renewal_task.done():
            self._seed_renewal_task.cancel()
            try:
                await self._seed_renewal_task
            except asyncio.CancelledError:
                pass
        self._seed_renewal_task = None

        if generation_task and not generation_task.done():
            generation_task.cancel()
            try:
                await generation_task
            except asyncio.CancelledError:
                self.logger.debug("Generation task cancelled")
            except Exception as e:
                self.logger.debug(f"Generation task completed with error: {e}")

        reason = self._close_reason
        if reason != 'shutdown':
            process = getattr(self.crawler, '_process', None) if self.crawler else None
            if process is not None:
                try:
                    reason = 'shutdown' if process._shutdown_requested else reason
                except Exception:
                    pass

        try:
            await self.close_spider(reason=reason)
        except asyncio.CancelledError:
            self.logger.debug("close_spider cancelled")

    async def _open_spider(self):
        self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.SPIDER_OPENED))
        # 直接调用crawl方法而不是创建任务，确保等待完成
        await self.crawl()

    async def _crawl(self, request):
        async def crawl_task():
            start_time = time.time()
            _last_error = None  # Capture error for distributed NACK
            try:
                outputs = await self._fetch(request)
                response_time = time.time() - start_time
                if self.task_manager:
                    self.task_manager.record_response_time(response_time)
                depth = getattr(request, 'meta', {}).get('depth', 0)
                page_type = '详情' if isinstance(depth, int) and depth > 1 else '列表'
                self.logger.debug(
                    f"[{page_type}] {request.url} ({response_time:.2f}s)"
                )
                if outputs and not isinstance(outputs, Failure):
                    await self._handle_spider_output(outputs, request)

                # Distributed ACK: success
                await _ack_message(request, self, success=True)

            except asyncio.CancelledError:
                await _ack_message(request, self, success=False)
                raise
            except Exception as e:
                _last_error = e
                self.logger.error(
                    f"处理请求失败: {getattr(request, 'url', 'Unknown URL')} - {type(e).__name__}: {e}",
                    exc_info=True
                )
                if hasattr(self.crawler, 'stats'):
                    self.crawler.stats.inc_value('downloader/exception_count')
                    self.crawler.stats.inc_value(f'downloader/exception_type_count/{type(e).__name__}')
                    if hasattr(request, 'url'):
                        self.crawler.stats.inc_value(f'downloader/failed_urls_count')

                errback = getattr(request, 'errback', None)
                if errback and callable(errback):
                    try:
                        errback_result = await common_call(errback, Failure(e, request=request))
                        if errback_result is not None:
                            await self._handle_errback_output(errback_result, request)
                    except Exception as errback_error:
                        self.logger.error(
                            f"errback 执行失败 [{getattr(request, 'url', 'Unknown URL')}]: "
                            f"{type(errback_error).__name__}: {errback_error}"
                        )

                # Distributed NACK: failure
                await _ack_message(request, self, success=False, error=e)

                if ErrorClassifier.is_critical(e):
                    self.logger.critical(f"遇到关键错误，停止爬虫: {type(e).__name__}: {e}")
                    raise

                return None

        # 使用异步任务创建，遵守并发限制
        if self.task_manager:
            coro = crawl_task()
            try:
                # 创建后台任务但不等待完成（fire-and-forget），
                # 让多个浏览器请求真正并发执行。
                # task_manager 的信号量控制并发上限，
                # done_callback 负责释放信号量。
                await self.task_manager.create_task_nowait(coro)
            except asyncio.CancelledError:
                # 只在第一次取消时打印日志，避免重复
                if not getattr(self, '_cancel_logged', False):
                    self.logger.info("爬取任务被取消")
                    self._cancel_logged = True
                # 确保协程被正确关闭，避免 RuntimeWarning
                coro.close()
                # 重新抛出CancelledError以便调用者可以正确处理
                raise
            except Exception as e:
                self.logger.error(f"创建爬取任务时发生错误: {e}")
                # 确保协程被正确关闭
                coro.close()

    async def _fetch(self, request):
        if self.spider is None:
            self.logger.warning(
                f"_fetch called but engine.spider is None ({request.url if request else 'n/a'}), "
                "skip callback processing, return None"
            )
            return None
        if self.downloader is None:
            self.logger.error("Downloader is not initialized, cannot fetch request")
            return Failure(request, RuntimeError("Downloader not available"))
        _response = await self.downloader.fetch(request)
        if _response is None:
            self.logger.warning(
                f"Downloader returned None for {request.url}, skipping errback"
            )
            return Failure(
                request,
                RuntimeError(f"Downloader returned empty response for {request.url}")
            )
        output = await process_callback_output(
            self.spider,
            request.callback or self.spider.parse,
            request.cb_kwargs,
            _response,
            self.logger
        )
        return output

    async def enqueue_request(self, start_request):
        if self.scheduler is not None:
            await self._schedule_request(start_request)
        else:
            # 修复：移除 emoji，避免影响日志 grep/解析
            self.logger.warning("Scheduler 未初始化，无法入队请求")

    async def _schedule_request(self, request):
        if self.scheduler is not None and await self.scheduler.enqueue_request(request):
            self._request_available.set()  # 唤醒主循环
            if self.crawler is not None and self.crawler.spider is not None:
                self._create_background_task(self.crawler.subscriber.notify(CrawlerEvent.REQUEST_SCHEDULED, request, self.crawler.spider))

    async def _get_next_request(self):
        if self.scheduler is not None:
            return await self.scheduler.next_request()
        return None

    async def _check_components_idle(self, include_background: bool = False) -> tuple[bool, bool, bool, bool, bool]:
        """统一检查各组件是否空闲（消除 _exit / _should_exit 代码重复）

        Returns:
            (scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done)
        """
        scheduler_idle = False
        downloader_idle = False
        task_manager_done = False
        processor_idle = False
        background_tasks_done = False

        if self.scheduler is not None:
            scheduler_idle = await self.scheduler.async_idle()
        if self.downloader is not None:
            downloader_idle = self.downloader.idle()
        if self.task_manager is not None:
            task_manager_done = self.task_manager.all_done()
        if self.processor is not None:
            processor_idle = await self.processor.idle_async()
        if include_background:
            background_tasks_done = len(self._background_tasks) == 0

        return scheduler_idle, downloader_idle, task_manager_done, processor_idle, background_tasks_done

    async def _exit(self):
        """快速退出检查（4 组件，不含 background_tasks，有 pending enqueue 时不退出）"""
        s, d, t, p, _ = await self._check_components_idle(include_background=False)
        return s and d and t and p and not has_pending_enqueues(self.scheduler)

    async def _check_all_idle(self) -> bool:
        """二次确认所有组件是否仍然空闲（用于瞬时空闲误判）"""
        return await self._exit()

    async def _should_exit(self, last_component_states=None) -> tuple[bool, tuple]:
        """检查是否应该退出（5 组件 + start_requests 判断）

        standalone / auto 模式：队列空 + 所有组件空闲 → 正常退出
        distributed 模式：不因队列空退出，由 BZPOPMIN 超时 + idle_timeout 决定

        注意：auto 模式即使检测到 Redis 并切换为 Redis 队列，
             仍然按单机逻辑退出（auto 只是根据环境自动选队列类型，不是常驻 Worker）

        Args:
            last_component_states: 上次的组件状态元组，用于减少冗余日志

        Returns:
            tuple: (should_exit, current_states)
        """
        # 分布式模式不因"组件空闲"退出，由 BZPOPMIN 超时 + idle_timeout 决定
        # 如果将来 _should_exit 增加致命错误等退出条件，需要细化判断，仅跳过"队列空"相关条件
        run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
        if run_mode == 'distributed':
            return False, None

        if self._start_requests_source is None:
            s, d, t, p, bg = await self._check_components_idle(include_background=True)
            current_states = (s, d, t, p, bg)

            if current_states != last_component_states:
                self.logger.debug(
                    f"组件状态变化 - Scheduler: {s}, "
                    f"Downloader: {d}, TaskManager: {t}, "
                    f"Processor: {p}, BackgroundTasks: {bg}"
                )

            if s and d and t and p and bg and not has_pending_enqueues(self.scheduler):
                self.logger.info("All components are idle, preparing to exit")
                return True, current_states
        else:
            self.logger.debug("start_requests 不为 None，不退出")
            current_states = None

        return False, current_states

    async def close_spider(self, reason='finished'):
        # 幂等保护：防止 close_spider 被重复调用
        if self._spider_closed:
            self.logger.debug("close_spider already called, skipping")
            return
        self._spider_closed = True
        self._close_reason = reason

        try:
            # 仅在非正常退出时等待活跃任务完成
            if reason != 'finished' and self.task_manager is not None and self.task_manager.current_task:
                self.logger.debug(f"Waiting for {len(self.task_manager.current_task)} active tasks to complete...")
                try:
                    await asyncio.gather(*self.task_manager.current_task, return_exceptions=True)
                except asyncio.CancelledError:
                    self.logger.debug("Task manager gather cancelled")
                except Exception as e:
                    self.logger.debug(f"Task manager gather completed with errors: {e}")

            # 检查点保存：Ctrl+C 触发的关闭时保存状态
            if reason == 'shutdown':
                await self._checkpoint.save_checkpoint(
                    self.scheduler, self.spider,
                    getattr(self.crawler, 'stats', None),
                    self.checkpoint_save_on_signal,
                )

            # 正常完成时清除检查点
            if reason == 'finished':
                await self._checkpoint.clear_checkpoint(self.spider)

            # 关闭 pipeline（刷新批量数据、清理资源）
            if self.processor is not None and hasattr(self.processor, 'pipelines'):
                await self.processor.pipelines.close()

            # 清理过期日志文件（Phase 3：直接调用 LogManager，不再经过 Engine 包装方法）
            try:
                from crawlo.logging import LogManager
                LogManager().cleanup_old_logs(days=self.days)
            except Exception as e:
                self.logger.error(f"Failed to clean up expired log files: {e}")

            # 关闭下载器（带超时保护，超时后取消内部协程防止资源泄漏）
            if self.downloader is not None and hasattr(self.downloader, 'close'):
                try:
                    close_result = self.downloader.close()
                    # 如果是协程，使用超时等待
                    if asyncio.iscoroutine(close_result):
                        close_task = asyncio.ensure_future(close_result)
                        try:
                            await asyncio.wait_for(close_task, timeout=5.0)
                        except asyncio.TimeoutError:
                            close_task.cancel()
                            try:
                                await close_task
                            except asyncio.CancelledError:
                                pass
                            raise  # 重新抛给外层 except 处理
                except asyncio.TimeoutError:
                    self.logger.warning("下载器关闭超时，强制清理资源")
                except Exception as e:
                    self.logger.debug(f"下载器关闭时发生错误: {e}")

            # 关闭集群组件（heartbeat + failover + deregister）
            await self._shutdown_cluster()

            # 关闭调度器（带超时保护，超时后取消内部协程防止资源泄漏）
            if self.scheduler is not None:
                try:
                    close_task = asyncio.ensure_future(self.scheduler.close())
                    try:
                        await asyncio.wait_for(close_task, timeout=5.0)
                    except asyncio.TimeoutError:
                        close_task.cancel()
                        try:
                            await close_task
                        except asyncio.CancelledError:
                            pass
                        raise  # 重新抛给外层 except 处理
                except asyncio.TimeoutError:
                    self.logger.warning("调度器关闭超时")
                except Exception as e:
                    self.logger.debug(f"调度器关闭时发生错误: {e}")
        except (Exception, asyncio.CancelledError):
            # 清理失败，重置标志允许重试
            self._spider_closed = False
            # 即使清理异常也尝试通知扩展（fire-and-forget，不计入 _background_tasks）
            try:
                if self.crawler is not None and self.crawler.subscriber is not None:
                    from crawlo.event import CrawlerEvent
                    asyncio.ensure_future(
                        self.crawler.subscriber.notify(
                            CrawlerEvent.SPIDER_CLOSED, reason='error'
                        )
                    )
            except Exception:
                pass
            raise

    # Phase 3：检查点三方法（_try_resume_from_checkpoint / _save_checkpoint /
    # _clear_checkpoint）与日志清理（_cleanup_old_logs）已迁出：
    #   - 检查点 → CheckpointCoordinator（组合，self._checkpoint）
    #   - 日志清理 → LogManager.cleanup_old_logs（直接调用）
    #   - 种子锁 → ClusterMixin（_SEED_LOCK_LUA / _renew_seed_lock /
    #     _try_acquire_seed_lock_atomic，本就属于分布式协调职责）

    def get_generation_stats(self) -> dict:
        """获取生成统计"""
        return {
            **self._generation_stats.to_dict(),
            'queue_size': safe_queue_size(self.scheduler),
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0,
            'backpressure_stats': self._backpressure_ctrl.get_stats(),
        }
