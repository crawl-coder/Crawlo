#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from typing import List, Type

from crawlo.logging import get_logger
from crawlo.stats import StatsCollector
from crawlo.exceptions import DownloadError

# ---- 收集可用的库异常类型（仅导入成功时才加入重试列表） ----

_retry_exceptions: List[Type[Exception]] = [asyncio.TimeoutError, DownloadError]

try:
    from anyio import EndOfStream
    _retry_exceptions.append(EndOfStream)
except ImportError:
    pass

try:
    from httpcore import ReadError
    _retry_exceptions.append(ReadError)
except ImportError:
    pass

try:
    from httpx import (
        RemoteProtocolError, ConnectError, ReadTimeout,
        ProxyError, TimeoutException, NetworkError,
    )
    _retry_exceptions.extend([
        ConnectError, ReadTimeout, RemoteProtocolError,
        ProxyError, TimeoutException, NetworkError,
    ])
except ImportError:
    pass

try:
    from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError
    from aiohttp import ClientConnectorError, ClientTimeout, ClientConnectorSSLError, ClientResponseError
    _retry_exceptions.extend([
        ClientConnectorError, ClientResponseError, ClientTimeout,
        ClientConnectorSSLError, ClientPayloadError, ClientConnectionError,
    ])
except ImportError:
    pass


class RetryMiddleware:

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
        # 检查爬虫是否正在关闭，如果是则不重试
        if getattr(spider, '_closing', False):
            self.logger.debug(f"爬虫正在关闭，跳过重试: {request.url}")
            return None
        
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
                    # HTTP error, continue using current proxy
                    self.logger.info(f"[Retry {retry_times}/{self.max_retry_times}] ({reason}), using proxy: {request_copy.proxy}, URL: {request.url}")
                else:
                    # Network error (non-HTTP) or exceeded threshold, clear proxy
                    old_proxy = request_copy.proxy
                    if is_http_error:
                        # HTTP error but exceeded threshold, switch to direct connection
                        self.logger.info(f"[Retry {retry_times}/{self.max_retry_times}] ({reason}), removing proxy: {old_proxy}, switching to direct connection, URL: {request.url}")
                    else:
                        # Network error, clear proxy to get new one
                        self.logger.info(f"[Retry {retry_times}/{self.max_retry_times}] ({reason}), clearing proxy: {old_proxy}, will get new proxy, URL: {request.url}")
                    request_copy.proxy = None  # Clear proxy, let proxy middleware reassign
            else:
                self.logger.info(f"[Retry {retry_times}/{self.max_retry_times}] ({reason}), direct connection, URL: {request.url}")
            
            # Exponential backoff retry: avoid rapid consecutive retries wasting resources
            # 1st retry: wait 1s
            # 2nd retry: wait 2s
            # 3rd retry: wait 4s
            backoff_time = min(2 ** (retry_times - 1), 2 ** (self.max_retry_times - 1))  # Max wait based on max_retry_times
            request_copy.meta['retry_backoff'] = backoff_time
                
            request_copy.priority = request.priority + self.retry_priority
            self.stats.inc_value("retry_count")
            # Add retry flag for statistics identification
            request_copy.meta['is_retry'] = True
            
            return request_copy
        else:
            self.logger.warning(f"{request.url} {reason} retry max {self.max_retry_times} times, give up.")
            return None