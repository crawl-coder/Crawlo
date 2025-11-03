#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
日志统计扩展
提供详细的爬虫运行统计信息
"""
import asyncio
from typing import Any

from crawlo.logging import get_logger
from crawlo.utils import now, time_diff


class LogStats:
    """
    日志统计扩展，记录和输出爬虫运行过程中的各种统计信息
    """

    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
        self._stats = crawler.stats
        self._stats['start_time'] = now(fmt='%Y-%m-%d %H:%M:%S')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    @classmethod
    def create_instance(cls, crawler):
        return cls.from_crawler(crawler)

    async def spider_closed(self, reason: str = 'finished') -> None:
        try:
            self._stats['end_time'] = now(fmt='%Y-%m-%d %H:%M:%S')
            self._stats['cost_time(s)'] = time_diff(start=self._stats['start_time'], end=self._stats['end_time'])
            self._stats['reason'] = reason
        except Exception as e:
            # 添加日志以便调试
            self.logger.error(f"Error in spider_closed: {e}")
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
            # 只增加总的丢弃计数，不记录每个丢弃项目的原因详情
            self._stats.inc_value('item_discard_count')
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
            # 检查是否为重试请求，如果是则不计入统计
            if not _request.meta.get('is_retry', False):
                self._stats.inc_value('request_scheduler_count')
        except Exception as e:
            # 静默处理，避免影响爬虫运行
            pass