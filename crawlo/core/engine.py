#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
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

        self.logger = get_logger(name=self.__class__.__name__)

    def _get_downloader_cls(self):
        downloader_cls = load_class(self.settings.get('DOWNLOADER'))
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'Downloader {downloader_cls.__name__} is not subclass of DownloaderBase.')
        return downloader_cls

    def engine_start(self):
        self.running = True
        self.logger.info(
            f"Crawlo (version {self.settings.get_float('VERSION')}) started. "
            f"(project name : {self.settings.get('PROJECT_NAME')})"
        )

    async def start_spider(self, spider):
        self.spider = spider

        self.scheduler = Scheduler.create_instance(self.crawler)
        if hasattr(self.scheduler, 'open'):
            self.scheduler.open()

        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            self.downloader.open()

        self.processor = Processor(self.crawler)
        if hasattr(self.processor, 'open'):
            self.processor.open()

        self.start_requests = iter(spider.start_requests())
        await self._open_spider()

    async def crawl(self):
        """
        Crawl the spider
        """
        while self.running:
            if request := await self._get_next_request():
                await self._crawl(request)
            try:
                start_request = next(self.start_requests)
            except StopIteration:
                self.start_requests = None
            except Exception as exp:
                # 1、发去请求的request全部运行完毕
                # 2、调度器是否空闲
                # 3、下载器是否空闲
                if not await self._exit():
                    continue
                self.running = False
                if self.start_requests is not None:
                    self.logger.error(f"启动请求时发生错误: {str(exp)}")
            else:
                # 请求入队
                await self.enqueue_request(start_request)

        if not self.running:
            await self.close_spider()

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

        # asyncio.create_task(crawl_task())
        self.task_manager.create_task(crawl_task())

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

    async def close_spider(self):
        await asyncio.gather(*self.task_manager.current_task)
        await self.scheduler.close()
        await self.downloader.close()
        if self.normal:
            await self.crawler.close()