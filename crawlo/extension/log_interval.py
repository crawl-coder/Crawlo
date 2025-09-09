#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Any, Optional

from crawlo.utils.log import get_logger
from crawlo.event import spider_opened, spider_closed


class LogIntervalExtension(object):

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.stats = crawler.stats
        self.item_count = 0
        self.response_count = 0
        self.seconds = crawler.settings.get('INTERVAL', 60)  # 默认60秒
        self.interval = int(self.seconds / 60) if self.seconds % 60 == 0 else self.seconds
        self.interval = "" if self.interval == 1 else self.interval
        self.unit = 'min' if self.seconds % 60 == 0 else 's'

        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogIntervalExtension':
        o = cls(crawler)
        crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
        crawler.subscriber.subscribe(o.spider_closed, event=spider_closed)
        return o

    async def spider_opened(self) -> None:
        self.task = asyncio.create_task(self.interval_log())

    async def spider_closed(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def interval_log(self) -> None:
        while True:
            try:
                last_item_count = self.stats.get_value('item_successful_count', default=0)
                last_response_count = self.stats.get_value('response_received_count', default=0)
                item_rate = last_item_count - self.item_count
                response_rate = last_response_count - self.response_count
                self.item_count, self.response_count = last_item_count, last_response_count
                self.logger.info(
                    f'Crawled {last_response_count} pages (at {response_rate} pages/{self.interval}{self.unit}),'
                    f' Got {last_item_count} items (at {item_rate} items/{self.interval}{self.unit}).'
                )
                await asyncio.sleep(self.seconds)
            except Exception as e:
                self.logger.error(f"Error in interval logging: {e}")
                await asyncio.sleep(self.seconds)  # 即使出错也继续执行