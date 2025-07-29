#!/usr/bin/python
# -*- coding: UTF-8 -*-
from typing import Optional
from aiohttp import (
    ClientSession,
    TCPConnector,
    ClientTimeout,
    TraceConfig,
    ClientResponse, ClientError,
)

from crawlo import Response
from crawlo.downloader import DownloaderBase


class AioHttpDownloader(DownloaderBase):
    """
    高性能异步下载器
    - 基于持久化 ClientSession
    - 智能识别 Request 的高层语义（json_body/form_data）
    - 支持 GET/POST/PUT/DELETE 等方法
    - 内存安全防护
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.session: Optional[ClientSession] = None
        self.max_download_size: int = 0

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
        利用 aiohttp 内建方法（.get/.post 等），避免重复代码。
        """
        method = request.method.lower()
        if not hasattr(session, method):
            raise ValueError(f"Unsupported HTTP method: {request.method}")

        method_func = getattr(session, method)

        # 构造参数
        kwargs = {
            "headers": request.headers,
            "cookies": request.cookies,
            "proxy": request.proxy,
            "allow_redirects": request.allow_redirects,
        }

        # 关键优化：如果原始请求使用了 json_body，则使用 json= 参数
        if hasattr(request, "_json_body") and request._json_body is not None:
            kwargs["json"] = request._json_body  # 让 aiohttp 自动处理序列化 + Content-Type
        elif isinstance(request.body, (dict, list)):
            # 兼容直接传 body=dict 的旧写法
            kwargs["json"] = request.body
        else:
            # 其他情况（表单、bytes、str）走 data=
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
        self.logger.debug(f"Requesting: {params.method} {params.url}")

    async def _on_request_end(self, session, trace_config_ctx, params):
        """请求成功结束时的回调。"""
        # 正确方式：直接从 params 获取响应对象
        response = params.response
        self.logger.debug(
            f"Finished: {params.method} {params.url} with status {response.status}"
        )

    async def _on_request_exception(self, session, trace_config_ctx, params):
        """请求发生异常时的回调。"""
        # 正确方式：通过 .exception 属性获取异常
        exc = trace_config_ctx.exception
        self.logger.warning(
            f"Failed: {params.method} {params.url} with exception {type(exc).__name__}: {exc}"
        )

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session and not self.session.closed:
            self.logger.info("Closing AioHttpDownloader session...")
            await self.session.close()
        self.logger.debug("AioHttpDownloader closed.")