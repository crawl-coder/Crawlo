#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import List
from anyio import EndOfStream
from httpcore import ReadError
from asyncio.exceptions import TimeoutError
from httpx import RemoteProtocolError, ConnectError, ReadTimeout
from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError
from aiohttp import ClientConnectorError, ClientTimeout, ClientConnectorSSLError, ClientResponseError

from crawlo.utils.log import get_logger
from crawlo.stats_collector import StatsCollector

_retry_exceptions = [
    EndOfStream,
    ReadError,
    TimeoutError,
    ConnectError,
    ReadTimeout,
    ClientConnectorError,
    ClientResponseError,
    RemoteProtocolError,
    ClientTimeout,
    ClientConnectorSSLError,
    ClientPayloadError,
    ClientConnectionError
]


class RetryMiddleware(object):

    def __init__(
            self,
            *,
            retry_http_codes: List,
            ignore_http_codes: List,
            max_retry_times: int,
            retry_exceptions: List,
            stats: StatsCollector,
            retry_priority: int
    ):
        self.retry_http_codes = retry_http_codes
        self.ignore_http_codes = ignore_http_codes
        self.max_retry_times = max_retry_times
        self.retry_exceptions = tuple(retry_exceptions + _retry_exceptions)
        self.retry_priority = retry_priority
        self.stats = stats
        self.logger = get_logger(self.__class__.__name__)

    @classmethod
    def create_instance(cls, crawler):
        o = cls(
            retry_http_codes=crawler.settings.get_list('RETRY_HTTP_CODES'),
            ignore_http_codes=crawler.settings.get_list('IGNORE_HTTP_CODES'),
            max_retry_times=crawler.settings.get_int('MAX_RETRY_TIMES'),
            retry_exceptions=crawler.settings.get_list('RETRY_EXCEPTIONS'),
            stats=crawler.stats,
            retry_priority=crawler.settings.get_int('RETRY_PRIORITY')
        )
        return o

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status_code in self.ignore_http_codes:
            return response
        if response.status_code in self.retry_http_codes:
            # 重试逻辑
            reason = f"response code {response.status_code}"
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exc, spider):
        if isinstance(exc, self.retry_exceptions) and not request.meta.get('dont_retry', False):
            return self._retry(request=request, reason=type(exc).__name__, spider=spider)

    def _retry(self, request, reason, spider):
        retry_times = request.meta.get('retry_times', 0)
        if retry_times < self.max_retry_times:
            retry_times += 1
            self.logger.info(f"{spider} {request} {reason} retrying {retry_times} time...")
            request.meta['retry_times'] = retry_times
            # request.dont_retry = True
            request.meta['dont_retry'] = True
            request.priority = request.priority + self.retry_priority
            self.stats.inc_value("retry_count")
            return request
        else:
            self.logger.warning(f"{spider} {request} {reason} retry max {self.max_retry_times} times, give up.")
            return None
