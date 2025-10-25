#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.event import CrawlerEvent


class LogIntervalExtension:

    def __init__(self, crawler: Any):
        self.task: Optional[asyncio.Task] = None
        self.stats = crawler.stats
        self.item_count = 0
        self.response_count = 0
        self.seconds = crawler.settings.get('INTERVAL', 60)  # 默认60秒
        
        # 修复时间单位计算逻辑
        if self.seconds % 60 == 0:
            self.interval = int(self.seconds / 60)
            self.unit = 'min'
        else:
            self.interval = self.seconds
            self.unit = 's'
        
        # 处理单数情况
        if self.interval == 1 and self.unit == 'min':
            self.interval_display = ""
        else:
            self.interval_display = str(self.interval)

        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LogIntervalExtension initialized with interval: {self.seconds} seconds")

    @classmethod
    def create_instance(cls, crawler: Any) -> 'LogIntervalExtension':
        o = cls(crawler)
        crawler.subscriber.subscribe(o.spider_opened, event=CrawlerEvent.SPIDER_OPENED)
        crawler.subscriber.subscribe(o.spider_closed, event=CrawlerEvent.SPIDER_CLOSED)
        return o

    async def spider_opened(self) -> None:
        self.logger.info("Spider opened, starting interval logging task")
        self.task = asyncio.create_task(self.interval_log())
        self.logger.info("Interval logging task started")

    async def spider_closed(self) -> None:
        self.logger.info("Spider closed, stopping interval logging task")
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def interval_log(self) -> None:
        iteration = 0
        while True:
            try:
                iteration += 1
                self.logger.debug(f"Interval log iteration {iteration} starting")
                last_item_count = self.stats.get_value('item_successful_count', default=0)
                last_response_count = self.stats.get_value('response_received_count', default=0)
                item_rate = last_item_count - self.item_count
                response_rate = last_response_count - self.response_count
                
                # 添加调试信息
                self.logger.debug(f"Debug info - Iteration: {iteration}, Last item count: {last_item_count}, Last response count: {last_response_count}")
                self.logger.debug(f"Debug info - Previous item count: {self.item_count}, Previous response count: {self.response_count}")
                self.logger.debug(f"Debug info - Item rate: {item_rate}, Response rate: {response_rate}")
                
                self.item_count, self.response_count = last_item_count, last_response_count
                
                # 修复效率计算，确保使用正确的单位
                if self.unit == 'min' and self.seconds > 0:
                    # 转换为每分钟速率
                    pages_per_min = response_rate * 60 / self.seconds if self.seconds > 0 else 0
                    items_per_min = item_rate * 60 / self.seconds if self.seconds > 0 else 0
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {pages_per_min:.0f} pages/min),'
                        f' Got {last_item_count} items (at {items_per_min:.0f} items/min).'
                    )
                else:
                    # 使用原始单位
                    self.logger.info(
                        f'Crawled {last_response_count} pages (at {response_rate} pages/{self.interval_display}{self.unit}),'
                        f' Got {last_item_count} items (at {item_rate} items/{self.interval_display}{self.unit}).'
                    )
                self.logger.debug(f"Interval log iteration {iteration} completed, sleeping for {self.seconds} seconds")
                await asyncio.sleep(self.seconds)
            except Exception as e:
                self.logger.error(f"Error in interval logging: {e}")
                await asyncio.sleep(self.seconds)  # 即使出错也继续执行