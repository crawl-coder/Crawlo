#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
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
        timeout_secs = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 15, int)
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

        self.logger.info(
            f"CurlCffiDownloader initialized with timeout {timeout_secs}s "
            f"(browser={self.browser_type_str}, max_clients={pool_size})"
        )

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
            # 检查是否为重试请求
            is_retry = request.meta.get("retry_times", 0) > 0

            # 重试请求直连超时保护
            # 基于 DOWNLOAD_TIMEOUT 动态计算，但比正常请求更严格
            # 默认 timeout_secs=15: 正常=15s, 重试=10.1s
            if is_retry:
                timeout_secs = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 15, int)
                strict_timeout = min(10.1, timeout_secs * 0.67)
                # 使用 asyncio.wait_for 强制超时保护
                response = await asyncio.wait_for(
                    self._download_with_timeout(request, strict_timeout),
                    timeout=strict_timeout
                )
            else:
                response = await self._download_with_timeout(request)

            # 记录下载统计
            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")

            return response

        except Exception as e:
            # 网络异常：重新抛出，交由 RetryMiddleware 处理
            # 使用 DEBUG 级别，不打印堆栈
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise

    async def _download_with_timeout(self, request, timeout: Optional[float] = None) -> Response:
        """
        执行下载操作，支持自定义超时

        Args:
            request: 请求对象
            timeout: 自定义超时配置（可选，秒）

        Returns:
            Response: 响应对象
        """
        # 如果有自定义超时，需要创建临时 session
        if timeout is not None:
            verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)
            pool_size = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 20, int)
            
            async with AsyncSession(
                timeout=timeout,
                verify=verify_ssl,
                max_clients=pool_size,
                impersonate=self.browser_type_str,
            ) as temp_session:
                return await self._execute_download(temp_session, request)
        else:
            # 使用默认 session
            return await self._execute_download(self.session, request)

    async def _execute_download(self, session, request) -> Response:
        """
        执行实际的下载操作

        Args:
            session: AsyncSession 实例
            request: 请求对象

        Returns:
            Response: 响应对象
        """
        kwargs = self._build_request_kwargs(request)
        method = request.method.lower()

        if not hasattr(session, method):
            raise ValueError(f"不支持的 HTTP 方法: {request.method}")

        method_func = getattr(session, method)
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

        # 记录下载大小
        self.logger.debug(f"Downloaded {request.url}, size: {actual_size} bytes")

        return self._structure_response(request, response, body)

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
            status=response.status,
            body=body,
            request=request,
        )

    async def _handle_download_error(self, request, error: Exception) -> None:
        """
        处理下载错误，不在此处重试，交由框架的 RetryMiddleware 处理

        Args:
            request: 请求对象
            error: 错误信息
        """
        error_type = type(error).__name__
        
        # 不在此处重试，避免与中间件重试逻辑冲突
        # 框架的 RetryMiddleware 会处理重试
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
