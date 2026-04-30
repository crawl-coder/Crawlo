#!/usr/bin/python
# -*- coding:UTF-8 -*-
import httpx
import asyncio
from typing import Optional

from httpx import HTTPStatusError
from httpx import AsyncClient, Timeout, Limits

from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.exceptions import DownloadError
from crawlo.constants import ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL, ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED


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
        self._timeout_total: int = 15  # 总超时配置，用于重试时动态计算
        self.max_download_size: int = 0
        self.logger = get_logger(self.__class__.__name__)
        
        # 并发控制
        self._concurrency = 12  # 默认并发数
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_requests = 0  # 当前活跃请求数

    def open(self) -> None:
        """初始化下载器，创建持久化 AsyncClient"""
        super().open()
        
        # 读取配置
        timeout_total = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 15, int)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int)
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 20, int)
        max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)

        self.max_download_size = max_download_size
        self._timeout_total = timeout_total  # 保存为实例变量
        
        # 初始化并发控制
        self._concurrency = safe_get_config(self.crawler.settings, "CONCURRENCY", 12, int)
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self.logger.debug(f"并发控制初始化: CONCURRENCY={self._concurrency}")

        # 基于 DOWNLOAD_TIMEOUT 配置动态计算分层超时
        # 采用分层超时策略，平衡性能与兼容性
        # 基于 httpx 源码分析：Timeout(connect, read, write, pool)
        # - connect: TCP 连接建立（三次握手 + TLS 协商）
        # - read: 等待并读取响应数据（主要等待时间）
        # - write: 发送请求数据（通常很快）
        # - pool: 从连接池获取可用连接
        # 
        # 分配比例: connect=17%, read=50%, write=17%, pool=固定1s
        # 默认 timeout_total=15: connect=2.6s, read=7.5s, write=2.6s, pool=1s → 13.7s
        self._client_timeout = Timeout(
            connect=min(5.0, timeout_total * 0.17),   # 连接超时：17%（上限5秒，网络异常快速失败）
            read=timeout_total * 0.50,                # 读取超时：50%（主要等待时间）
            write=min(5.0, timeout_total * 0.17),     # 写入超时：17%（上限5秒）
            pool=1.0                                  # 连接池超时：固定1秒
        )
        # 基于 httpx 源码分析优化连接池配置：
        # httpx 使用 Limits(max_connections, max_keepalive_connections, keepalive_expiry)
        # - max_connections: 最大并发连接数（对应 CONNECTION_POOL_LIMIT）
        # - max_keepalive_connections: 保活连接数（对应 CONNECTION_POOL_LIMIT_PER_HOST）
        # - keepalive_expiry: 空闲连接保活时间（默认5秒，超时后关闭）
        # 
        # 优化策略：
        # 1. keepalive_expiry=5.0：使用 httpx 默认值，平衡性能与资源占用
        # 2. 过短（<3s）：连接复用率低，频繁重建连接
        # 3. 过长（>10s）：占用过多文件描述符，可能遇到服务器关闭连接
        self._client_limits = Limits(
            max_connections=pool_limit,                      # 最大连接数
            max_keepalive_connections=pool_per_host,         # 最大保活连接数
            keepalive_expiry=5.0                             # 保活连接过期时间（5秒，httpx 默认值）
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
        # 添加入口日志，用于诊断请求是否到达下载器
        retry_times = request.meta.get('retry_times', 0)
        has_proxy = bool(request.proxy)
        self.logger.debug(
            f"Download request (retry={retry_times}, proxy={has_proxy}): {request.url}"
        )
        
        # 并发控制：等待信号量
        if self._semaphore:
            self.logger.debug(
                f"等待并发槽位: {request.url} (active={self._active_requests}/{self._concurrency})"
            )
            await self._semaphore.acquire()
            self._active_requests += 1
            self.logger.debug(
                f"获取并发槽位成功: {request.url} (active={self._active_requests}/{self._concurrency})"
            )
        
        if not self._client:
            self.logger.error("HttpXDownloader client is not available.")
            if self._semaphore:
                self._active_requests -= 1
                self._semaphore.release()
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

            # Per-request auth: HTTP Basic Auth / Bearer token
            if request.auth:
                kwargs["auth"] = request.auth

            # Per-request SSL verification override
            if not request.verify:
                kwargs["verify"] = False

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
                        # 基于 httpx 源码分析：Timeout(connect, read, write, pool)
                        # connect: 代理连接建立（TCP 握手 + SSL）
                        # read: 等待响应数据
                        # write: 发送请求数据
                        # pool: 从连接池获取连接
                        # 
                        # 重试请求的代理超时更严格（已经失败过一次）
                        is_retry = request.meta.get("retry_times", 0) > 0
                        if is_retry:
                            # 重试请求：更严格的超时
                            proxy_timeout = Timeout(
                                connect=3.0,   # 连接超时：3秒（快速失败）
                                read=5.0,      # 读取超时：5秒（已经重试过）
                                write=3.0,     # 写入超时：3秒
                                pool=0.5       # 连接池超时：0.5秒
                            )
                        else:
                            # 正常请求：正常超时
                            proxy_timeout = Timeout(
                                connect=5.0,   # 连接超时：5秒（代理服务器响应慢）
                                read=8.0,      # 读取超时：8秒（等待目标服务器响应）
                                write=5.0,     # 写入超时：5秒（发送请求体）
                                pool=1.0       # 连接池超时：1秒（获取可用连接）
                            )
                        
                        temp_client = AsyncClient(
                            timeout=proxy_timeout,
                            limits=self._client_limits,      # 复用主客户端的连接池配置
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
            
            # 重试请求直连超时保护：检测重试次数，使用更严格的超时
            retry_times = request.meta.get('retry_times', 0)
            if retry_times > 0 and not request.proxy:
                # 直连重试请求，使用严格超时防止长时间阻塞
                # 基于 httpx 源码分析：已经重试过，应该更快失败
                # 分配比例: connect=17%, read=33%, write=10%, pool=固定1s
                # 默认 timeout_total=15: connect=2.6s, read=5.0s, write=1.5s, pool=1s → 10.1s
                strict_timeout = Timeout(
                    connect=min(5.0, self._timeout_total * 0.17),   # 连接超时：17%（上限5秒）
                    read=self._timeout_total * 0.33,                # 读取超时：33%（已经重试过，更快失败）
                    write=min(3.0, self._timeout_total * 0.10),     # 写入超时：10%（上限3秒）
                    pool=1.0                                        # 连接池超时：固定1秒
                )
                
                # 创建临时客户端（严格超时模式）
                temp_client = AsyncClient(
                    timeout=strict_timeout,
                    limits=self._client_limits,      # 复用主客户端的连接池配置
                    verify=self._client_verify,
                    http2=self._client_http2,
                    follow_redirects=True
                )
                effective_client = temp_client
                self.logger.info(
                    f"Retry direct request (retry_times={retry_times}) with strict timeout "
                    f"(connect={min(5.0, self._timeout_total * 0.17):.1f}s, read={self._timeout_total * 0.33:.1f}s, write={min(3.0, self._timeout_total * 0.10):.1f}s): {request.url}"
                )

            # 发送请求（使用绝对超时保护，防止代理连接永久阻塞）
            # 判断是否为代理请求（有代理配置即为代理请求）
            is_proxy_request = bool(httpx_proxy_config)
            
            # 所有请求都使用绝对超时保护，从 DOWNLOAD_TIMEOUT 配置派生
            # 代理请求使用 EXTENDED 系数，正常/重试请求使用 NORMAL 系数
            absolute_timeout = (
                self._timeout_total * ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED if is_proxy_request
                else self._timeout_total * ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL
            )
            
            # 记录请求详情（用于诊断）
            client_type = "代理客户端" if is_proxy_request else "主客户端(直连)"
            self.logger.debug(
                f"Sending request via {client_type} (absolute_timeout={absolute_timeout:.0f}s): {request.url}"
            )
            
            # 基于 httpx 源码分析优化：
            # httpx 的 Timeout 在 httpcore 层应用，但代理连接可能在更底层阻塞
            # asyncio.wait_for 可能无法中断 httpcore 的底层 socket 操作
            # 因此使用 asyncio.create_task + task.cancel() 强制取消
            kwargs["timeout"] = effective_client.timeout  # 显式传递超时配置
            
            try:
                # 创建请求任务
                request_task = asyncio.create_task(
                    effective_client.request(**kwargs)
                )
                
                # 等待任务完成或超时
                done, pending = await asyncio.wait(
                    [request_task],
                    timeout=absolute_timeout
                )
                
                if done:
                    # 请求成功
                    httpx_response = done.pop().result()
                else:
                    # 超时，取消任务
                    self.logger.error(
                        f"请求绝对超时（{absolute_timeout:.0f}s），强制取消: {request.url}"
                    )
                    request_task.cancel()
                    try:
                        await request_task
                    except asyncio.CancelledError:
                        pass
                    
                    raise DownloadError(
                        f"Connection timeout to host {request.url} (absolute timeout {absolute_timeout:.0f}s)",
                        url=request.url
                    )
            except DownloadError:
                raise
            except asyncio.CancelledError:
                # 只在第一次取消时打印日志，避免重复
                if not getattr(self, '_cancel_logged', False):
                    self.logger.warning(f"请求被取消: {request.url}")
                    self._cancel_logged = True
                raise DownloadError(
                    f"Request cancelled for {request.url}",
                    url=request.url
                )
            except Exception as e:
                self.logger.error(f"请求异常: {type(e).__name__}: {e}")
                raise

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
            
            # 释放并发槽位
            if self._semaphore:
                self._active_requests -= 1
                self._semaphore.release()
                self.logger.debug(
                    f"释放并发槽位: {request.url} (active={self._active_requests}/{self._concurrency})"
                )

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
    
    def idle(self) -> bool:
        """检查下载器是否空闲（无活跃请求）"""
        is_idle = self._active_requests == 0
        if not is_idle:
            self.logger.debug(
                f"下载器忙碌: active_requests={self._active_requests}/{self._concurrency}"
            )
        return is_idle
