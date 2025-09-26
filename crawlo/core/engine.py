#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import time
from inspect import iscoroutine
from typing import Optional, Generator, Callable

from crawlo import Request, Item
from crawlo.core.processor import Processor
from crawlo.core.scheduler import Scheduler
from crawlo.downloader import DownloaderBase
from crawlo.event import spider_opened, spider_error, request_scheduled
from crawlo.exceptions import OutputError
from crawlo.utils.class_loader import load_class
from crawlo.spider import Spider
from crawlo.task_manager import TaskManager
from crawlo.utils.func_tools import transform
from crawlo.utils.log import get_logger


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
        self.generation_interval = self.settings.get_float('REQUEST_GENERATION_INTERVAL', 0.01)  # 优化默认值
        self.backpressure_ratio = self.settings.get_float('BACKPRESSURE_RATIO', 0.9)  # 优化默认值
        
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
        self.logger.debug(f"Crawlo Framework Started {version}")

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

        # 启动引擎
        self.engine_start()
        
        self.logger.debug("开始创建start_requests迭代器")
        try:
            # 先收集所有请求到列表中，避免在检查时消耗迭代器
            requests_list = list(spider.start_requests())
            self.logger.debug(f"收集到 {len(requests_list)} 个请求")
            self.start_requests = iter(requests_list)
            self.logger.debug("start_requests迭代器创建成功")
        except Exception as e:
            self.logger.error(f"创建start_requests迭代器失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
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
                self.logger.debug("创建受控请求生成任务")
                generation_task = asyncio.create_task(
                    self._controlled_request_generation()
                )
            else:
                # 传统方式处理启动请求
                self.logger.debug("创建传统请求生成任务")
                generation_task = asyncio.create_task(
                    self._traditional_request_generation()
                )
            
            self.logger.debug("请求生成任务创建完成")
            
            # 主爬取循环
            loop_count = 0
            last_exit_check = 0  # 记录上次检查退出条件的时间
            exit_check_interval = 1  # 每1次循环检查一次退出条件，进一步提高检查频率
            
            while self.running:
                loop_count += 1
                # 获取并处理请求
                if request := await self._get_next_request():
                    await self._crawl(request)
                
                # 优化退出条件检查频率
                if loop_count - last_exit_check >= exit_check_interval:
                    should_exit = await self._should_exit()
                    if should_exit:
                        self.logger.debug("满足退出条件，准备退出循环")
                        break
                    last_exit_check = loop_count
                
                # 短暂休息避免忙等，但减少休息时间以提高效率
                await asyncio.sleep(0.000001)  # 从0.00001减少到0.000001
            
            self.logger.debug(f"主爬取循环结束，总共执行了 {loop_count} 次")
        
        finally:
            # 确保请求生成任务完成
            if generation_task and not generation_task.done():
                try:
                    await generation_task
                except asyncio.CancelledError:
                    pass
            
            await self.close_spider()

    async def _traditional_request_generation(self):
        """Traditional request generation method (compatible with older versions)"""
        self.logger.debug("开始处理传统请求生成")
        processed_count = 0
        while self.running:
            try:
                start_request = next(self.start_requests)
                self.logger.debug(f"获取到请求: {getattr(start_request, 'url', 'Unknown URL')}")
                # 请求入队
                await self.enqueue_request(start_request)
                processed_count += 1
                self.logger.debug(f"已处理请求数量: {processed_count}")
            except StopIteration:
                self.logger.debug("所有起始请求处理完成")
                self.start_requests = None
                break
            except Exception as exp:
                self.logger.error(f"处理请求时发生异常: {exp}")
                import traceback
                self.logger.error(traceback.format_exc())
                # 1. All requests have been processed
                # 2. Is scheduler idle
                # 3. Is downloader idle
                if not await self._exit():
                    continue
                self.running = False
                if self.start_requests is not None:
                    self.logger.error(f"Error occurred while starting request: {str(exp)}")
            # 减少等待时间以提高效率
            await asyncio.sleep(0.00001)  # 从0.0001减少到0.00001
        self.logger.debug(f"传统请求生成完成，总共处理了 {processed_count} 个请求")

    async def _controlled_request_generation(self):
        """Controlled request generation (enhanced features)"""
        self.logger.debug("Starting controlled request generation")
        
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
            self.logger.debug(f"Request generation completed, total: {total_generated}")

    async def _process_generation_batch(self, batch) -> int:
        """Process a batch of requests"""
        generated = 0
        
        for request in batch:
            if not self.running:
                break
            
            # 等待队列有空间
            while await self._is_queue_full() and self.running:
                await asyncio.sleep(0.01)  # 减少等待时间
            
            if self.running:
                await self.enqueue_request(request)
                generated += 1
                self._generation_stats['total_generated'] += 1
            
            # 控制生成速度，但使用更小的间隔
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
        
        wait_time = 0.01  # 减少初始等待时间
        max_wait = 1.0  # 减少最大等待时间
        
        while await self._should_pause_generation() and self.running:
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, max_wait)

    async def _open_spider(self):
        asyncio.create_task(self.crawler.subscriber.notify(spider_opened))
        # 直接调用crawl方法而不是创建任务，确保等待完成
        await self.crawl()

    async def _crawl(self, request):
        async def crawl_task():
            start_time = time.time()
            try:
                outputs = await self._fetch(request)
                # 记录响应时间
                response_time = time.time() - start_time
                if self.task_manager:
                    self.task_manager.record_response_time(response_time)
                
                # TODO 处理output
                if outputs:
                    await self._handle_spider_output(outputs)
            except Exception as e:
                # 记录详细的异常信息
                self.logger.error(
                    f"处理请求失败: {getattr(request, 'url', 'Unknown URL')} - {type(e).__name__}: {e}"
                )
                self.logger.debug(f"详细异常信息", exc_info=True)
                
                # 发送统计事件
                if hasattr(self.crawler, 'stats'):
                    self.crawler.stats.inc_value('downloader/exception_count')
                    self.crawler.stats.inc_value(f'downloader/exception_type_count/{type(e).__name__}')
                    if hasattr(request, 'url'):
                        self.crawler.stats.inc_value(f'downloader/failed_urls_count')
                
                # 不再重新抛出异常，避免未处理的Task异常
                return None

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
        self.logger.debug(f"检查退出条件: start_requests={self.start_requests is not None}")
        # 没有启动请求，且所有队列都空闲
        if self.start_requests is None:
            self.logger.debug("start_requests 为 None，检查其他组件状态")
            # 使用异步的idle检查方法以获得更精确的结果
            scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
            downloader_idle = self.downloader.idle()
            task_manager_done = self.task_manager.all_done()
            processor_idle = self.processor.idle()
            
            self.logger.debug(f"组件状态 - Scheduler: {scheduler_idle}, Downloader: {downloader_idle}, TaskManager: {task_manager_done}, Processor: {processor_idle}")
            
            if (scheduler_idle and 
                downloader_idle and 
                task_manager_done and 
                processor_idle):
                # 立即进行二次检查，不等待
                scheduler_idle = await self.scheduler.async_idle() if hasattr(self.scheduler, 'async_idle') else self.scheduler.idle()
                downloader_idle = self.downloader.idle()
                task_manager_done = self.task_manager.all_done()
                processor_idle = self.processor.idle()
                
                self.logger.debug(f"二次检查组件状态 - Scheduler: {scheduler_idle}, Downloader: {downloader_idle}, TaskManager: {task_manager_done}, Processor: {processor_idle}")
                
                if (scheduler_idle and 
                    downloader_idle and 
                    task_manager_done and 
                    processor_idle):
                    self.logger.info("所有组件都空闲，准备退出")
                    return True
        else:
            self.logger.debug("start_requests 不为 None，不退出")
        
        return False

    async def close_spider(self):
        # 不再调用crawler.close()，避免重复清理
        # 清理工作应该由crawler的_lifecycle_manager上下文管理器来处理
        await asyncio.gather(*self.task_manager.current_task)
        await self.scheduler.close()
        await self.downloader.close()
    
    def get_generation_stats(self) -> dict:
        """获取生成统计"""
        return {
            **self._generation_stats,
            'queue_size': len(self.scheduler) if self.scheduler else 0,
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0
        }