#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
from typing import Optional, Dict, Any
from curl_cffi.requests import AsyncSession

from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config


class CurlCffiDownloader(DownloaderBase):
    """
    基于 curl-cffi 的高性能异步下载器
    - 支持真实浏览器指纹模拟，绕过 Cloudflare 等反爬虫检测
    - 高性能的异步 HTTP 客户端，基于 libcurl
    - 内存安全的响应处理
    - 自动代理和 Cookie 管理
    - 代理由 ProxyMiddleware 统一管理
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)
        self.session: Optional[AsyncSession] = None
        self.max_download_size: int = 0

    def open(self) -> None:
        """
        打开下载器，创建 AsyncSession
        """
        if self.session is not None:
            self.logger.warning("CurlCffiDownloader already initialized, skipping")
            return

        super().open()

        # 读取配置
        timeout_secs = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 180, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)
        pool_size = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 20, int)
        self.max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)

        # 浏览器指纹模拟配置
        user_browser_map = safe_get_config(self.crawler.settings, "CURL_BROWSER_VERSION_MAP", {}, dict)
        default_browser_map = self._get_default_browser_map()
        effective_browser_map = {**default_browser_map, **user_browser_map}

        raw_browser_type_str = safe_get_config(self.crawler.settings, "CURL_BROWSER_TYPE", "chrome", str)
        self.browser_type_str = effective_browser_map.get(raw_browser_type_str.lower(), raw_browser_type_str)

        # 创建持久化 session
        self.session = AsyncSession(
            timeout=timeout_secs,
            verify=verify_ssl,
            max_clients=pool_size,
            impersonate=self.browser_type_str,
        )

        self.logger.debug("CurlCffiDownloader initialized.")

    @staticmethod
    def _get_default_browser_map() -> Dict[str, str]:
        """获取代码中硬编码的默认浏览器映射"""
        return {
            "chrome": "chrome136",
            "edge": "edge101",
            "safari": "safari184",
            "firefox": "firefox135",
        }

    async def download(self, request) -> Optional[Response]:
        """
        下载请求并返回响应

        Args:
            request: 请求对象

        Returns:
            Response: 响应对象
        """
        if not self.session:
            self.logger.error("CurlCffiDownloader session is not open.")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        try:
            kwargs = self._build_request_kwargs(request)
            method = request.method.lower()

            if not hasattr(self.session, method):
                raise ValueError(f"不支持的 HTTP 方法: {request.method}")

            method_func = getattr(self.session, method)
            response = await method_func(request.url, **kwargs)

            # 检查 Content-Length
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    cl = int(content_length)
                    if cl > self.max_download_size:
                        raise OverflowError(f"响应过大 (Content-Length): {cl} > {self.max_download_size}")
                except ValueError:
                    self.logger.warning(f"无效的 Content-Length 头部: {content_length}")

            body = response.content
            actual_size = len(body)

            if actual_size > self.max_download_size:
                raise OverflowError(f"响应体过大: {actual_size} > {self.max_download_size}")

            # 记录下载统计
            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s, size: {actual_size} bytes")

            return self._structure_response(request, response, body)

        except Exception as e:
            self._handle_download_error(request, e)
            return None

    def _build_request_kwargs(self, request) -> Dict[str, Any]:
        """
        构造 curl-cffi 请求参数（支持 str 和 dict 格式 proxy）

        Args:
            request: 请求对象

        Returns:
            Dict[str, Any]: 请求参数字典
        """
        request_headers = getattr(request, 'headers', {}) or {}
        headers = {**self.default_headers, **request_headers} if hasattr(self, 'default_headers') else request_headers

        kwargs = {
            "headers": headers,
            "cookies": getattr(request, 'cookies', {}) or {},
            "allow_redirects": getattr(request, 'allow_redirects', True),
        }

        # 处理代理（由 ProxyMiddleware 分配）
        proxy = getattr(request, 'proxy', None)
        if proxy is not None:
            if isinstance(proxy, str):
                if proxy.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
                    kwargs["proxies"] = {"http": proxy, "https": proxy}
                else:
                    self.logger.warning(f"代理协议未知，尝试直接使用: {proxy}")
                    kwargs["proxies"] = {"http": proxy, "https": proxy}
            elif isinstance(proxy, dict):
                kwargs["proxies"] = proxy
            else:
                self.logger.error(f"不支持的 proxy 类型: {type(proxy)}，值: {proxy}")

        # 处理通过 meta 传递的代理认证信息
        proxy_auth_header = request.headers.get("Proxy-Authorization") or request.meta.get("proxy_auth_header")
        if proxy_auth_header:
            kwargs["headers"]["Proxy-Authorization"] = proxy_auth_header

        # 请求体处理
        if hasattr(request, "_json_body") and request._json_body is not None:
            kwargs["json"] = request._json_body
        elif isinstance(getattr(request, 'body', None), (dict, list)):
            kwargs["json"] = request.body
        elif getattr(request, 'body', None) is not None:
            kwargs["data"] = request.body

        return kwargs

    @staticmethod
    def _structure_response(request, response, body: bytes) -> Response:
        """
        构造框架所需的 Response 对象

        Args:
            request: 请求对象
            response: curl-cffi 响应对象
            body: 响应体

        Returns:
            Response: 框架响应对象
        """
        return Response(
            url=str(response.url),
            headers=dict(response.headers),
            status_code=response.status_code,
            body=body,
            request=request,
        )

    def _handle_download_error(self, request, error: Exception) -> None:
        """
        处理下载错误

        Args:
            request: 请求对象
            error: 错误信息
        """
        error_type = type(error).__name__
        if "CurlError" in error_type or "ClientError" in error_type:
            self.logger.error(f"Client error for {request.url}: {error}")
        elif "TimeoutError" in error_type:
            self.logger.error(f"Timeout error for {request.url}: {error}")
        elif isinstance(error, OverflowError):
            self.logger.error(f"Response size error for {request.url}: {error}")
        else:
            self.logger.error(f"Unexpected error for {request.url}: {error}", exc_info=True)

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session:
            self.logger.debug("Closing CurlCffiDownloader session...")
            try:
                await self.session.close()
            except Exception as e:
                self.logger.warning(f"Error during session close: {e}")
            finally:
                self.session = None

        self.logger.debug("CurlCffiDownloader closed.")
