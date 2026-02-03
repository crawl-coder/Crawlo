#!/usr/bin/python
# -*- coding:UTF-8 -*-
import time
from typing import Optional, Dict, Any, Union
from urllib.parse import urlparse

import httpx
from httpx import AsyncClient, Timeout, Limits

try:
    from httpcore import ProxyError as HttpCoreProxyError
except ImportError:
    HttpCoreProxyError = None

from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.utils.misc import safe_get_config


class HttpXDownloader(DownloaderBase):
    """
    基于 httpx 的高性能异步下载器
    - 使用持久化 AsyncClient（推荐做法）
    - 支持连接池、HTTP/2、透明代理
    - 智能处理 Request 的 json_body 和 form_data
    - 代理由 ProxyMiddleware 统一管理
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: Optional[AsyncClient] = None
        self._client_timeout: Optional[Timeout] = None
        self._client_limits: Optional[Limits] = None
        self._client_verify: bool = True
        self._client_http2: bool = False
        self.max_download_size: int = 0

    def open(self) -> None:
        """
        打开下载器，创建 AsyncClient
        """
        if self._client is not None:
            self.logger.warning("HttpXDownloader already initialized, skipping")
            return

        super().open()

        # 读取配置 - 使用统一的安全获取方式
        timeout_total = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 30, int)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int)
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 20, int)
        max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)
        enable_http2 = safe_get_config(self.crawler.settings, "HTTP2_ENABLED", True, bool)

        # 保存配置
        self.max_download_size = max_download_size

        # 保存客户端配置以便复用
        self._client_timeout = Timeout(
            connect=10.0,
            read=timeout_total - 10.0 if timeout_total > 10 else timeout_total / 2,
            write=10.0,
            pool=1.0
        )
        self._client_limits = Limits(
            max_connections=pool_limit,
            max_keepalive_connections=pool_per_host
        )
        self._client_verify = verify_ssl
        self._client_http2 = enable_http2

        # 创建持久化客户端
        self._client = AsyncClient(
            timeout=self._client_timeout,
            limits=self._client_limits,
            verify=self._client_verify,
            http2=self._client_http2,
            follow_redirects=True,
        )

        self.logger.debug("HttpXDownloader initialized.")

    async def download(self, request: Request) -> Optional[Response]:
        """下载请求并返回响应"""
        if not self._client:
            self.logger.error("HttpXDownloader client is not available.")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        kwargs = self._build_request_kwargs(request)

        # 如果请求有代理，创建临时客户端（由 ProxyMiddleware 分配）
        client_to_use = self._client
        if request.proxy:
            proxy_config = self._parse_proxy_config(request.proxy, request.url)
            if proxy_config:
                try:
                    client_to_use = AsyncClient(
                        timeout=self._client_timeout,
                        limits=self._client_limits,
                        verify=self._client_verify,
                        http2=self._client_http2,
                        follow_redirects=True,
                        proxy=proxy_config
                    )
                    self.logger.debug(f"Using temporary client with proxy: {proxy_config} for {request.url}")
                except Exception as e:
                    self.logger.error(f"Failed to create client with proxy: {e}")
                    return None

        try:
            httpx_response = await client_to_use.request(**kwargs)
            return await self._process_response(request, httpx_response, start_time)
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP {e.response.status_code} for {request.url}: {e}")
            try:
                error_body = await e.response.aread() if hasattr(e.response, 'aread') else e.response.content
            except Exception:
                error_body = b""
            return self.structure_response(request=request, response=e.response, body=error_body)
        except httpx.ProxyError as e:
            self.logger.warning(f"Proxy error for {request.url}: {e}")
            raise
        except Exception as e:
            if HttpCoreProxyError and isinstance(e, HttpCoreProxyError):
                self.logger.warning(f"Proxy error (httpcore) for {request.url}: {e}")
                raise httpx.ProxyError(str(e)) from e
            
            self._handle_download_error(request, e)
            raise
        finally:
            # 如果使用了临时客户端，关闭它
            if client_to_use is not self._client:
                try:
                    await client_to_use.aclose()
                except Exception as e:
                    self.logger.warning(f"Error closing temporary client: {e}")

    def _build_request_kwargs(self, request: Request) -> Dict[str, Any]:
        """
        构建发送请求所需的参数字典

        Args:
            request: 请求对象

        Returns:
            Dict[str, Any]: 请求参数字典
        """
        kwargs = {
            "method": request.method,
            "url": request.url,
            "headers": request.headers,
            "cookies": request.cookies,
            "follow_redirects": request.allow_redirects,
        }

        # 智能处理 body（关键优化）
        if hasattr(request, "_json_body") and request._json_body is not None:
            kwargs["json"] = request._json_body
        elif isinstance(request.body, (dict, list)):
            kwargs["json"] = request.body
        else:
            kwargs["content"] = request.body

        return kwargs

    def _parse_proxy_config(self, proxy: Union[str, Dict[str, str]], url: str) -> Optional[str]:
        """
        解析代理配置，返回 httpx 可用的代理 URL

        Args:
            proxy: 代理配置（字符串或字典）
            url: 请求 URL

        Returns:
            Optional[str]: httpx 可用的代理 URL
        """
        if isinstance(proxy, str):
            return proxy

        if isinstance(proxy, dict):
            request_scheme = urlparse(url).scheme
            if request_scheme == "https" and proxy.get("https"):
                return proxy["https"]
            elif proxy.get("http"):
                return proxy["http"]
            else:
                # 如果没有匹配的，尝试使用任意一个
                httpx_proxy_config = next(iter(proxy.values()), None)
                if httpx_proxy_config:
                    self.logger.warning(
                        f"No specific proxy for scheme '{request_scheme}', using '{httpx_proxy_config}'"
                    )
                return httpx_proxy_config

        return None

    async def _process_response(
        self,
        request: Request,
        httpx_response: httpx.Response,
        start_time: float
    ) -> Response:
        """
        处理响应，包括大小检查、读取响应体、记录统计

        Args:
            request: 请求对象
            httpx_response: httpx 响应对象
            start_time: 开始时间（用于统计）

        Returns:
            Response: 处理后的响应对象

        Raises:
            OverflowError: 响应体过大
        """
        content_length = httpx_response.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_download_size:
            await httpx_response.aclose()
            raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

        body = await httpx_response.aread() if hasattr(httpx_response, 'aread') else httpx_response.content

        if start_time:
            download_time = time.time() - start_time
            self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s, size: {len(body)} bytes")

        return self.structure_response(request=request, response=httpx_response, body=body)

    def _handle_download_error(self, request: Request, error: Exception) -> None:
        """
        处理下载错误

        Args:
            request: 请求对象
            error: 错误信息
        """
        if isinstance(error, httpx.TimeoutException):
            self.logger.error(f"Timeout error for {request.url}: {error}")
        elif isinstance(error, httpx.NetworkError):
            self.logger.error(f"Network error for {request.url}: {error}")
        elif isinstance(error, httpx.HTTPStatusError):
            self.logger.warning(f"HTTP {error.response.status_code} for {request.url}: {error}")
        elif isinstance(error, OverflowError):
            self.logger.error(f"Response size error for {request.url}: {error}")
        else:
            self.logger.error(f"Unexpected error for {request.url}: {error}", exc_info=True)

    @staticmethod
    def structure_response(request: Request, response: httpx.Response, body: bytes) -> Response:
        """
        构造 Response 对象

        Args:
            request: 请求对象
            response: httpx 响应对象
            body: 响应体

        Returns:
            Response: 响应对象
        """
        return Response(
            url=str(response.url),
            headers=dict(response.headers),
            status_code=response.status_code,
            body=body,
            request=request
        )

    async def close(self) -> None:
        """关闭主客户端"""
        if self._client:
            self.logger.debug("Closing HttpXDownloader client...")
            try:
                await self._client.aclose()
            except Exception as e:
                self.logger.warning(f"Error during client close: {e}")
            finally:
                self._client = None

        self.logger.debug("HttpXDownloader closed.")
