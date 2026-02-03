#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import List

try:
    from anyio import EndOfStream
except ImportError:
    # 如果 anyio 不可用或者 EndOfStream 不存在，创建一个占位符
    class EndOfStream(Exception):
        pass

try:
    from httpcore import ReadError
except ImportError:
    class ReadError(Exception):
        pass

try:
    from httpx import RemoteProtocolError, ConnectError, ReadTimeout, ProxyError, TimeoutException, NetworkError
except ImportError:
    class RemoteProtocolError(Exception):
        pass
    class ConnectError(Exception):
        pass
    class ReadTimeout(Exception):
        pass
    class ProxyError(Exception):
        pass
    class TimeoutException(Exception):
        pass
    class NetworkError(Exception):
        pass

try:
    from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError
    from aiohttp import ClientConnectorError, ClientTimeout, ClientConnectorSSLError, ClientResponseError
except ImportError:
    class ClientConnectionError(Exception):
        pass
    class ClientPayloadError(Exception):
        pass
    class ClientConnectorError(Exception):
        pass
    class ClientTimeout(Exception):
        pass
    class ClientConnectorSSLError(Exception):
        pass
    class ClientResponseError(Exception):
        pass

from crawlo.logging import get_logger
from crawlo.stats_collector import StatsCollector

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
        # 添加一个代理切换阈值，通常是最大重试次数的一半，至少为1
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
            # 重试逻辑
            reason = f"response code {response.status_code}"
            return self._retry(request, reason, spider) or response
        
        # 检查是否是重试成功的请求
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
                
            # 代理重试逻辑：前几次使用代理，超过阈值后使用直连
            if request_copy.proxy:
                if retry_times <= self.proxy_switch_threshold:
                    # 前几次重试，继续使用代理
                    self.logger.info(f"[Retry {retry_times}/3] {request.url} ({reason}), using proxy: {request_copy.proxy}")
                else:
                    # 超过阈值，移除代理，使用直连
                    self.logger.info(f"[Retry {retry_times}/3] {request.url} ({reason}), switching to direct connection (removed proxy)")
                    request_copy.proxy = None
            else:
                self.logger.info(f"[Retry {retry_times}/3] {request.url} ({reason}), direct connection")
                
            request_copy.priority = request.priority + self.retry_priority
            self.stats.inc_value("retry_count")
            # 添加重试标识，用于统计时识别
            request_copy.meta['is_retry'] = True
            return request_copy
        else:
            self.logger.warning(f"{request.url} {reason} retry max {self.max_retry_times} times, give up.")
            return None