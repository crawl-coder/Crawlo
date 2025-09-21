#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
简化版代理中间件
提供基础的代理功能，避免过度复杂的实现
"""
import random
from typing import Optional, List

from crawlo import Request, Response
from crawlo.exceptions import NotConfiguredError
from crawlo.utils.log import get_logger


class SimpleProxyMiddleware:
    """简化版代理中间件"""

    def __init__(self, settings, log_level):
        self.logger = get_logger(self.__class__.__name__, log_level)

        # 获取代理列表
        self.proxies: List[str] = settings.get("PROXY_LIST", [])
        self.enabled = settings.get_bool("PROXY_ENABLED", False)

        if not self.enabled:
            self.logger.info("SimpleProxyMiddleware disabled")
            return

        if not self.proxies:
            raise NotConfiguredError("PROXY_LIST not configured, SimpleProxyMiddleware disabled")

        self.logger.info(f"SimpleProxyMiddleware enabled with {len(self.proxies)} proxies")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings, log_level=crawler.settings.get("LOG_LEVEL"))

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """为请求分配代理"""
        if not self.enabled:
            return None

        if request.proxy:
            # 请求已指定代理，不覆盖
            return None

        if self.proxies:
            # 随机选择一个代理
            proxy = random.choice(self.proxies)
            request.proxy = proxy
            self.logger.debug(f"Assigned proxy {proxy} to {request.url}")

        return None

    def process_response(self, request: Request, response: Response, spider) -> Response:
        """处理响应"""
        if request.proxy:
            self.logger.debug(f"Proxy request successful: {request.proxy} | {request.url}")
        return response

    def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """处理异常"""
        if request.proxy:
            self.logger.warning(f"Proxy request failed: {request.proxy} | {request.url} | {repr(exception)}")
        return None
