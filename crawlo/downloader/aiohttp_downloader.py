#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import time
import socket
from yarl import URL
from typing import Optional, TYPE_CHECKING, Union, Dict, Any
from aiohttp import (
    ClientSession,
    TCPConnector,
    ClientTimeout,
    TraceConfig,
    ClientResponse,
    ClientError,
    BasicAuth,
)

from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.downloader import DownloaderBase

if TYPE_CHECKING:
    from crawlo.network.request import Request
    from crawlo.crawler import Crawler


class AioHttpDownloader(DownloaderBase):
    """
    高性能异步下载器
    - 基于持久化 ClientSession
    - 智能识别 Request 的高层语义（json_body/form_data）
    - 支持 GET/POST/PUT/DELETE 等方法
    - 支持中间件设置的 IP 代理（HTTP/HTTPS）
    - 内存安全防护
    """

    def __init__(self, crawler: 'Crawler') -> None:
        """
        初始化 AioHttp 下载器
        
        Args:
            crawler: 爬虫实例
        """
        super().__init__(crawler)
        self.session: Optional[ClientSession] = None
        self.max_download_size: int = 0
        self.logger = get_logger(self.__class__.__name__)

    def open(self) -> None:
        """
        打开下载器，创建 ClientSession
        """
        super().open()
        # 恢复关键的下载器启动信息为INFO级别
        # 读取配置
        from crawlo.utils.misc import safe_get_config
        timeout_secs = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 30, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 300, int)  # 从200增加到300
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 100, int)  # 从50增加到100
        self.max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)  # 10MB

        # 创建连接器
        connector = TCPConnector(
            verify_ssl=verify_ssl,
            limit=pool_limit,
            limit_per_host=pool_per_host,
            ttl_dns_cache=300,
            keepalive_timeout=15,
            force_close=False,
            use_dns_cache=True,  # 启用DNS缓存
            family=socket.AF_UNSPEC,  # 允许IPv4和IPv6
        )

        # 超时控制 - 增加更多超时设置
        timeout = ClientTimeout(
            total=timeout_secs,
            connect=timeout_secs/2,  # 连接超时
            sock_read=timeout_secs,  # 读取超时
            sock_connect=timeout_secs/2  # socket连接超时
        )

        # 请求追踪
        trace_config = TraceConfig()
        trace_config.on_request_start.append(self._on_request_start)
        trace_config.on_request_end.append(self._on_request_end)
        trace_config.on_request_exception.append(self._on_request_exception)

        # 创建全局 session
        self.session = ClientSession(
            connector=connector,
            timeout=timeout,
            trace_configs=[trace_config],
            auto_decompress=True,
        )

        # 输出下载器配置摘要
        spider_name = getattr(self.crawler.spider, 'name', 'Unknown')
        concurrency = safe_get_config(self.crawler.settings, 'CONCURRENCY', 4, int)

    async def download(self, request: 'Request') -> Response:
        """
        下载请求并返回响应
        
        Args:
            request: 请求对象
            
        Returns:
            Response: 响应对象
        """
        if not self.session or self.session.closed:
            self.logger.error("AioHttpDownloader session is not open.")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        try:
            # 使用通用发送逻辑（支持所有 HTTP 方法）
            async with await self._send_request(self.session, request) as resp:
                # 安全检查：防止大响应体导致 OOM
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > self.max_download_size:
                    raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

                body = await resp.read()
                response = self._structure_response(request, resp, body)
                
                # 记录下载统计
                if start_time:
                    download_time = time.time() - start_time
                    self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s, size: {len(body)} bytes")
                
                return response

        except ClientError as e:
            self.logger.error(f"Client error for {request.url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {request.url}: {e}", exc_info=True)
            return None

    @staticmethod
    async def _send_request(session: ClientSession, request: 'Request') -> ClientResponse:
        """
        根据请求方法和高层语义智能发送请求。
        支持中间件设置的 proxy，兼容以下格式：
            - str: "http://user:pass@host:port"
            - dict: {"http": "...", "https": "..."} （自动取 http 或 https 字段）
            
        Args:
            session: ClientSession 实例
            request: 请求对象
            
        Returns:
            ClientResponse: 响应对象
        """
        method = request.method.lower()
        if not hasattr(session, method):
            raise ValueError(f"Unsupported HTTP method: {request.method}")

        method_func = getattr(session, method)

        # 构造参数
        kwargs: Dict[str, Any] = {
            "headers": request.headers,
            "cookies": request.cookies,
            "allow_redirects": request.allow_redirects,
        }

        # === 处理代理（proxy）===
        proxy = getattr(request, "proxy", None)
        proxy_auth = None

        if proxy:
            # 兼容字典格式：{"http": "http://...", "https": "http://..."}
            if isinstance(proxy, dict):
                # 优先使用 https，否则用 http
                proxy = proxy.get("https") or proxy.get("http")

            if not isinstance(proxy, (str, URL)):
                raise ValueError(f"proxy must be str or URL, got {type(proxy)}")

            try:
                proxy_url = URL(proxy)
                if proxy_url.scheme not in ("http", "https"):
                    raise ValueError(f"Unsupported proxy scheme: {proxy_url.scheme}, only HTTP/HTTPS supported.")

                # 提取认证信息
                if proxy_url.user and proxy_url.password:
                    proxy_auth = BasicAuth(proxy_url.user, proxy_url.password)
                    # 去掉用户密码的 URL
                    proxy = str(proxy_url.with_user(None))
                else:
                    proxy = str(proxy_url)

                kwargs["proxy"] = proxy
                if proxy_auth:
                    kwargs["proxy_auth"] = proxy_auth

            except Exception as e:
                raise ValueError(f"Invalid proxy URL: {proxy}") from e

        # 处理通过meta传递的代理认证信息
        meta_proxy_auth = request.meta.get("proxy_auth")
        if meta_proxy_auth and isinstance(meta_proxy_auth, dict):
            username = meta_proxy_auth.get("username")
            password = meta_proxy_auth.get("password")
            if username and password:
                kwargs["proxy_auth"] = BasicAuth(username, password)

        # === 处理请求体 ===
        if hasattr(request, "_json_body") and request._json_body is not None:
            kwargs["json"] = request._json_body
        elif isinstance(request.body, (dict, list)):
            kwargs["json"] = request.body
        else:
            if request.body is not None:
                kwargs["data"] = request.body

        return await method_func(request.url, **kwargs)

    @staticmethod
    def _structure_response(request: 'Request', resp: ClientResponse, body: bytes) -> Response:
        """
        构造框架所需的 Response 对象
        
        Args:
            request: 请求对象
            resp: aiohttp 响应对象
            body: 响应体
            
        Returns:
            Response: 框架响应对象
        """
        return Response(
            url=str(resp.url),
            headers=dict(resp.headers),
            status_code=resp.status,
            body=body,
            request=request,
        )

    # --- 请求追踪日志 ---
    async def _on_request_start(self, session: ClientSession, trace_config_ctx: Any, params: Any) -> None:
        """
        请求开始时的回调。
        
        Args:
            session: ClientSession 实例
            trace_config_ctx: 追踪配置上下文
            params: 参数
        """
        pass

    async def _on_request_end(self, session: ClientSession, trace_config_ctx: Any, params: Any) -> None:
        """
        请求成功结束时的回调。
        
        Args:
            session: ClientSession 实例
            trace_config_ctx: 追踪配置上下文
            params: 参数
        """
        pass

    async def _on_request_exception(self, session: ClientSession, trace_config_ctx: Any, params: Any) -> None:
        """
        请求发生异常时的回调。
        
        Args:
            session: ClientSession 实例
            trace_config_ctx: 追踪配置上下文
            params: 参数
        """
        pass

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session and not self.session.closed:
            self.logger.info("Closing AioHttpDownloader session...")
            try:
                # 关闭 session
                await self.session.close()
                
                # 等待一小段时间确保连接完全关闭
                # 参考: https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
                await asyncio.sleep(0.25)
            except Exception as e:
                self.logger.warning(f"Error during session close: {e}")
            finally:
                self.session = None
        
        self.logger.debug("AioHttpDownloader closed.")