#!/usr/bin/python
# -*- coding:UTF-8 -*-
import httpx
from typing import Optional
from httpx import AsyncClient, Timeout, Limits

from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.logging import get_logger

# 尝试导入 httpx 异常，用于更精确地捕获
try:
    # httpx 0.23.0+ 将异常移到了 _exceptions
    from httpx import ConnectError, TimeoutException, NetworkError, HTTPStatusError
except ImportError:
    try:
        # 旧版本可能在 httpcore 或顶层
        from httpcore import ConnectError
        from httpx import TimeoutException, NetworkError, HTTPStatusError
    except ImportError:
        ConnectError = httpx.ConnectError
        TimeoutException = httpx.TimeoutException
        NetworkError = httpx.NetworkError
        HTTPStatusError = httpx.HTTPStatusError

# 定义我们认为是网络问题，应该触发降级的异常
NETWORK_EXCEPTIONS = (ConnectError, TimeoutException, NetworkError)


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
        # ------------------------
        self._timeout: Optional[Timeout] = None
        self._limits: Optional[Limits] = None
        # --- 获取 logger 实例 ---
        self.logger = get_logger(self.__class__.__name__)

    def open(self) -> None:
        """
        打开下载器，创建 AsyncClient
        """
        super().open()
        
        from crawlo.utils.misc import safe_get_config
        
        # 读取配置 - 使用统一的安全获取方式
        timeout_total = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 30, int)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int)
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 20, int)
        max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)

        # 保存配置
        self.max_download_size = max_download_size

        # --- 保存客户端配置以便复用 ---
        self._client_timeout = Timeout(
            connect=10.0,  # 建立连接超时
            read=timeout_total - 10.0 if timeout_total > 10 else timeout_total / 2,  # 读取数据超时
            write=10.0,  # 发送数据超时
            pool=1.0  # 从连接池获取连接的超时
        )
        self._client_limits = Limits(
            max_connections=pool_limit,
            max_keepalive_connections=pool_per_host
        )
        self._client_verify = verify_ssl
        self._client_http2 = True  # 启用 HTTP/2 支持
        # ----------------------------

        # 创建持久化客户端 (不在此处设置全局代理)
        self._client = AsyncClient(
            timeout=self._client_timeout,
            limits=self._client_limits,
            verify=self._client_verify,
            http2=self._client_http2,
            follow_redirects=True,  # 自动跟随重定向
            # 注意：此处不设置 proxy 或 proxies
        )

        self.logger.debug("HttpXDownloader initialized.")

    async def download(self, request) -> Response:
        """下载请求并返回响应，支持代理失败后的优雅降级"""
        if not self._client:
            self.logger.error("HttpXDownloader client is not available.")
            return None

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            import time
            start_time = time.time()

        # --- 1. 确定要使用的 client 实例 ---
        effective_client = self._client  # 默认使用共享的主 client
        temp_client = None  # 用于可能创建的临时 client
        used_proxy = None  # 记录当前尝试使用的代理

        try:
            # --- 2. 构造发送参数 (不包含 proxy/proxies) ---
            kwargs = {
                "method": request.method,
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

            # --- 3. 处理代理 ---
            httpx_proxy_config = None  # 用于初始化临时 client 的代理配置
            if request.proxy:
                # 根据 request.proxy 的类型准备 httpx 的 proxy 参数
                if isinstance(request.proxy, str):
                    # 直接是代理 URL 字符串
                    httpx_proxy_config = request.proxy
                elif isinstance(request.proxy, dict):
                    # 从字典中选择合适的代理 URL
                    # 优先选择与请求协议匹配的，否则 fallback 到 http
                    from urllib.parse import urlparse
                    request_scheme = urlparse(request.url).scheme
                    if request_scheme == "https" and request.proxy.get("https"):
                        httpx_proxy_config = request.proxy["https"]
                    elif request.proxy.get("http"):
                        httpx_proxy_config = request.proxy["http"]
                    else:
                        # 如果没有匹配的，尝试使用任意一个
                        httpx_proxy_config = next(iter(request.proxy.values()), None)
                        if httpx_proxy_config:
                            self.logger.warning(
                                f"No specific proxy for scheme '{request_scheme}', using '{httpx_proxy_config}'"
                            )

                # 如果成功解析出代理配置，则创建临时 client
                if httpx_proxy_config:
                    try:
                        # --- 4. 创建临时 client，配置代理 ---
                        # 使用在 open() 中保存的配置
                        # 确保 _client_limits 不为 None
                        client_limits = self._client_limits or Limits(
                            max_connections=100,
                            max_keepalive_connections=20
                        )
                        
                        # 为代理请求设置更严格的超时控制
                        proxy_timeout = Timeout(
                            connect=5.0,  # 缩短连接超时
                            read=20.0,    # 读取超时
                            write=10.0,   # 写入超时
                            pool=1.0      # 连接池超时
                        )
                        
                        temp_client = AsyncClient(
                            timeout=proxy_timeout,
                            limits=client_limits,
                            verify=self._client_verify,
                            http2=self._client_http2,
                            follow_redirects=True,  # 确保继承
                            proxy=httpx_proxy_config,  # 设置代理
                        )
                        effective_client = temp_client
                        used_proxy = httpx_proxy_config  # 记录使用的代理
                        self.logger.info(f"Using temporary client with proxy: {httpx_proxy_config} for {request.url}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to create temporary client with proxy {httpx_proxy_config} for {request.url}: {e}")
                        # 出错则回退到使用主 client（无代理）
                        # 可以选择抛出异常或继续
                        # raise # 如果希望代理失败导致请求失败，取消注释

            # --- 5. 发送请求 (带降级逻辑) ---
            try:
                httpx_response = await effective_client.request(**kwargs)
            except NETWORK_EXCEPTIONS as proxy_error:
                # --- 优雅降级逻辑 ---
                # 如果我们刚刚尝试使用了代理 (temp_client) 并且失败了
                if temp_client is not None and effective_client is temp_client:
                    # 记录警告日志
                    self.logger.warning(
                        f"代理请求失败 ({used_proxy}), 正在尝试直连: {request.url} | 错误: {repr(proxy_error)}"
                    )
                    # 关闭失败的临时客户端
                    await temp_client.aclose()
                    temp_client = None  # 防止 finally 再次关闭

                    # 切换到主客户端（直连）
                    effective_client = self._client
                    # 再次尝试发送请求
                    httpx_response = await effective_client.request(**kwargs)
                else:
                    # 如果是主客户端（直连）失败，或者不是网络错误，则记录日志并返回None
                    self.logger.error(f"Direct connection failed for {request.url}: {repr(proxy_error)}")
                    return None
            except httpx.RemoteProtocolError as remote_error:
                # 特别处理 RemoteProtocolError
                if temp_client is not None and effective_client is temp_client:
                    # 代理请求出现远程协议错误，尝试直连
                    self.logger.warning(
                        f"代理请求远程协议错误 ({used_proxy}), 正在尝试直连: {request.url} | 错误: {repr(remote_error)}"
                    )
                    # 关闭失败的临时客户端
                    await temp_client.aclose()
                    temp_client = None  # 防止 finally 再次关闭

                    # 切换到主客户端（直连）
                    effective_client = self._client
                    # 再次尝试发送请求
                    try:
                        httpx_response = await effective_client.request(**kwargs)
                    except Exception as direct_error:
                        self.logger.error(f"Direct connection also failed for {request.url}: {repr(direct_error)}")
                        return None
                else:
                    # 直连也出现远程协议错误，记录日志并返回None
                    self.logger.error(f"Direct connection failed for {request.url}: {repr(remote_error)}")
                    return None

            # --- 6. 安全检查：防止大响应体 ---
            content_length = httpx_response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_download_size:
                await httpx_response.aclose()  # 立即关闭连接，释放资源
                raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

            # --- 7. 读取响应体 ---
            body = await httpx_response.aread()

            # --- 8. 记录下载统计 ---
            if start_time:
                import time
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s, size: {len(body)} bytes")

            # --- 9. 构造并返回 Response ---
            return self.structure_response(request=request, response=httpx_response, body=body)

        except httpx.TimeoutException as e:
            self.logger.error(f"Timeout error for {request.url}: {e}")
            return None
        except httpx.NetworkError as e:
            self.logger.error(f"Network error for {request.url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP {e.response.status_code} for {request.url}: {e}")
            # 即使是 4xx/5xx，也返回 Response，由上层逻辑（如 spider）处理
            # 如果需要在此处 raise，可取消注释下一行
            # raise
            # 读取响应体以便 structure_response 处理
            try:
                error_body = await e.response.aread()
            except Exception:
                error_body = b""  # 如果读取错误响应体失败，则为空
            return self.structure_response(request=request, response=e.response, body=error_body)
        except Exception as e:
            self.logger.error(f"Unexpected error for {request.url}: {e}", exc_info=True)
            # 不重新抛出异常，而是返回 None 或适当的响应对象
            # 这样可以避免单个请求失败导致整个爬虫进程退出
            # 返回 None 让上层逻辑处理失败情况
            return None

        finally:
            # --- 10. 清理：关闭临时 client ---
            # 如果创建了临时 client，则关闭它
            if temp_client:
                try:
                    await temp_client.aclose()
                    # self.logger.debug("Closed temporary client.")
                except Exception as e:
                    self.logger.warning(f"Error closing temporary client: {e}")

    @staticmethod
    def structure_response(request, response: httpx.Response, body: bytes) -> Response:
        return Response(
            url=str(response.url),  # httpx 的 URL 是对象，需转字符串
            headers=dict(response.headers),
            status_code=response.status_code,  # 注意：使用 status_code
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
