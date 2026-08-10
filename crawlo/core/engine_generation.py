#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Engine 请求生成 Mixin — 从 engine.py 拆分

将 RequestGenerationMixin 物理分离到独立文件，
减少 engine.py 体积。Engine 仍通过继承使用，不改变运行时行为。

Components:
- RequestGenerationMixin: 请求生成 Mixin（传统/受控两种流式生成模式 + spider 输出处理）
"""
import asyncio
from typing import Any
from inspect import isasyncgen, iscoroutine, isgenerator

from crawlo import Request, Item
from crawlo.event import CrawlerEvent
from crawlo.core.errors import OutputError

__all__ = ['RequestGenerationMixin']


class RequestGenerationMixin:
    """请求生成 Mixin，提供传统/受控两种流式生成模式"""

    scheduler: Any
    task_manager: Any
    max_queue_size: int
    generation_interval: float
    _generation_stats: Any
    _backpressure_ctrl: Any
    logger: Any
    running: bool

    async def enqueue_request(self, request, **kwargs):  # 由 Engine 提供
        raise NotImplementedError

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
                except Exception as e:
                    self.logger.debug("Suppressed exception: %s", e)
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
                except Exception as e:
                    self.logger.debug("Suppressed exception: %s", e)
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
    # Spider 输出处理（从 Engine 迁入，属于请求生成/输出处理职责）
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
