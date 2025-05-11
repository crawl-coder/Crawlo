#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Optional, Generator, Callable
from inspect import iscoroutine, isgenerator, isasyncgen

from crawlo import Request, Item
from crawlo.spider import Spider
from crawlo.core.scheduler import Scheduler
from crawlo.core.processor import Processor
from crawlo.utils.log import get_logger
from crawlo.task_manager import TaskManager
from crawlo.utils.project import load_class
from crawlo.downloader import DownloaderBase
from crawlo.exceptions import TransformTypeError, OutputError


class Engine(object):

    def __init__(self, crawler):
        self.running = False
        self.crawler = crawler
        self.settings = crawler.settings
        self.spider: Optional[Spider] = None
        self.downloader: Optional[DownloaderBase] = None
        self.scheduler: Optional[Scheduler] = None
        self.processor: Optional[Processor] = None
        self.start_requests: Optional[Generator] = None
        self.task_manager: Optional[TaskManager] = TaskManager(self.settings.get_int('CONCURRENCY'))

        self.logger = get_logger(name=self.__class__.__name__)

    def _get_downloader(self):
        downloader_cls = load_class(self.settings.get('DOWNLOADER'))
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(f'Downloader {downloader_cls.__name__} is not subclass of DownloaderBase.')
        return downloader_cls

    async def start_spider(self, spider):
        self.running = True
        self.logger.info(f"CrawlO started. (project name : {self.settings.get('PROJECT_NAME')})")
        self.spider = spider

        self.scheduler = Scheduler()
        if hasattr(self.scheduler, 'open'):
            self.scheduler.open()

        downloader_cls = self._get_downloader()
        self.downloader = downloader_cls(self.crawler)
        if hasattr(self.downloader, 'open'):
            self.downloader.open()

        self.processor = Processor(self.crawler)
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
                    return self.transform(_outputs)

        _response = await self.downloader.fetch(request)
        if _response is None:
            return None
        output = await _successful(_response)
        return output

    async def enqueue_request(self, start_request):
        await self._schedule_request(start_request)

    async def _schedule_request(self, request):
        # TODO 去重
        await self.scheduler.enqueue_request(request)

    async def _get_next_request(self):
        return await self.scheduler.next_request()

    async def _handle_spider_output(self, outputs):
        async for spider_output in outputs:
            if isinstance(spider_output, (Request, Item)):
                await self.processor.enqueue(spider_output)
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`.')

    async def _exit(self):
        if self.scheduler.idle() and self.downloader.idle() and self.task_manager.all_done() and self.processor.idle():
            return True
        return False

    @staticmethod
    async def transform(funcs):
        if isgenerator(funcs):
            for f in funcs:
                yield f
        elif isasyncgen(funcs):
            async for f in funcs:
                yield f
        else:
            raise TransformTypeError(
                f'callback return type error: {type(funcs)} must be `generator` or `async generator`'
            )

    async def close_spider(self):
        await self.downloader.close()
