#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 请求生成 Mixin

将流式/受控请求生成逻辑从 Engine 主类中分离，
遵循单一职责原则，独立维护生成策略。
"""
import asyncio
from inspect import isasyncgen, iscoroutine, isgenerator
from typing import Tuple, Optional, Any

from crawlo import Request, Item
from crawlo.utils.func_tools import transform


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
