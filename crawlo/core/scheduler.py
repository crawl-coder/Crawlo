#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional, Callable

from crawlo.utils.log import get_logger
from crawlo.utils.request import set_request
from crawlo.utils.pqueue import SpiderPriorityQueue
from crawlo.project import load_class, common_call


class Scheduler:
    def __init__(self, crawler, dupe_filter, stats, log_level, priority):
        self.crawler = crawler
        self.request_queue: Optional[SpiderPriorityQueue] = None

        self.logger = get_logger(name=self.__class__.__name__, level=log_level)
        self.stats = stats
        self.dupe_filter = dupe_filter
        self.priority = priority

    @classmethod
    def create_instance(cls, crawler):
        filter_cls = load_class(crawler.settings.get('FILTER_CLASS'))
        o = cls(
            crawler=crawler,
            dupe_filter=filter_cls.create_instance(crawler),
            stats=crawler.stats,
            log_level=crawler.settings.get('LOG_LEVEL'),
            priority=crawler.settings.get('DEPTH_PRIORITY')
        )
        return o

    def open(self):
        self.request_queue = SpiderPriorityQueue()
        self.logger.info(f'requesting filter: {self.dupe_filter}')

    async def next_request(self):
        request = await self.request_queue.get()
        return request

    async def enqueue_request(self, request):
        if not request.dont_filter and await common_call(self.dupe_filter.requested, request):
            self.dupe_filter.log_stats(request)
            return False
        set_request(request, self.priority)
        await self.request_queue.put(request)
        return True

    def idle(self) -> bool:
        return len(self) == 0

    async def close(self):
        if isinstance(closed := getattr(self.dupe_filter, 'closed', None), Callable):
            await closed()

    def __len__(self):
        return self.request_queue.qsize()
