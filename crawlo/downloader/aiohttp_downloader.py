#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import inspect
import socket
import time
from typing import Optional, TYPE_CHECKING, Dict, Any
from yarl import URL
from aiohttp import (
    ClientSession,
    TCPConnector,
    ClientTimeout,
    ClientResponse,
    ClientError,
    BasicAuth,
)

from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.downloader import DownloaderBase
from crawlo.utils.misc import safe_get_config
from crawlo.constants import ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL, ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED

# 检查 aiohttp 版本是否支持 happy_eyeballs_delay 参数
# 该参数在 aiohttp 3.9.0+ 中引入，但某些 3.9.x 版本可能不包含
def _supports_happy_eyeballs():
    try:
        sig = inspect.signature(TCPConnector.__init__)
        return 'happy_eyeballs_delay' in sig.parameters
    except Exception:
        return False

_HAPPY_EYEBALLS_SUPPORTED = _supports_happy_eyeballs()
from crawlo.exceptions import DownloadError

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
    - 代理由 ProxyMiddleware 统一管理
    """

    def __init__(self, crawler: 'Crawler') -> None:
        """
        初始化 AioHttp 下载器

        Args:
            crawler: 爬虫实例
        """
        super().__init__(crawler)
        self.session: Optional[ClientSession] = None
        self._timeout_secs: int = 30  # 总超时配置，用于重试时动态计算（增加到30秒）
        self.max_download_size: int = 0
        self.logger = get_logger(self.__class__.__name__)
        
        # 并发控制
        self._concurrency = 12  # 默认并发数
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_requests = 0  # 当前活跃请求数

    def open(self) -> None:
        """
        打开下载器，创建 ClientSession
        """
        if self.session is not None:
            self.logger.warning("AioHttpDownloader already initialized, skipping")
            return

        super().open()

        # 读取配置
        timeout_secs = safe_get_config(self.crawler.settings, "DOWNLOAD_TIMEOUT", 30, int)
        verify_ssl = safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool)
        pool_limit = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int)
        pool_per_host = safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT_PER_HOST", 0, int)  # 0=不限制
        self.max_download_size = safe_get_config(self.crawler.settings, "DOWNLOAD_MAXSIZE", 10 * 1024 * 1024, int)
        auto_decompress = safe_get_config(self.crawler.settings, "AIOHTTP_AUTO_DECOMPRESS", True, bool)

        # 保存为实例变量
        self._timeout_secs = timeout_secs
        
        # 初始化并发控制
        self._concurrency = safe_get_config(self.crawler.settings, "CONCURRENCY", 12, int)
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self.logger.debug(f"并发控制初始化: CONCURRENCY={self._concurrency}")

        # 创建连接器（优化配置，防止连接泄漏和死锁）
        # 关键优化说明：
        # 1. limit_per_host=0: 不限制单主机连接数（由全局 limit 控制）
        # 2. keepalive_timeout=15: 使用 aiohttp 默认值（15秒）
        # 3. enable_cleanup_closed=True: 防止 SSL 连接泄漏（重要！）
        # 4. happy_eyeballs_delay=0.25: RFC 8305 快速连接建立（如果支持）
        connector_kwargs = {
            'verify_ssl': verify_ssl,
            'limit': pool_limit,
            'limit_per_host': pool_per_host,  # 0=不限制单主机连接
            'ttl_dns_cache': 300,  # DNS 缓存 5 分钟
            'keepalive_timeout': 15.0,  # 使用 aiohttp 默认值
            'force_close': False,  # 启用连接复用
            'use_dns_cache': True,
            'family': socket.AF_UNSPEC,
            'enable_cleanup_closed': True,  # 启用 SSL 连接清理（防止泄漏）
        }
        if _HAPPY_EYEBALLS_SUPPORTED:
            connector_kwargs['happy_eyeballs_delay'] = 0.25  # RFC 8305 快速连接建立
        
        connector = TCPConnector(**connector_kwargs)

        # 基于 DOWNLOAD_TIMEOUT 动态计算分层超时
        # 优化分配比例: connect=33%, sock_read=50%, sock_connect=33%, total=100%
        # 默认 timeout_secs=30: total=30s, connect=10s, sock_read=15s, sock_connect=10s
        timeout = ClientTimeout(
            total=timeout_secs,                        # 总超时：30秒（覆盖99%场景）
            connect=min(10.0, timeout_secs * 0.33),   # 连接超时：33%（上限10秒，给足连接时间）
            sock_read=timeout_secs * 0.50,            # 读取超时：50%（主要等待时间）
            sock_connect=min(10.0, timeout_secs * 0.33)  # 连接超时：33%（上限10秒）
        )

        # 创建持久化 session
        self.session = ClientSession(
            connector=connector,
            timeout=timeout,
            auto_decompress=auto_decompress,
        )

        self.logger.info(
            f"AioHttpDownloader initialized with timeout {timeout_secs}s "
            f"(total={timeout_secs}s, connect={min(10.0, timeout_secs * 0.33):.1f}s, "
            f"sock_read={timeout_secs * 0.50:.1f}s, sock_connect={min(10.0, timeout_secs * 0.33):.1f}s)"
        )

    async def download(self, request: 'Request') -> Optional[Response]:
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

        start_time = None
        if self.crawler.settings.get_bool("DOWNLOAD_STATS", True):
            start_time = time.time()

        try:
            # 检查是否为重试请求
            is_retry = request.meta.get("retry_times", 0) > 0

            # 所有请求都使用绝对超时保护（防止代理连接永久阻塞）
            # 从 DOWNLOAD_TIMEOUT 配置派生，乘以超时系数作为安全防线
            absolute_timeout = (
                self._timeout_secs * ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED if is_retry
                else self._timeout_secs * ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL
            )
            
            if is_retry:
                # 重试时使用正常超时，因为已经切换了代理或等待了一段时间
                retry_timeout = ClientTimeout(
                    total=self._timeout_secs,                  # 100%（30秒）
                    connect=min(10.0, self._timeout_secs * 0.33),  # 33%（10秒）
                    sock_read=self._timeout_secs * 0.50,       # 50%（15秒）
                    sock_connect=min(10.0, self._timeout_secs * 0.33)  # 33%（10秒）
                )
                # 使用 asyncio.timeout 强制超时保护，超时后取消下载防止连接泄漏
                try:
                    download_task = asyncio.ensure_future(
                        self._download_with_timeout(request, retry_timeout)
                    )
                    async with asyncio.timeout(absolute_timeout):
                        response = await download_task
                except asyncio.TimeoutError:
                    download_task.cancel()
                    try:
                        await download_task
                    except asyncio.CancelledError:
                        pass
                    self.logger.error(
                        f"重试请求绝对超时（{absolute_timeout:.0f}s），代理连接可能死锁: {request.url} "
                        f"(retry_times={request.meta.get('retry_times', 0)})"
                    )
                    raise DownloadError(
                        f"Connection timeout to host {request.url} (absolute timeout {absolute_timeout:.0f}s)",
                        url=request.url
                    )
            else:
                # 正常请求也添加绝对超时保护，超时后取消下载防止连接泄漏
                try:
                    download_task = asyncio.ensure_future(
                        self._download_with_timeout(request)
                    )
                    async with asyncio.timeout(absolute_timeout):
                        response = await download_task
                except asyncio.TimeoutError:
                    download_task.cancel()
                    try:
                        await download_task
                    except asyncio.CancelledError:
                        pass
                    self.logger.error(
                        f"请求绝对超时（{absolute_timeout:.0f}s），代理连接可能死锁: {request.url}"
                    )
                    raise DownloadError(
                        f"Connection timeout to host {request.url} (absolute timeout {absolute_timeout:.0f}s)",
                        url=request.url
                    )

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
        finally:
            # 释放并发槽位
            if self._semaphore:
                self._active_requests -= 1
                self._semaphore.release()
                self.logger.debug(
                    f"释放并发槽位: {request.url} (active={self._active_requests}/{self._concurrency})"
                )

    async def _download_with_timeout(self, request: 'Request', timeout: Optional[ClientTimeout] = None) -> Response:
        """
        执行下载操作，支持自定义超时

        Args:
            request: 请求对象
            timeout: 自定义超时配置（可选）

        Returns:
            Response: 响应对象
        """
        # 记录请求详情（用于诊断）
        client_type = "临时session(重试)" if timeout is not None else "主session(正常)"
        timeout_value = timeout.total if timeout and timeout.total else (self._timeout_secs * ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED if request.meta.get('retry_times', 0) > 0 else self._timeout_secs * ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL)
        self.logger.debug(
            f"Sending request via {client_type} (absolute_timeout={timeout_value:.0f}s): {request.url}"
        )
        
        # 如果有自定义超时，需要创建临时 session
        if timeout is not None:
            # 优化连接池配置，防止连接泄漏和死锁
            # 与主连接器保持一致的配置，确保行为一致
            temp_connector_kwargs = {
                'verify_ssl': safe_get_config(self.crawler.settings, "VERIFY_SSL", True, bool),
                'limit': safe_get_config(self.crawler.settings, "CONNECTION_POOL_LIMIT", 100, int),
                'limit_per_host': 0,  # 不限制单主机连接
                'ttl_dns_cache': 300,
                'keepalive_timeout': 15.0,  # 使用默认值
                'force_close': False,
                'use_dns_cache': True,
                'family': socket.AF_UNSPEC,
                'enable_cleanup_closed': True,  # 启用 SSL 连接清理
            }
            if _HAPPY_EYEBALLS_SUPPORTED:
                temp_connector_kwargs['happy_eyeballs_delay'] = 0.25  # 快速连接建立
            
            connector = TCPConnector(**temp_connector_kwargs)
            try:
                async with ClientSession(connector=connector, timeout=timeout) as temp_session:
                    async with await self._send_request(temp_session, request) as resp:
                        return await self._process_response(request, resp)
            finally:
                # 确保连接器被正确关闭（防止连接泄漏）
                await connector.close()
        else:
            # 使用默认 session
            async with await self._send_request(self.session, request) as resp:
                return await self._process_response(request, resp)

    async def _process_response(self, request: 'Request', resp: ClientResponse) -> Response:
        """
        处理响应数据

        Args:
            request: 请求对象
            resp: aiohttp 响应对象

        Returns:
            Response: 框架响应对象
        """
        # 安全检查：防止大响应体导致 OOM
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_download_size:
            raise OverflowError(f"Response too large: {content_length} > {self.max_download_size}")

        body = await resp.read()
        response = self._structure_response(request, resp, body)

        # 记录下载大小
        self.logger.debug(f"Downloaded {request.url}, size: {len(body)} bytes")

        return response

    @staticmethod
    async def _send_request(session: ClientSession, request: 'Request') -> ClientResponse:
        """
        根据请求方法和高层语义智能发送请求

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

        # Per-request auth: HTTP Basic Auth
        if request.auth:
            if isinstance(request.auth, (list, tuple)) and len(request.auth) == 2:
                kwargs["auth"] = BasicAuth(*request.auth)
            else:
                kwargs["auth"] = request.auth

        # Per-request SSL verification override
        if not request.verify:
            kwargs["ssl"] = False

        # 处理代理（由 ProxyMiddleware 分配）
        proxy = getattr(request, "proxy", None)
        proxy_auth = None

        if proxy:
            # 兼容字典格式：{"http": "...", "https": "..."}
            if isinstance(proxy, dict):
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
                    proxy = str(proxy_url.with_user(None))
                else:
                    proxy = str(proxy_url)

                kwargs["proxy"] = proxy
                if proxy_auth:
                    kwargs["proxy_auth"] = proxy_auth

            except Exception as e:
                raise ValueError(f"Invalid proxy URL: {proxy}") from e

        # 处理通过 meta 传递的代理认证信息
        meta_proxy_auth = request.meta.get("proxy_auth")
        if meta_proxy_auth and isinstance(meta_proxy_auth, dict):
            username = meta_proxy_auth.get("username")
            password = meta_proxy_auth.get("password")
            if username and password:
                kwargs["proxy_auth"] = BasicAuth(username, password)

        # 处理请求体
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
            status=resp.status,
            body=body,
            request=request,
        )

    async def _handle_download_error(self, request: 'Request', error: Exception) -> None:
        """
        处理下载错误，不在此处重试，交由框架的 RetryMiddleware 处理

        Args:
            request: 请求对象
            error: 错误信息
        """
        error_type = type(error).__name__
        
        # 不在此处重试，避免与中间件重试逻辑冲突
        # 框架的 RetryMiddleware 会处理重试
        if isinstance(error, ClientError):
            self.logger.error(f"Client error for {request.url}: {error}")
        elif isinstance(error, asyncio.TimeoutError):
            self.logger.error(f"Timeout error for {request.url}: {error}")
        elif isinstance(error, OverflowError):
            self.logger.error(f"Response size error for {request.url}: {error}")
        else:
            self.logger.error(f"Unexpected error for {request.url}: {error}", exc_info=True)

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session and not self.session.closed:
            self.logger.debug("Closing AioHttpDownloader session...")
            try:
                await self.session.close()
                await asyncio.sleep(0.25)
            except Exception as e:
                self.logger.warning(f"Error during session close: {e}")
            finally:
                self.session = None
            self.logger.debug("AioHttpDownloader session closed.")
        
        self.logger.debug("AioHttpDownloader closed.")
    
    def idle(self) -> bool:
        """检查下载器是否空闲（无活跃请求）"""
        is_idle = self._active_requests == 0
        if not is_idle:
            self.logger.debug(
                f"下载器忙碌: active_requests={self._active_requests}/{self._concurrency}"
            )
        return is_idle
