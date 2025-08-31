#!/usr/bin/python
# -*- coding: UTF-8 -*-
from yarl import URL
from typing import Optional
from aiohttp import (
    ClientSession,
    TCPConnector,
    ClientTimeout,
    TraceConfig,
    ClientResponse,
    ClientError,
    BasicAuth,
)

from crawlo import Response
from crawlo.utils.log import get_logger
from crawlo.downloader import DownloaderBase


class AioHttpDownloader(DownloaderBase):
    """
    高性能异步下载器
    - 基于持久化 ClientSession
    - 智能识别 Request 的高层语义（json_body/form_data）
    - 支持 GET/POST/PUT/DELETE 等方法
    - 支持中间件设置的 IP 代理（HTTP/HTTPS）
    - 内存安全防护
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.session: Optional[ClientSession] = None
        self.max_download_size: int = 0
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get("LOG_LEVEL"))

    def open(self):
        super().open()
        self.logger.info("Opening AioHttpDownloader")

        # 读取配置
        timeout_secs = self.crawler.settings.get_int("DOWNLOAD_TIMEOUT", 30)
        verify_ssl = self.crawler.settings.get_bool("VERIFY_SSL", True)
        pool_limit = self.crawler.settings.get_int("CONNECTION_POOL_LIMIT", 100)
        pool_per_host = self.crawler.settings.get_int("CONNECTION_POOL_LIMIT_PER_HOST", 20)
        self.max_download_size = self.crawler.settings.get_int("DOWNLOAD_MAXSIZE", 10 * 1024 * 1024)  # 10MB

        # 创建连接器
        connector = TCPConnector(
            verify_ssl=verify_ssl,
            limit=pool_limit,
            limit_per_host=pool_per_host,
            ttl_dns_cache=300,
            keepalive_timeout=15,
            force_close=False,
        )

        # 超时控制
        timeout = ClientTimeout(total=timeout_secs)

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

        self.logger.debug("AioHttpDownloader initialized.")

    async def download(self, request) -> Optional[Response]:
        if not self.session or self.session.closed:
            raise RuntimeError("AioHttpDownloader session is not open.")

        try:
            # 使用通用发送逻辑（支持所有 HTTP 方法）
            async with await self._send_request(self.session, request) as resp:
                # 安全检查：防止大响应体导致 OOM
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > self.max_download_size:
                    raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

                body = await resp.read()
                return self._structure_response(request, resp, body)

        except ClientError as e:
            self.logger.error(f"Client error for {request.url}: {e}")
            raise
        except Exception as e:
            self.logger.critical(f"Unexpected error for {request.url}: {e}", exc_info=True)
            raise

    @staticmethod
    async def _send_request(session: ClientSession, request) -> ClientResponse:
        """
        根据请求方法和高层语义智能发送请求。
        支持中间件设置的 proxy，兼容以下格式：
            - str: "http://user:pass@host:port"
            - dict: {"http": "...", "https": "..."} （自动取 http 或 https 字段）
        """
        method = request.method.lower()
        if not hasattr(session, method):
            raise ValueError(f"Unsupported HTTP method: {request.method}")

        method_func = getattr(session, method)

        # 构造参数
        kwargs = {
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
    def _structure_response(request, resp: ClientResponse, body: bytes) -> Response:
        """构造框架所需的 Response 对象"""
        return Response(
            url=str(resp.url),
            headers=dict(resp.headers),
            status_code=resp.status,
            body=body,
            request=request,
        )

    # --- 请求追踪日志 ---
    async def _on_request_start(self, session, trace_config_ctx, params):
        """请求开始时的回调。"""
        proxy = getattr(params, "proxy", None)
        proxy_info = f" via {proxy}" if proxy else ""
        self.logger.debug(f"Requesting: {params.method} {params.url}{proxy_info}")

    async def _on_request_end(self, session, trace_config_ctx, params):
        """请求成功结束时的回调。"""
        response = params.response
        self.logger.debug(
            f"Finished: {params.method} {params.url} with status {response.status}"
        )

    async def _on_request_exception(self, session, trace_config_ctx, params):
        """请求发生异常时的回调。"""
        exc = params.exception
        self.logger.warning(
            f"Failed: {params.method} {params.url} with exception {type(exc).__name__}: {exc}"
        )

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session and not self.session.closed:
            self.logger.info("Closing AioHttpDownloader session...")
            await self.session.close()
        self.logger.debug("AioHttpDownloader closed.")