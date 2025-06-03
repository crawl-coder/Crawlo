#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Optional

from crawlo.utils.log import get_logger
from crawlo.event import request_scheduled
from crawlo.utils.pqueue import SpiderPriorityQueue


class Scheduler:
    def __init__(self, crawler):
        self.crawler = crawler
        self.request_queue: Optional[SpiderPriorityQueue] = None

        self.item_count = 0
        self.response_count = 0
        self.logger = get_logger(name=self.__class__.__name__, level=crawler.settings.get('LOG_LEVEL'))

    def open(self):
        self.request_queue = SpiderPriorityQueue()

    async def next_request(self):
        request = await self.request_queue.get()
        return request

    async def enqueue_request(self, request):
        await self.request_queue.put(request)
        asyncio.create_task(self.crawler.subscriber.notify(request_scheduled, request, self.crawler.spider))

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return self.request_queue.qsize()
