#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import time
from inspect import iscoroutine
from typing import Optional, Generator, Callable

from crawlo import Request, Item
from crawlo.spider import Spider
from crawlo.utils.log import get_logger
from crawlo.exceptions import OutputError
from crawlo.core.scheduler import Scheduler
from crawlo.core.processor import Processor
from crawlo.task_manager import TaskManager
from crawlo.project import load_class
from crawlo.downloader import DownloaderBase
from crawlo.utils.func_tools import transform
from crawlo.event import spider_opened, spider_error, request_scheduled


class Engine(object):

    def __init__(self, crawler):
        self.running = False
        self.normal = True
        self.crawler = crawler
        self.settings = crawler.settings
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderBase] = None
        self.scheduler: Optional[Scheduler] = None
        self.processor: Optional[Processor] = None
        self.start_requests: Optional[Generator] = None
        self.task_manager: Optional[TaskManager] = TaskManager(self.settings.get_int('CONCURRENCY'))

        # Enhanced control parameters
        self.max_queue_size = self.settings.get_int('SCHEDULER_MAX_QUEUE_SIZE', 200)
        self.generation_batch_size = self.settings.get_int('REQUEST_GENERATION_BATCH_SIZE', 10)
        self.generation_interval = self.settings.get_float('REQUEST_GENERATION_INTERVAL', 0.05)
        self.backpressure_ratio = self.settings.get_float('BACKPRESSURE_RATIO', 0.8)  # Start backpressure when queue reaches 80%
        
        # State tracking
        self._generation_paused = False
        self._last_generation_time = 0
        self._generation_stats = {
            'total_generated': 0,
            'backpressure_events': 0
        }

        self.logger = get_logger(name=self.__class__.__name__)

    def _get_downloader_cls(self):
        """Get downloader class, supports multiple configuration methods"""
        # 方式1: 使用 DOWNLOADER_TYPE 简化名称（推荐）
        downloader_type = self.settings.get('DOWNLOADER_TYPE')
        if downloader_type:
            try:
                from crawlo.downloader import get_downloader_class
                downloader_cls = get_downloader_class(downloader_type)
                self.logger.debug(f"Using downloader type: {downloader_type} -> {downloader_cls.__name__}")
                return downloader_cls
            except (ImportError, ValueError) as e:
                self.logger.warning(f"Unable to use downloader type '{downloader_type}': {e}, falling back to default configuration")
        
        # 方式2: 使用 DOWNLOADER 完整类路径（兼容旧版本）
        downloader_cls = load_class(self.settings.get('DOWNLOADER'))
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'Downloader {downloader_cls.__name__} is not subclass of DownloaderBase.')
        return downloader_cls

    def engine_start(self):
        self.running = True
        # Get version number, use default value if failed to get
        version = self.settings.get('VERSION', '1.0.0')
        if not version or version == 'None':
            version = '1.0.0'
        # Change INFO level log to DEBUG level to avoid duplication with CrawlerProcess startup log
        self.logger.debug(
            f"Crawlo Started version {version}"
        )

    async def start_spider(self, spider):
        self.spider = spider

        self.scheduler = Scheduler.create_instance(self.crawler)
        if hasattr(self.scheduler, 'open'):
            if asyncio.iscoroutinefunction(self.scheduler.open):
                await self.scheduler.open()
            else:
                self.scheduler.open()

        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            if asyncio.iscoroutinefunction(self.downloader.open):
                self.downloader.open()
            else:
                # DownloaderBase.open() 是同步方法，直接调用而不是await
                self.downloader.open()

        self.processor = Processor(self.crawler)
        if hasattr(self.processor, 'open'):
            if asyncio.iscoroutinefunction(self.processor.open):
                await self.processor.open()
            else:
                # Processor.open() 是同步方法
                self.processor.open()

        # 在处理器初始化之后初始化扩展管理器，确保日志输出顺序正确
        # 中间件 -> 管道 -> 扩展
        if not hasattr(self.crawler, 'extension') or not self.crawler.extension:
            self.crawler.extension = self.crawler._create_extension()

        self.start_requests = iter(spider.start_requests())
        await self._open_spider()

    async def crawl(self):
        """
        Crawl the spider
        Enhanced version supports intelligent request generation and backpressure control
        """
        generation_task = None
        
        try:
            # 启动请求生成任务（如果启用了受控生成）
            if (self.start_requests and 
                self.settings.get_bool('ENABLE_CONTROLLED_REQUEST_GENERATION', False)):
                generation_task = asyncio.create_task(
                    self._controlled_request_generation()
                )
            else:
                # 传统方式处理启动请求
                generation_task = asyncio.create_task(
                    self._traditional_request_generation()
                )
            
            # 主爬取循环
            while self.running:
                # 获取并处理请求
                if request := await self._get_next_request():
                    await self._crawl(request)
                
                # 检查退出条件
                if await self._should_exit():
                    break
                
                # 短暂休息避免忙等
                await asyncio.sleep(0.001)
        
        finally:
            # 清理生成任务
            if generation_task and not generation_task.done():
                generation_task.cancel()
                try:
                    await generation_task
                except asyncio.CancelledError:
                    pass
            
            await self.close_spider()

    async def _traditional_request_generation(self):
        """Traditional request generation method (compatible with older versions)"""
        while self.running:
            try:
                start_request = next(self.start_requests)
                # 请求入队
                await self.enqueue_request(start_request)
            except StopIteration:
                self.start_requests = None
                break
            except Exception as exp:
                # 1. All requests have been processed
                # 2. Is scheduler idle
                # 3. Is downloader idle
                if not await self._exit():
                    continue
                self.running = False
                if self.start_requests is not None:
                    self.logger.error(f"Error occurred while starting request: {str(exp)}")
            await asyncio.sleep(0.001)

    async def _controlled_request_generation(self):
        """Controlled request generation (enhanced features)"""
        self.logger.info("Starting controlled request generation")
        
        batch = []
        total_generated = 0
        
        try:
            for request in self.start_requests:
                batch.append(request)
                
                # 批量处理
                if len(batch) >= self.generation_batch_size:
                    generated = await self._process_generation_batch(batch)
                    total_generated += generated
                    batch = []
                
                # 背压检查
                if await self._should_pause_generation():
                    await self._wait_for_capacity()
            
            # 处理剩余请求
            if batch:
                generated = await self._process_generation_batch(batch)
                total_generated += generated
        
        except Exception as e:
            self.logger.error(f"Request generation failed: {e}")
        
        finally:
            self.start_requests = None
            self.logger.info(f"Request generation completed, total: {total_generated}")

    async def _process_generation_batch(self, batch) -> int:
        """Process a batch of requests"""
        generated = 0
        
        for request in batch:
            if not self.running:
                break
            
            # 等待队列有空间
            while await self._is_queue_full() and self.running:
                await asyncio.sleep(0.1)
            
            if self.running:
                await self.enqueue_request(request)
                generated += 1
                self._generation_stats['total_generated'] += 1
            
            # 控制生成速度
            if self.generation_interval > 0:
                await asyncio.sleep(self.generation_interval)
        
        return generated

    async def _should_pause_generation(self) -> bool:
        """Determine whether generation should be paused"""
        # 检查队列大小
        if await self._is_queue_full():
            return True
        
        # 检查任务管理器负载
        if self.task_manager:
            current_tasks = len(self.task_manager.current_task)
            if hasattr(self.task_manager, 'semaphore'):
                max_concurrency = getattr(self.task_manager.semaphore, '_initial_value', 8)
                if current_tasks >= max_concurrency * self.backpressure_ratio:
                    return True
        
        return False

    async def _is_queue_full(self) -> bool:
        """Check if queue is full"""
        if not self.scheduler:
            return False
        
        queue_size = len(self.scheduler)
        return queue_size >= self.max_queue_size * self.backpressure_ratio

    async def _wait_for_capacity(self):
        """Wait for system to have sufficient capacity"""
        self._generation_stats['backpressure_events'] += 1
        self.logger.debug("Backpressure triggered, pausing request generation")
        
        wait_time = 0.1
        max_wait = 2.0
        
        while await self._should_pause_generation() and self.running:
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, max_wait)

    async def _open_spider(self):
        asyncio.create_task(self.crawler.subscriber.notify(spider_opened))
        crawling = asyncio.create_task(self.crawl())
        await crawling

    async def _crawl(self, request):
        # TODO 实现并发
        async def crawl_task():
            outputs = await self._fetch(request)
            # TODO 处理output
            if outputs:
                await self._handle_spider_output(outputs)

        # 使用异步任务创建，遵守并发限制
        await self.task_manager.create_task(crawl_task())

    async def _fetch(self, request):
        async def _successful(_response):
            callback: Callable = request.callback or self.spider.parse
            if _outputs := callback(_response):
                if iscoroutine(_outputs):
                    await _outputs
                else:
                    return transform(_outputs, _response)

        _response = await self.downloader.fetch(request)
        if _response is None:
            return None
        output = await _successful(_response)
        return output

    async def enqueue_request(self, start_request):
        await self._schedule_request(start_request)

    async def _schedule_request(self, request):
        # TODO 去重
        if await self.scheduler.enqueue_request(request):
            asyncio.create_task(self.crawler.subscriber.notify(request_scheduled, request, self.crawler.spider))

    async def _get_next_request(self):
        return await self.scheduler.next_request()

    async def _handle_spider_output(self, outputs):
        async for spider_output in outputs:
            if isinstance(spider_output, (Request, Item)):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                asyncio.create_task(
                    self.crawler.subscriber.notify(spider_error, spider_output, self.spider)
                )
                raise spider_output
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`.')

    async def _exit(self):
        if self.scheduler.idle() and self.downloader.idle() and self.task_manager.all_done() and self.processor.idle():
            return True
        return False

    async def _should_exit(self) -> bool:
        """检查是否应该退出"""
        # 没有启动请求，且所有队列都空闲
        if self.start_requests is None:
            # 使用异步的idle检查方法以获得更精确的结果
            scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
            
            if (scheduler_idle and 
                self.downloader.idle() and 
                self.task_manager.all_done() and 
                self.processor.idle()):
                # 增加额外检查确保所有任务都完成
                await asyncio.sleep(0.1)  # 短暂等待确保没有新的任务加入
                if (await self.scheduler.async_idle() and 
                    self.downloader.idle() and 
                    self.task_manager.all_done() and 
                    self.processor.idle()):
                    return True
        
        return False

    async def close_spider(self):
        await asyncio.gather(*self.task_manager.current_task)
        await self.scheduler.close()
        await self.downloader.close()
        if self.normal:
            await self.crawler.close()
    
    def get_generation_stats(self) -> dict:
        """获取生成统计"""
        return {
            **self._generation_stats,
            'queue_size': len(self.scheduler) if self.scheduler else 0,
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0
        }