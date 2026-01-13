#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
通用代理中间件
支持静态代理列表和动态代理API两种模式
"""
import random
from typing import Optional, List

from crawlo.logging import get_logger
from crawlo.network import Request, Response


class ProxyMiddleware:
    """通用代理中间件"""

    def __init__(self, settings):
        self.logger = get_logger(self.__class__.__name__)

        # 获取代理列表和API URL
        self.proxies: List[str] = settings.get("PROXY_LIST", [])
        self.api_url = settings.get("PROXY_API_URL")
        # 获取代理提取配置
        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")  # 默认从"proxy"字段提取
        
        # 记录失败的代理，避免重复使用
        self.failed_proxies = set()
        # 最大失败次数，超过这个次数的代理将被标记为失效
        self.max_failed_attempts = settings.get("PROXY_MAX_FAILED_ATTEMPTS", 3)
        # 失效代理记录
        self.proxy_failure_count = {}
        
        # 根据配置决定启用哪种模式
        if self.proxies:
            self.mode = "static"  # 静态代理模式
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (static mode) with {len(self.proxies)} proxies")
        elif self.api_url:
            self.mode = "dynamic"  # 动态代理模式
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (dynamic mode) | API: {self.api_url}")
        else:
            self.mode = None
            self.enabled = False
            self.logger.info("ProxyMiddleware disabled (no proxy configuration)")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings)

    async def _fetch_proxy_from_api(self) -> Optional[str]:
        """从代理API获取代理"""
        try:
            import aiohttp
            # 创建带有适当配置的连接器，避免版本兼容性问题
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, force_close=True)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        # 添加内容类型检查
                        content_type = resp.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await resp.json()
                        else:
                            # 如果不是JSON，尝试作为文本处理
                            text = await resp.text()
                            import json
                            data = json.loads(text)
                        
                        # 支持多种代理提取方式
                        proxy = self._extract_proxy_from_data(data)
                        if proxy and isinstance(proxy, str) and (proxy.startswith("http://") or proxy.startswith("https://")):
                            return proxy
                    else:
                        self.logger.warning(f"Proxy API returned status {resp.status}")
        except ImportError as e:
            self.logger.error(f"aiohttp not installed: {repr(e)}")
        except Exception as e:
            self.logger.warning(f"Failed to fetch proxy from API: {repr(e)}")
        return None

    def _extract_proxy_from_data(self, data) -> Optional[str]:
        """
        从API返回的数据中提取代理
        
        支持简单的字段提取方式：
        1. 字符串: 直接作为字段名使用
        """
        if isinstance(self.proxy_extractor, str):
            # 简单字段名提取（向后兼容）
            if self.proxy_extractor in data:
                proxy_value = data[self.proxy_extractor]
                return str(proxy_value) if proxy_value is not None else None
        
        # 默认提取方式（向后兼容）
        if "proxy" in data:
            proxy_value = data["proxy"]
            return str(proxy_value) if proxy_value is not None else None
        
        return None

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """为请求分配代理"""
        if not self.enabled:
            return None

        if request.proxy:
            # 请求已指定代理，不覆盖
            return None

        proxy = None
        if self.mode == "static" and self.proxies:
            # 静态代理模式：随机选择一个代理，排除已知失败的代理
            available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
            if available_proxies:
                proxy = random.choice(available_proxies)
            else:
                self.logger.warning("所有静态代理都已失效，将使用直连")
        elif self.mode == "dynamic" and self.api_url:
            # 动态代理模式：从API获取代理
            proxy = await self._fetch_proxy_from_api()

        if proxy:
            # 检查代理是否在失败列表中
            if proxy in self.failed_proxies:
                self.logger.warning(f"尝试使用已知失败的代理: {proxy}，但仍会尝试")
            
            request.proxy = proxy
            self.logger.info(f"Assigned proxy {proxy} to {request.url}")
        else:
            self.logger.warning(f"No proxy available, request connecting directly: {request.url}")

        return None

    async def process_response(self, request: Request, response: Response, spider) -> Response:
        """处理响应"""
        if request.proxy:
            self.logger.debug(f"Proxy request successful: {request.proxy} | {request.url}")
            # 代理请求成功，从失败列表中移除（如果存在）
            self.failed_proxies.discard(request.proxy)
            # 重置失败计数
            if request.proxy in self.proxy_failure_count:
                del self.proxy_failure_count[request.proxy]
        return response

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """处理异常"""
        if request.proxy:
            error_msg = f"Proxy request failed: {request.proxy} | {request.url} | {repr(exception)}"
            self.logger.warning(error_msg)
            
            # 记录代理失败次数
            if request.proxy not in self.proxy_failure_count:
                self.proxy_failure_count[request.proxy] = 0
            self.proxy_failure_count[request.proxy] += 1
            
            # 如果失败次数超过阈值，将代理标记为失效
            if self.proxy_failure_count[request.proxy] >= self.max_failed_attempts:
                self.failed_proxies.add(request.proxy)
                self.logger.warning(f"代理 {request.proxy} 已失败 {self.max_failed_attempts} 次，标记为失效")
                
                # 从代理列表中移除（仅适用于静态代理模式）
                if self.mode == "static" and request.proxy in self.proxies:
                    self.proxies.remove(request.proxy)
                    self.logger.info(f"已从静态代理列表中移除失效代理: {request.proxy}")
        return None
