#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from inspect import iscoroutine, isgenerator, isasyncgen
from typing import Optional, Generator, Callable

from crawlo import Request
from crawlo.exceptions import TransformTypeError, OutputError
from crawlo.spider import Spider
from crawlo.core.download import Downloader
from crawlo.core.scheduler import Scheduler


class Engine(object):

    def __init__(self):
        self.spider: Optional[Spider] = None
        self.downloader: Optional[Downloader] = None
        self.scheduler: Optional[Scheduler] = None
        self.start_requests: Optional[Generator] = None

    async def start_spider(self, spider):
        self.spider = spider
        self.scheduler = Scheduler()
        if hasattr(self.scheduler, 'open'):
            self.scheduler.open()

        self.downloader = Downloader()
        self.start_requests = iter(spider.start_requests())
        await self._open_spider()

    async def crawl(self):
        """
        Crawl the spider
        :return:
        """
        while True:
            if request := await self._get_next_request():
                await self._crawl(request)
            try:
                start_request = next(self.start_requests)  # noqa

            except StopIteration:
                self.start_requests = None
            except Exception as e:
                break
            else:
                # 请求入队
                await self.enqueue_request(start_request)

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
        asyncio.create_task(crawl_task())

    async def _fetch(self, request):
        async def _successful(_response):
            callback: Callable = request.callback or self.spider.parse
            if _outputs := callback(_response):
                if iscoroutine(_outputs):
                    await _outputs
                else:
                    return self.transform(_outputs)

        _response = await self.downloader.fetch(request)
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
            if isinstance(spider_output, Request):
                await self.enqueue_request(spider_output)
            # 需要判断是不是数据，替换为Item
            else:
                raise OutputError(f'{type(self.spider)} must return `Request` or `Item`')

    async def _exit(self):
        if self.scheduler.idle() and self.downloader.idle() and self.task_manager.all_done() and self.processor.idle():
            return True
        else:
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
