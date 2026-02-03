# -*- coding: UTF-8 -*-
"""
ofweek_standalone.middlewares
============================
自定义中间件示例
"""
import random
import time
from typing import Dict, List, Optional

import aiohttp

from crawlo.logging import get_logger
from crawlo.network import Request, Response


class ProxyMiddleware:
    """
    IP代理中间件
    
    功能特性:
    - 支持静态代理列表和动态代理API两种模式
    - 时间窗口失效检测（5分钟内失败3次标记为坏代理）
    - 自动从失效列表中恢复过期的代理
    """

    def __init__(self, settings):
        self.logger = get_logger(self.__class__.__name__)

        # 获取代理配置
        self.proxies: List[str] = settings.get("PROXY_LIST", [])
        self.api_url = settings.get("PROXY_API_URL")
        
        # 失效代理记录: proxy -> 失败时间戳
        self.failed_proxies: Dict[str, float] = {}
        
        # 失效检测配置
        self.failure_threshold = settings.get("PROXY_FAILURE_THRESHOLD", 3)
        self.failure_window = settings.get("PROXY_FAILURE_WINDOW", 300)  # 5分钟

        # 根据配置决定启用模式
        if self.proxies:
            self.mode = "static"
            self.enabled = True
            self.logger.info(f"代理中间件已启用 (静态模式) | 代理数量: {len(self.proxies)}")
        elif self.api_url:
            self.mode = "dynamic"
            self.enabled = True
            self.logger.info(f"代理中间件已启用 (动态模式) | API: {self.api_url}")
        else:
            self.mode = None
            self.enabled = False
            self.logger.info("代理中间件已禁用 (无代理配置)")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings)

    def _is_bad_proxy(self, proxy: str) -> bool:
        """
        检查代理是否在失效时间窗口内
        
        Args:
            proxy: 代理地址
            
        Returns:
            bool: 是否为坏代理
        """
        now = time.time()
        if proxy in self.failed_proxies:
            failure_time = self.failed_proxies[proxy]
            if now - failure_time < self.failure_window:
                return True
            else:
                # 清除过期的失败记录
                del self.failed_proxies[proxy]
        return False

    def _mark_bad_proxy(self, proxy: str):
        """
        标记代理为失效
        
        Args:
            proxy: 代理地址
        """
        if proxy:
            self.failed_proxies[proxy] = time.time()
            self.logger.warning(
                f"代理 {proxy} 标记为失效，将在接下来的 {self.failure_window} 秒内不再使用"
            )

    async def _fetch_proxy_from_api(self) -> Optional[str]:
        """
        从代理API获取代理
        
        Returns:
            Optional[str]: 代理地址
        """
        try:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, force_close=True)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await resp.json()
                        else:
                            text = await resp.text()
                            import json
                            data = json.loads(text)
                        
                        # 支持多种代理提取方式
                        proxy = self._extract_proxy_from_data(data)
                        
                        # 检查代理是否已失效
                        if proxy and self._is_bad_proxy(proxy):
                            self.logger.debug(f"跳过已知失效代理: {proxy}")
                            return None
                            
                        return proxy
                    else:
                        self.logger.warning(f"代理API返回状态 {resp.status}")
        except Exception as e:
            self.logger.error(f"获取代理时发生异常: {e}")
        return None

    def _extract_proxy_from_data(self, data) -> Optional[str]:
        """
        从API返回的数据中提取代理
        
        Args:
            data: API返回的数据
            
        Returns:
            Optional[str]: 代理地址
        """
        # 支持简单的字段提取方式
        if isinstance(data, dict):
            # 优先从 proxy 字段提取
            if 'proxy' in data:
                proxy_value = data['proxy']
                if isinstance(proxy_value, str):
                    return proxy_value
                elif isinstance(proxy_value, dict):
                    # {"proxy": {"http": "...", "https": "..."}}
                    return proxy_value.get('http') or proxy_value.get('https')
            
            # 尝试其他常见字段
            for field in ['http', 'https', 'url', 'address']:
                if field in data:
                    proxy_value = data[field]
                    if isinstance(proxy_value, str) and (proxy_value.startswith('http://') or proxy_value.startswith('https://')):
                        return proxy_value
        
        # 如果是字符串，直接返回
        if isinstance(data, str) and (data.startswith('http://') or data.startswith('https://')):
            return data
            
        return None

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """
        为请求分配代理
        
        Args:
            request: 请求对象
            spider: 爬虫实例
            
        Returns:
            Optional[Request]: 修改后的请求对象
        """
        if not self.enabled:
            return None

        if request.proxy:
            # 请求已指定代理，不覆盖
            return None

        proxy = None
        if self.mode == "static" and self.proxies:
            # 静态代理模式：随机选择一个代理，排除已知失效的代理
            available_proxies = [p for p in self.proxies if not self._is_bad_proxy(p)]
            if available_proxies:
                proxy = random.choice(available_proxies)
            else:
                self.logger.warning("所有静态代理都已失效，将使用直连")
        elif self.mode == "dynamic" and self.api_url:
            # 动态代理模式：从API获取代理
            proxy = await self._fetch_proxy_from_api()

        if proxy:
            request.proxy = proxy
            self.logger.debug(f"为 {request.url} 分配代理 {proxy}")
        else:
            self.logger.debug(f"无可用代理，请求直接连接: {request.url}")

        return None

    async def process_response(self, request: Request, response: Response, spider) -> Response:
        """
        处理响应
        
        Args:
            request: 请求对象
            response: 响应对象
            spider: 爬虫实例
            
        Returns:
            Response: 响应对象
        """
        if request.proxy:
            # 检查是否是502错误（代理网关错误）
            if hasattr(response, 'status') and response.status_code == 502:
                self.logger.warning(f"代理请求收到502错误: {request.proxy} | {request.url}")
                self._mark_bad_proxy(request.proxy)
            else:
                self.logger.debug(
                    f"代理请求成功: {request.proxy} | {request.url} | Status: {response.status_code}"
                )
        return response

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """
        处理异常
        
        Args:
            request: 请求对象
            exception: 异常对象
            spider: 爬虫实例
            
        Returns:
            Optional[Request]: 修改后的请求对象
        """
        if request.proxy:
            # 检查是否是代理相关错误
            error_str = str(exception)
            is_proxy_error = (
                '502' in error_str or
                'Bad Gateway' in error_str or
                'ProxyError' in str(type(exception)) or
                'RemoteProtocolError' in error_str or
                'Server disconnected without sending a response' in error_str
            )

            if is_proxy_error:
                self._mark_bad_proxy(request.proxy)
                self.logger.warning(f"代理请求失败: {request.proxy} | {request.url} | {repr(exception)}")

        # 不处理重试逻辑，让 RetryMiddleware 处理
        return None
