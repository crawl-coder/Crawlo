#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
数据处理处理器
==============
处理爬虫产生的数据，支持：
- 持续监听模式
- 异步并发处理
- 优雅关闭机制

核心改进：
- 从阻塞式改为持续监听模式
- 支持后台任务运行
- 添加优雅关闭机制
"""
import asyncio
from asyncio import Queue
from typing import Union, Optional, List, Any
from enum import Enum, auto

from crawlo import Request, Item
from crawlo.exceptions import ItemDiscard
from crawlo.logging import get_logger


class ProcessorState(Enum):
    """处理器状态"""
    IDLE = auto()       # 空闲
    RUNNING = auto()    # 运行中
    STOPPING = auto()   # 停止中
    STOPPED = auto()    # 已停止


class Processor:
    """
    数据处理器
    
    持续监听队列，处理 Request 和 Item。
    
    特性：
    - 持续监听模式：不断从队列获取数据处理
    - 后台运行：可作为后台任务运行
    - 优雅关闭：支持等待当前任务完成后关闭
    - 统计信息：跟踪处理数量
    
    使用示例：
        processor = Processor(crawler)
        await processor.open()
        
        # 方式1: 后台运行
        task = processor.start()
        
        # 方式2: 手动处理
        await processor.enqueue(item)
        
        # 关闭
        await processor.stop()
    """
    
    def __init__(self, crawler):
        """
        初始化处理器
        
        Args:
            crawler: Crawler 实例
        """
        self.crawler = crawler
        self.queue: Queue = Queue()
        self.pipelines = None
        self.logger = get_logger(self.__class__.__name__)
        
        # 状态管理
        self._state = ProcessorState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # 统计信息
        self._processed_count = 0
        self._item_count = 0
        self._request_count = 0
        self._error_count = 0
        
        # 正在处理的项（用于优雅关闭）
        # 使用 List 而非 Set，因为 Item 不可哈希
        self._processing: List[Any] = []
        
        # 配置
        self._batch_size = getattr(crawler.settings, 'get_int', lambda x, d: d)('PROCESSOR_BATCH_SIZE', 10)
        self._timeout = getattr(crawler.settings, 'get_float', lambda x, d: d)('PROCESSOR_TIMEOUT', 1.0)
    
    async def open(self) -> None:
        """初始化处理器"""
        from crawlo.pipelines.pipeline_manager import PipelineManager
        self.pipelines = await PipelineManager.from_crawler(self.crawler)
        self.logger.debug("Processor initialized")
    
    async def start(self) -> asyncio.Task:
        """
        启动处理器（后台运行）
        
        Returns:
            asyncio.Task: 后台任务
        """
        if self._state == ProcessorState.RUNNING:
            self.logger.warning("Processor is already running")
            return self._task
        
        self._state = ProcessorState.RUNNING
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        self.logger.debug("Processor started as background task")
        return self._task
    
    async def _run_loop(self) -> None:
        """
        持续监听循环
        
        不断从队列获取数据并处理，直到收到停止信号。
        """
        while not self._stop_event.is_set():
            try:
                # 使用超时避免永久阻塞
                try:
                    result = await asyncio.wait_for(
                        self.queue.get(), 
                        timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    # 超时后继续检查停止信号
                    continue
                
                await self._handle_result(result)
                
            except asyncio.CancelledError:
                self.logger.debug("Processor cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in processor loop: {e}")
                self._error_count += 1
        
        # 处理剩余队列
        await self._drain_queue()
        
        self._state = ProcessorState.STOPPED
        self.logger.debug(f"Processor stopped. Processed: {self._processed_count}")
    
    async def _handle_result(self, result: Union[Request, Item]) -> None:
        """
        处理单个结果
        
        Args:
            result: Request 或 Item
        """
        self._processing.append(result)
        try:
            if isinstance(result, Request):
                await self.crawler.engine.enqueue_request(result)
                self._request_count += 1
            elif isinstance(result, Item):
                await self._process_item(result)
                self._item_count += 1
            else:
                self.logger.warning(f"Unknown result type: {type(result)}")
            
            self._processed_count += 1
            
        except Exception as e:
            self.logger.error(f"Error processing {result}: {e}")
            self._error_count += 1
        finally:
            self._processing.remove(result)
    
    async def _process_item(self, item: Item) -> None:
        """
        处理 Item
        
        Args:
            item: 数据项
        """
        try:
            await self.pipelines.process_item(item=item)
        except ItemDiscard:
            # Item 被丢弃，正常流程
            pass
    
    async def _drain_queue(self) -> None:
        """排空队列中的剩余项"""
        while not self.queue.empty():
            try:
                result = self.queue.get_nowait()
                await self._handle_result(result)
            except asyncio.QueueEmpty:
                break
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        停止处理器
        
        Args:
            timeout: 等待超时时间
        """
        if self._state == ProcessorState.STOPPED:
            return
        
        self._state = ProcessorState.STOPPING
        self._stop_event.set()
        
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                self.logger.warning("Processor stop timeout, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        self._state = ProcessorState.STOPPED
    
    async def enqueue(self, output: Union[Request, Item]) -> None:
        """
        将数据加入队列
        
        如果处理器未启动，会自动启动一次性处理。
        
        Args:
            output: Request 或 Item
        """
        await self.queue.put(output)
        
        # 如果处理器未运行，启动一次性处理
        if self._state == ProcessorState.IDLE:
            await self.process_once()
    
    async def process_once(self) -> None:
        """
        一次性处理队列中的所有数据
        
        处理完当前队列中的所有数据后返回。
        """
        while not self.queue.empty():
            try:
                result = self.queue.get_nowait()
                await self._handle_result(result)
            except asyncio.QueueEmpty:
                break
    
    def idle(self) -> bool:
        """
        检查处理器是否空闲
        
        Returns:
            bool: 是否空闲（队列为空且无正在处理的项）
        """
        return len(self) == 0 and len(self._processing) == 0
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息字典
        """
        return {
            'state': self._state.name,
            'queue_size': len(self),
            'processing_count': len(self._processing),
            'processed_total': self._processed_count,
            'items_processed': self._item_count,
            'requests_processed': self._request_count,
            'errors': self._error_count,
        }
    
    def __len__(self) -> int:
        return self.queue.qsize()
    
    def __repr__(self) -> str:
        return f"<Processor: queue={len(self)}, state={self._state.name}>"
