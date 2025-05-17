#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Optional

from crawlo.utils.log import get_logger
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
        self.crawler.stats.inc_value('request_scheduler_count')

    async def interval_log(self, interval):
        while True:
            last_item_count = self.crawler.stats.get_value('item_successful_count', default=0)
            last_response_count = self.crawler.stats.get_value('response_received_count', default=0)
            item_rate = last_item_count - self.item_count
            response_rate = last_response_count - self.response_count
            self.item_count, self.response_count = last_item_count, last_response_count
            self.logger.info(
                f'Crawled {last_response_count} pages (at {response_rate} pages/{interval}s),'
                f'Got {last_item_count} items (at {item_rate} items/{interval}s).'
            )
            await asyncio.sleep(interval)

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return self.request_queue.qsize()
