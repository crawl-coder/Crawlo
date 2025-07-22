#!/usr/bin/python
# -*- coding:UTF-8 -*-
import httpx
from typing import Optional
from httpx import AsyncClient, Timeout, Limits

from crawlo import Response
from crawlo.downloader import DownloaderBase


class HttpXDownloader(DownloaderBase):
    """
    基于 httpx 的高性能异步下载器
    - 使用持久化 AsyncClient（推荐做法）
    - 支持连接池、HTTP/2、透明代理
    - 智能处理 Request 的 json_body 和 form_data
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: Optional[AsyncClient] = None
        self._timeout: Optional[Timeout] = None
        self._limits: Optional[Limits] = None

    def open(self):
        super().open()
        self.logger.info("Opening HttpXDownloader")

        # 读取配置
        timeout_total = self.crawler.settings.get_int("DOWNLOAD_TIMEOUT", 30)
        pool_limit = self.crawler.settings.get_int("CONNECTION_POOL_LIMIT", 100)
        pool_per_host = self.crawler.settings.get_int("CONNECTION_POOL_LIMIT_PER_HOST", 20)
        max_download_size = self.crawler.settings.get_int("DOWNLOAD_MAXSIZE", 10 * 1024 * 1024)  # 10MB

        # 保存配置
        self.max_download_size = max_download_size

        # 配置超时（更精细）
        self._timeout = Timeout(
            connect=10.0,  # 建立连接超时
            read=timeout_total - 10.0 if timeout_total > 10 else timeout_total / 2,  # 读取数据超时
            write=10.0,   # 发送数据超时
            pool=1.0      # 从连接池获取连接的超时
        )

        # 配置连接池限制
        self._limits = Limits(
            max_connections=pool_limit,
            max_keepalive_connections=pool_per_host
        )

        # 创建持久化客户端
        # verify=False 对应 VERIFY_SSL=False
        verify_ssl = self.crawler.settings.get_bool("VERIFY_SSL", True)

        self._client = AsyncClient(
            timeout=self._timeout,
            limits=self._limits,
            verify=verify_ssl,
            http2=True,  # 启用 HTTP/2 支持
            follow_redirects=True,  # 自动跟随重定向
        )

        self.logger.debug("HttpXDownloader initialized.")

    async def download(self, request) -> Optional[Response]:
        if not self._client:
            raise RuntimeError("HttpXDownloader client is not available.")

        try:
            # 构造发送参数
            kwargs = {
                "url": request.url,
                "headers": request.headers,
                "cookies": request.cookies,
                "follow_redirects": request.allow_redirects,
            }

            # 智能处理 body（关键优化）
            if hasattr(request, "_json_body") and request._json_body is not None:
                kwargs["json"] = request._json_body  # 让 httpx 处理序列化
            elif isinstance(request.body, (dict, list)):
                kwargs["json"] = request.body
            else:
                kwargs["content"] = request.body  # 使用 content 而不是 data

            # 设置代理
            if request.proxy:
                kwargs["proxy"] = request.proxy

            # 发送请求
            response = await self._client.request(
                method=request.method,
                **kwargs
            )

            # 安全检查：防止大响应体
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_download_size:
                response.close()  # 立即关闭连接，释放资源
                raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

            # 读取响应体
            body = await response.aread()

            return self.structure_response(request=request, response=response, body=body)

        except httpx.TimeoutException as e:
            self.logger.error(f"Timeout error for {request.url}: {e}")
            raise
        except httpx.NetworkError as e:
            self.logger.error(f"Network error for {request.url}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP {e.response.status_code} for {request.url}: {e}")
            # 即使是 4xx/5xx，也返回 Response，由上层逻辑（如 spider）处理
            # 如果需要在此处 raise，可取消注释下一行
            # raise
            return self.structure_response(request=request, response=e.response, body=b"")
        except Exception as e:
            self.logger.critical(f"Unexpected error for {request.url}: {e}", exc_info=True)
            raise

    @staticmethod
    def structure_response(request, response, body: bytes) -> Response:
        return Response(
            url=str(response.url),  # httpx 的 URL 是对象，需转字符串
            headers=dict(response.headers),
            status_code=response.status_code,
            body=body,
            request=request
        )

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            self.logger.info("Closing HttpXDownloader client...")
            await self._client.aclose()
        self.logger.debug("HttpXDownloader closed.")
# #!/usr/bin/python
# # -*- coding:UTF-8 -*-
# from typing import Optional
# from httpx import AsyncClient, Timeout
#
# from crawlo import Response
# from crawlo.downloader import DownloaderBase
#
#
# class HttpXDownloader(DownloaderBase):
#     def __init__(self, crawler):
#         super().__init__(crawler)
#         self._client: Optional[AsyncClient] = None
#         self._timeout: Optional[Timeout] = None
#
#     def open(self):
#         super().open()
#         timeout = self.crawler.settings.get_int("DOWNLOAD_TIMEOUT")
#         self._timeout = Timeout(timeout=timeout)
#
#     async def download(self, request) -> Optional[Response]:
#         try:
#             proxies = None
#             async with AsyncClient(timeout=self._timeout, proxy=proxies) as client:
#                 self.logger.debug(f"request downloading: {request.url}，method: {request.method}")
#                 response = await client.request(
#                     url=request.url,
#                     method=request.method,
#                     headers=request.headers,
#                     cookies=request.cookies,
#                     data=request.body
#                 )
#                 body = await response.aread()
#         except Exception as exp:
#             self.logger.error(f"Error downloading {request}: {exp}")
#             raise exp
#
#         return self.structure_response(request=request, response=response, body=body)
#
#     @staticmethod
#     def structure_response(request, response, body) -> Response:
#         return Response(
#             url=response.url,
#             headers=dict(response.headers),
#             status_code=response.status_code,
#             body=body,
#             request=request
#         )