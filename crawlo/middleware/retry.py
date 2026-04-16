#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import List

# Import exception classes with graceful fallback
try:
    from anyio import EndOfStream
except ImportError:
    EndOfStream = type('EndOfStream', (Exception,), {})

try:
    from httpcore import ReadError
except ImportError:
    ReadError = type('ReadError', (Exception,), {})

try:
    from httpx import (
        RemoteProtocolError,
        ConnectError,
        ReadTimeout,
        ProxyError,
        TimeoutException,
        NetworkError,
    )
except ImportError:
    RemoteProtocolError = type('RemoteProtocolError', (Exception,), {})
    ConnectError = type('ConnectError', (Exception,), {})
    ReadTimeout = type('ReadTimeout', (Exception,), {})
    ProxyError = type('ProxyError', (Exception,), {})
    TimeoutException = type('TimeoutException', (Exception,), {})
    NetworkError = type('NetworkError', (Exception,), {})

try:
    from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError
    from aiohttp import ClientConnectorError, ClientTimeout, ClientConnectorSSLError, ClientResponseError
except ImportError:
    ClientConnectionError = type('ClientConnectionError', (Exception,), {})
    ClientPayloadError = type('ClientPayloadError', (Exception,), {})
    ClientConnectorError = type('ClientConnectorError', (Exception,), {})
    ClientTimeout = type('ClientTimeout', (Exception,), {})
    ClientConnectorSSLError = type('ClientConnectorSSLError', (Exception,), {})
    ClientResponseError = type('ClientResponseError', (Exception,), {})

from crawlo.logging import get_logger
from crawlo.stats import StatsCollector

_retry_exceptions = [
    EndOfStream,
    ReadError,
    asyncio.TimeoutError,
    ConnectError,
    ReadTimeout,
    ClientConnectorError,
    ClientResponseError,
    RemoteProtocolError,
    ClientTimeout,
    ClientConnectorSSLError,
    ClientPayloadError,
    ClientConnectionError,
    ProxyError,
    TimeoutException,
    NetworkError
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
        # Add proxy switch threshold, usually half of max retries, at least 1
        self.proxy_switch_threshold = max(1, (max_retry_times + 1) // 2)

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
            # Retry logic
            reason = f"response code {response.status_code}"
            return self._retry(request, reason, spider) or response
        
        # Check if this is a successful retry
        if request.meta.get('retry_times', 0) > 0:
            self.logger.info(f"[Retry Success] {request.url} succeeded with status {response.status_code} (attempt {request.meta.get('retry_times')})")
        
        return response

    def process_exception(self, request, exc, spider):
        # self.logger.debug(f"Checking exception {type(exc).__name__} for request {request.url}")
        # self.logger.debug(f"Is instance of retry_exceptions: {isinstance(exc, self.retry_exceptions)}")
        self.logger.info(f"dont_retry: {request.meta.get('dont_retry', False)}")
        if isinstance(exc, self.retry_exceptions) and not request.meta.get('dont_retry', False):
            return self._retry(request=request, reason=type(exc).__name__, spider=spider)

    def _retry(self, request, reason, spider):
        retry_times = request.meta.get('retry_times', 0)
        if retry_times < self.max_retry_times:
            retry_times += 1
            request_copy = request.copy()
            request_copy.meta['retry_times'] = retry_times
                
            # Proxy retry logic: use proxy for first retries, then switch to direct connection
            if request_copy.proxy:
                if retry_times <= self.proxy_switch_threshold:
                    # First retries, continue using proxy
                    self.logger.info(f"[Retry {retry_times}/3] ({reason}), using proxy: {request_copy.proxy}, URL: {request.url}")
                else:
                    # Exceeded threshold, remove proxy, switch to direct connection
                    old_proxy = request_copy.proxy
                    self.logger.info(f"[Retry {retry_times}/3] ({reason}), removing proxy: {old_proxy}, switching to direct connection, URL: {request.url}")
                    request_copy.proxy = None
            else:
                self.logger.info(f"[Retry {retry_times}/3] ({reason}), direct connection, URL: {request.url}")
                
            request_copy.priority = request.priority + self.retry_priority
            self.stats.inc_value("retry_count")
            # Add retry flag for statistics identification
            request_copy.meta['is_retry'] = True
            return request_copy
        else:
            self.logger.warning(f"{request.url} {reason} retry max {self.max_retry_times} times, give up.")
            return None