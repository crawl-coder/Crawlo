#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo import event
from crawlo.utils.date_tools import now, time_diff


class LogStats(object):

    def __init__(self, stats):
        self._stats = stats

    @classmethod
    def create_instance(cls, crawler):
        o = cls(crawler.stats)
        crawler.subscriber.subscribe(o.spider_opened, event=event.spider_opened)
        crawler.subscriber.subscribe(o.spider_closed, event=event.spider_closed)
        crawler.subscriber.subscribe(o.item_successful, event=event.item_successful)
        crawler.subscriber.subscribe(o.item_discard, event=event.item_discard)
        crawler.subscriber.subscribe(o.response_received, event=event.response_received)
        crawler.subscriber.subscribe(o.request_scheduled, event=event.request_scheduled)

        return o

    async def spider_opened(self):
        self._stats['start_time'] = now(fmt='%Y-%m-%d %H:%M:%S')

    async def spider_closed(self):
        self._stats['end_time'] = now(fmt='%Y-%m-%d %H:%M:%S')
        self._stats['cost_time(s)'] = time_diff(start=self._stats['start_time'], end=self._stats['end_time'])

    async def item_successful(self, _item, _spider):
        self._stats.inc_value('item_successful_count')

    async def item_discard(self, _item, exc, _spider):
        self._stats.inc_value('item_discard_count')
        reason = exc.msg
        if reason:
            self._stats.inc_value(f"item_discard/{reason}")

    async def response_received(self, _response, _spider):
        self._stats.inc_value('response_received_count')

    async def request_scheduled(self, _request, _spider):
        self._stats.inc_value('request_scheduler_count')
