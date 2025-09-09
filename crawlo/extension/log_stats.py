#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Any

from crawlo import event
from crawlo.utils.date_tools import now, time_diff


class LogStats(object):

    def __init__(self, stats: Any):
        self._stats = stats

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogStats':
        o = cls(crawler.stats)
        # 订阅所有需要的事件
        event_subscriptions = [
            (o.spider_opened, event.spider_opened),
            (o.spider_closed, event.spider_closed),
            (o.item_successful, event.item_successful),
            (o.item_discard, event.item_discard),
            (o.response_received, event.response_received),
            (o.request_scheduled, event.request_scheduled),
        ]
        
        for handler, evt in event_subscriptions:
            try:
                crawler.subscriber.subscribe(handler, event=evt)
            except Exception as e:
                # 获取日志记录器并记录错误
                from crawlo.utils.log import get_logger
                logger = get_logger(cls.__name__)
                logger.error(f"Failed to subscribe to event {evt}: {e}")

        return o

    async def spider_opened(self) -> None:
        try:
            self._stats['start_time'] = now(fmt='%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass

    async def spider_closed(self) -> None:
        try:
            self._stats['end_time'] = now(fmt='%Y-%m-%d %H:%M:%S')
            self._stats['cost_time(s)'] = time_diff(start=self._stats['start_time'], end=self._stats['end_time'])
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass

    async def item_successful(self, _item: Any, _spider: Any) -> None:
        try:
            self._stats.inc_value('item_successful_count')
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass

    async def item_discard(self, _item: Any, exc: Any, _spider: Any) -> None:
        try:
            self._stats.inc_value('item_discard_count')
            reason = getattr(exc, 'msg', None)  # 更安全地获取属性
            if reason:
                self._stats.inc_value(f"item_discard/{reason}")
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass

    async def response_received(self, _response: Any, _spider: Any) -> None:
        try:
            self._stats.inc_value('response_received_count')
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass

    async def request_scheduled(self, _request: Any, _spider: Any) -> None:
        try:
            self._stats.inc_value('request_scheduler_count')
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass