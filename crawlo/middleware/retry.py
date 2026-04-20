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
from crawlo.exceptions import DownloadError

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
    NetworkError,
    DownloadError,  
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
        # 获取配置中的 RETRY_EXCEPTIONS（可能是字符串列表）
        retry_exceptions_config = crawler.settings.get_list('RETRY_EXCEPTIONS')
        
        # 将字符串转换为实际的异常类型
        retry_exceptions = []
        for exc_str in retry_exceptions_config:
            if isinstance(exc_str, str):
                # 字符串格式：'httpx.ReadTimeout' 或 'httpx.TimeoutException'
                try:
                    from crawlo.utils.misc import load_object
                    exc_type = load_object(exc_str)
                    retry_exceptions.append(exc_type)
                except Exception as e:
                    get_logger(cls.__name__).warning(f"无法加载异常类型 '{exc_str}': {e}")
            else:
                # 已经是异常类型
                retry_exceptions.append(exc_str)
        
        o = cls(
            retry_http_codes=crawler.settings.get_list('RETRY_HTTP_CODES'),
            ignore_http_codes=crawler.settings.get_list('IGNORE_HTTP_CODES'),
            max_retry_times=crawler.settings.get_int('MAX_RETRY_TIMES'),
            retry_exceptions=retry_exceptions,
            stats=crawler.stats,
            retry_priority=crawler.settings.get_int('RETRY_PRIORITY')
        )
        return o

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.ignore_http_codes:
            return response
        if response.status in self.retry_http_codes:
            # Retry logic
            reason = f"response code {response.status}"
            return self._retry(request, reason, spider) or response
        
        # Check if this is a successful retry
        if request.meta.get('retry_times', 0) > 0:
            self.logger.info(f"[Retry Success] {request.url} succeeded with status {response.status} (attempt {request.meta.get('retry_times')})")
        
        return response

    def process_exception(self, request, exc, spider):
        self.logger.debug(f"dont_retry: {request.meta.get('dont_retry', False)}")
        if isinstance(exc, self.retry_exceptions) and not request.meta.get('dont_retry', False):
            return self._retry(request=request, reason=type(exc).__name__, spider=spider)

    def _retry(self, request, reason, spider):
        # Retry logic: create a new request copy with incremented retry count
        
        retry_times = request.meta.get('retry_times', 0)
        if retry_times < self.max_retry_times:
            retry_times += 1
            request_copy = request.copy()
            request_copy.meta['retry_times'] = retry_times
                
            # Proxy retry logic: 网络错误时清除代理，让代理中间件重新分配
            # 这样可以从代理API获取新代理，而不是继续使用故障代理
            if request_copy.proxy:
                # 判断是否为 HTTP 状态码错误（如 404, 500, 502 等）
                # HTTP 错误通常是目标服务器问题，不是代理问题，可以继续使用当前代理
                # 其他错误（超时、连接错误等）清除代理，获取新代理
                is_http_error = reason.isdigit() or reason.startswith('HTTP')
                
                if is_http_error and retry_times <= self.proxy_switch_threshold:
                    # HTTP 错误，继续使用当前代理
                    self.logger.info(f"[Retry {retry_times}/3] ({reason}), using proxy: {request_copy.proxy}, URL: {request.url}")
                else:
                    # 网络错误（非 HTTP 错误）或超过阈值，清除代理
                    old_proxy = request_copy.proxy
                    if is_http_error:
                        # HTTP 错误但超过阈值，切换直连
                        self.logger.info(f"[Retry {retry_times}/3] ({reason}), removing proxy: {old_proxy}, switching to direct connection, URL: {request.url}")
                    else:
                        # 网络错误，清除代理获取新代理
                        self.logger.info(f"[Retry {retry_times}/3] ({reason}), clearing proxy: {old_proxy}, will get new proxy, URL: {request.url}")
                    request_copy.proxy = None  # 清除代理，让代理中间件重新分配
            else:
                self.logger.info(f"[Retry {retry_times}/3] ({reason}), direct connection, URL: {request.url}")
            
            # 指数退避重试：避免快速连续重试导致资源浪费
            # 第1次重试：等待 1秒
            # 第2次重试：等待 2秒
            # 第3次重试：等待 4秒
            backoff_time = min(2 ** (retry_times - 1), 4)  # 最多等待4秒
            request_copy.meta['retry_backoff'] = backoff_time
                
            request_copy.priority = request.priority + self.retry_priority
            self.stats.inc_value("retry_count")
            # Add retry flag for statistics identification
            request_copy.meta['is_retry'] = True
            
            return request_copy
        else:
            self.logger.warning(f"{request.url} {reason} retry max {self.max_retry_times} times, give up.")
            return None