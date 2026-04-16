#!/usr/bin/python
# -*- coding:UTF-8 -*-
import httpx
from typing import Optional

from httpx import HTTPStatusError
from httpx import AsyncClient, Timeout, Limits

from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config


class HttpXDownloader(DownloaderBase):
    """
    基于 httpx 的高性能异步下载器
    - 使用持久化 AsyncClient（推荐做法）
    - 支持连接池、HTTP/2、透明代理
    - 智能处理 Request 的 json_body 和 form_data
    - 支持代理失败后自动降级为直连
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: Optional[AsyncClient] = None
        self._client_timeout: Optional[Timeout] = None
        self._client_limits: Optional[Limits] = None
        self._client_verify: bool = True
        self._client_http2: bool = False
        self.max_download_size: int = 0
        self.logger = get_logger(self.__class__.__name__)

    def open(self) -> None:
        """初始化下载器，创建持久化 AsyncClient"""
        super().open()
        
        # 读取配置
        timeout_total = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 30, int)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int)
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 20, int)
        max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)

        self.max_download_size = max_download_size

        # 配置主客户端的超时和连接池
        self._client_timeout = Timeout(
            connect=10.0,     # 建立连接超时
            read=timeout_total - 10.0 if timeout_total > 10 else timeout_total / 2,  # 读取数据超时
            write=10.0,       # 发送数据超时
            pool=1.0          # 从连接池获取连接的超时
        )
        self._client_limits = Limits(
            max_connections=pool_limit,
            max_keepalive_connections=pool_per_host
        )
        self._client_verify = verify_ssl
        self._client_http2 = True  # 启用 HTTP/2 支持

        # 创建持久化客户端（不设置代理，代理由临时客户端处理）
        self._client = AsyncClient(
            timeout=self._client_timeout,
            limits=self._client_limits,
            verify=self._client_verify,
            http2=self._client_http2,
            follow_redirects=True,  # 自动跟随重定向
        )

        self.logger.debug("HttpXDownloader initialized.")

    async def download(self, request) -> Response:
        """
        执行下载请求，支持代理失败自动降级为直连
        
        流程：
        1. 如果有代理，创建临时客户端（严格超时）
        2. 发送请求，网络异常时降级为直连
        3. 安全检查、读取响应、返回结果
        """
        if not self._client:
            self.logger.error("HttpXDownloader client is not available.")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            import time
            start_time = time.time()

        # 初始化客户端变量
        effective_client = self._client  # 默认使用主客户端（直连）
        temp_client = None               # 临时客户端（代理模式）

        try:
            # 构造请求参数
            kwargs = {
                "method": request.method,
                "url": request.url,
                "headers": request.headers,
                "cookies": request.cookies,
                "follow_redirects": request.allow_redirects,
            }

            # 处理请求体
            if hasattr(request, "_json_body") and request._json_body is not None:
                kwargs["json"] = request._json_body  # JSON 格式
            elif isinstance(request.body, (dict, list)):
                kwargs["json"] = request.body        # 字典/列表转 JSON
            else:
                kwargs["content"] = request.body     # 原始字节数据

            # 处理代理配置
            httpx_proxy_config = None
            if request.proxy:
                if isinstance(request.proxy, str):
                    # 字符串格式：直接使用
                    httpx_proxy_config = request.proxy
                elif isinstance(request.proxy, dict):
                    # 字典格式：根据协议选择
                    from urllib.parse import urlparse
                    request_scheme = urlparse(request.url).scheme
                    if request_scheme == "https" and request.proxy.get("https"):
                        httpx_proxy_config = request.proxy["https"]
                    elif request.proxy.get("http"):
                        httpx_proxy_config = request.proxy["http"]
                    else:
                        # 兜底：使用任意可用代理
                        httpx_proxy_config = next(iter(request.proxy.values()), None)
                        if httpx_proxy_config:
                            self.logger.warning(
                                f"No specific proxy for scheme '{request_scheme}', using '{httpx_proxy_config}'"
                            )

                # 创建临时客户端（代理模式）
                if httpx_proxy_config:
                    try:
                        # 代理客户端使用更严格的超时（快速失败）
                        proxy_timeout = Timeout(
                            connect=5.0,   # 连接超时
                            read=8.0,      # 读取超时
                            write=5.0,     # 写入超时
                            pool=1.0       # 连接池超时
                        )
                        
                        temp_client = AsyncClient(
                            timeout=proxy_timeout,
                            limits=self._client_limits,
                            verify=self._client_verify,
                            http2=self._client_http2,
                            follow_redirects=True,
                            proxy=httpx_proxy_config
                        )
                        effective_client = temp_client
                        self.logger.info(f"Using proxy: {httpx_proxy_config} for {request.url}")
                    except Exception as e:
                        # 临时客户端创建失败，快速失败
                        # 重试和降级由 RetryMiddleware 处理
                        self.logger.error(
                            f"Failed to create proxy client {httpx_proxy_config} for {request.url}: {e}")
                        return None

            # 发送请求
            httpx_response = await effective_client.request(**kwargs)

            # 安全检查：防止大响应体导致 OOM
            content_length = httpx_response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_download_size:
                await httpx_response.aclose()
                raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

            # 读取响应体
            body = await httpx_response.aread()

            # 记录下载统计
            if start_time:
                import time
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s, size: {len(body)} bytes")

            # 构造并返回 Response
            return self.structure_response(request=request, response=httpx_response, body=body)

        except HTTPStatusError as e:
            # HTTP 状态码错误（4xx/5xx）：返回 Response 由上层处理
            self.logger.warning(f"HTTP {e.response.status_code} for {request.url}: {e}")
            try:
                error_body = await e.response.aread()
            except Exception:
                error_body = b""
            return self.structure_response(request=request, response=e.response, body=error_body)
        except Exception as e:
            # 网络异常（超时、连接错误等）：重新抛出，交由 RetryMiddleware 处理
            # 使用 DEBUG 级别，不打印堆栈，因为异常会被重试中间件统一处理
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise  # 重新抛出异常

        finally:
            # 清理：关闭临时客户端（如果存在）
            if temp_client:
                try:
                    await temp_client.aclose()
                except Exception as e:
                    self.logger.warning(f"Error closing temporary client: {e}")

    @staticmethod
    def structure_response(request, response: httpx.Response, body: bytes) -> Response:
        """构造框架标准的 Response 对象"""
        return Response(
            url=str(response.url),
            headers=dict(response.headers),
            status=response.status_code,
            body=body,
            request=request
        )

    async def close(self) -> None:
        """关闭下载器，释放主客户端资源"""
        if self._client:
            self.logger.debug("Closing HttpXDownloader client...")
            try:
                await self._client.aclose()
            except Exception as e:
                self.logger.warning(f"Error during client close: {e}")
            finally:
                self._client = None
        
        self.logger.debug("HttpXDownloader closed.")
