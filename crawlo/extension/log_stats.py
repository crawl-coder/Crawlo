#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Log Statistics Extension
Provides detailed crawler runtime statistics
"""
import asyncio
from typing import Any

from crawlo.logging import get_logger
from crawlo.helpers import now, time_diff


class LogStats:
    """
    Log statistics extension, records and outputs various statistics during crawler runtime
    """

    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
        self._stats = crawler.stats
        self._stats['start_time'] = now(fmt='%Y-%m-%d %H:%M:%S')

    @classmethod
    def create_instance(cls, crawler):
        """Factory method compatible with ExtensionManager"""
        instance = cls(crawler)
        return instance

    async def spider_closed(self, reason: str = 'finished') -> None:
        try:
            self._stats['end_time'] = now(fmt='%Y-%m-%d %H:%M:%S')
            self._stats['cost_time(s)'] = time_diff(start=self._stats['start_time'], end=self._stats['end_time'])
            self._stats['reason'] = reason
        except Exception as e:
            # Log for debugging, silently handle to avoid affecting crawler
            self.logger.error(f"Error in spider_closed: {e}")

    async def item_successful(self, _item: Any, _spider: Any) -> None:
        try:
            self._stats.inc_value('item_successful_count')
        except Exception as e:
            # Silently handle to avoid affecting crawler
            pass

    async def item_discard(self, _item: Any, exc: Any, _spider: Any) -> None:
        try:
            # Only increment total discard count, don't record details for each discarded item
            self._stats.inc_value('item_discard_count')
        except Exception as e:
            # Silently handle to avoid affecting crawler
            pass

    async def response_received(self, _response: Any, _spider: Any) -> None:
        # Remove duplicate counting: response_received_count already counted in middleware_manager.py
        # Keep this method for event subscription compatibility, but don't double count
        pass

    async def request_scheduled(self, _request: Any, _spider: Any) -> None:
        try:
            # Check if it's a retry request, if so don't count it
            if not _request.meta.get('is_retry', False):
                self._stats.inc_value('request_scheduler_count')
        except Exception as e:
            # Silently handle to avoid affecting crawler
            pass