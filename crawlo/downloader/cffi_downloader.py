#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import random
import time
from typing import Optional, Dict, Any
from curl_cffi import CurlError
from curl_cffi.requests import AsyncSession

from crawlo import Response
from crawlo.downloader import DownloaderBase


class CurlCffiDownloader(DownloaderBase):
    """
    基于 curl-cffi 的高性能异步下载器
    - 支持真实浏览器指纹模拟，绕过Cloudflare等反爬虫检测
    - 高性能的异步HTTP客户端，基于libcurl
    - 内存安全的响应处理
    - 自动代理和Cookie管理
    - 支持请求延迟、重试、警告大小检查等高级功能
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.session: Optional[AsyncSession] = None
        self.max_download_size: int = 0
        self.download_warn_size: int = 0
        self.download_delay: float = 0
        self.randomize_delay: bool = False
        self.default_headers: dict = {}
        # 使用默认值，但会在 open 中被 settings 覆盖
        self.browser_type_str: str = "chrome136"
        self._last_request_time: float = 0
        self._active_requests: set = set()  # 用于跟踪活跃请求

    def open(self):
        super().open()
        self.logger.info("正在打开 CurlCffiDownloader")

        # 读取配置
        timeout_secs = self.crawler.settings.get_int("DOWNLOAD_TIMEOUT", 30)
        verify_ssl = self.crawler.settings.get_bool("VERIFY_SSL", True)
        pool_size = self.crawler.settings.get_int("CONNECTION_POOL_LIMIT", 100)
        self.max_download_size = self.crawler.settings.get_int("DOWNLOAD_MAXSIZE", 10 * 1024 * 1024)  # 10MB
        self.download_warn_size = self.crawler.settings.get_int("DOWNLOAD_WARN_SIZE", 1024 * 1024)  # 1MB
        self.download_delay = self.crawler.settings.get_float("DOWNLOAD_DELAY", 0)
        # 兼容旧的 RANDOMNESS 配置
        self.randomize_delay = self.crawler.settings.get_bool("RANDOMIZE_DOWNLOAD_DELAY",
                                                              self.crawler.settings.get_bool("RANDOMNESS", False))
        self.default_headers = self.crawler.settings.get_dict("DEFAULT_REQUEST_HEADERS", {})

        # --- 浏览器指纹模拟配置 ---
        # 1. 读取用户自定义的浏览器版本映射
        user_browser_map = self.crawler.settings.get_dict("CURL_BROWSER_VERSION_MAP", {})
        # 2. 定义代码中的默认浏览器版本映射
        default_browser_map = self._get_default_browser_map()
        # 3. 合并配置：用户配置优先级更高
        effective_browser_map = {**default_browser_map, **user_browser_map}

        # 4. 读取用户选择的浏览器类型 (键)
        raw_browser_type_str = self.crawler.settings.get("CURL_BROWSER_TYPE", "chrome")

        # 5. 使用合并后的映射进行规范化
        #    如果 raw_browser_type_str 在映射中，则使用映射的值
        #    如果不在映射中（例如用户直接指定了具体版本 "chrome136"），则使用原始字符串
        self.browser_type_str = effective_browser_map.get(raw_browser_type_str.lower(), raw_browser_type_str)

        # 创建会话配置
        session_config = {
            "timeout": timeout_secs,
            "verify": verify_ssl,
            "max_clients": pool_size,  # Use max_clients for pool size
            "impersonate": self.browser_type_str,  # Add impersonate
        }

        # 创建全局 session
        self.session = AsyncSession(**session_config)

        self.logger.debug(f"CurlCffiDownloader 初始化完成，浏览器指纹模拟: {self.browser_type_str}")

    @staticmethod
    def _get_default_browser_map() -> Dict[str, str]:
        """获取代码中硬编码的默认浏览器映射"""
        return {
            "chrome": "chrome136",
            "edge": "edge101",
            "safari": "safari184",
            "firefox": "firefox135",
            # 可根据 curl-cffi 支持的版本添加更多
        }

    async def download(self, request) -> Optional[Response]:
        if not self.session:
            raise RuntimeError("CurlCffiDownloader 会话未打开")

        # 请求延迟控制
        await self._apply_download_delay()

        # 本地重试机制
        # 复用现有的 MAX_RETRY_TIMES 配置
        max_retries = self.crawler.settings.get_int("DOWNLOAD_RETRY_TIMES",
                                                    self.crawler.settings.get_int("MAX_RETRY_TIMES", 1))
        last_exception = None

        for attempt in range(max_retries + 1):
            request_id = id(request)
            self._active_requests.add(request_id)
            try:
                # 尝试执行请求
                result = await self._execute_request(request)
                return result  # 成功，返回响应

            except (CurlError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries:
                    retry_delay = 2 ** attempt
                    self.logger.warning(
                        f"第 {attempt + 1}/{max_retries} 次重试 {request.url}，等待 {retry_delay} 秒，原因: {type(e).__name__}")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"请求 {request.url} 在 {max_retries} 次重试后失败: {type(e).__name__}: {e}")
            except Exception as e:
                last_exception = e
                self.logger.critical(f"请求 {request.url} 发生未预期错误: {e}", exc_info=True)
                # 对于未预期错误，可能不希望重试
                break  # Or handle differently based on error type
            finally:
                self._active_requests.discard(request_id)

        # If loop finishes without returning, it means all retries failed or an unretriable error occurred
        if last_exception:
            raise last_exception
        # This line should ideally not be reached if exceptions are handled correctly above
        raise RuntimeError(f"下载 {request.url} 失败，已重试或发生不可重试错误")

    async def _apply_download_delay(self):
        """应用下载延迟"""
        if self.download_delay > 0:
            current_time = time.time()
            if hasattr(self, '_last_request_time'):  # Check if attribute exists
                elapsed = current_time - self._last_request_time
            else:
                elapsed = self.download_delay + 1  # Ensure delay is applied if _last_request_time is not set yet

            if elapsed < self.download_delay:
                delay = self.download_delay - elapsed
                if self.randomize_delay:
                    # 兼容旧的 RANDOM_RANGE 配置
                    range_tuple = self.crawler.settings.get("RANDOM_RANGE", (0.75, 1.25))
                    if isinstance(range_tuple, (list, tuple)) and len(range_tuple) == 2:
                        delay *= random.uniform(range_tuple[0], range_tuple[1])
                    else:
                        delay *= random.uniform(0.5, 1.5)  # Fallback
                await asyncio.sleep(max(0, int(delay)))  # Ensure non-negative sleep
            self._last_request_time = time.time()

    async def _execute_request(self, request) -> Response:
        """执行单个请求"""
        if not self.session:
            raise RuntimeError("会话未初始化")

        # 构造请求参数
        kwargs = self._build_request_kwargs(request)

        # 发送请求
        method = request.method.lower()
        if not hasattr(self.session, method):
            raise ValueError(f"不支持的 HTTP 方法: {request.method}")

        method_func = getattr(self.session, method)

        # *** 核心修正：直接 await 方法调用 ***
        try:
            response = await method_func(request.url, **kwargs)
        except Exception as e:
            # Re-raise to let the calling function handle retries
            raise

        # 检查 Content-Length
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                cl = int(content_length)
                if cl > self.max_download_size:
                    raise OverflowError(
                        f"响应过大 (基于 Content-Length): {cl} > {self.max_download_size}")
            except ValueError:
                self.logger.warning(f"无效的 Content-Length 头部值: {content_length}")

        # 获取响应体 (curl-cffi 中 response.content 通常是 bytes)
        # *** 核心修正：直接使用 response.content ***
        body = response.content

        # 再次检查实际大小 (以防 Content-Length 不准确或缺失)
        actual_size = len(body)
        if actual_size > self.max_download_size:
            raise OverflowError(f"响应体过大: {actual_size} > {self.max_download_size}")

        # 警告大小检查
        if actual_size > self.download_warn_size:
            self.logger.warning(f"响应体较大: {actual_size} 字节，来自 {request.url}")

        return self._structure_response(request, response, body)

    def _build_request_kwargs(self, request) -> Dict[str, Any]:
        """构造curl-cffi请求参数"""
        # 合并默认 headers 和请求 headers
        # 确保 request.headers 是一个字典或类似对象
        request_headers = getattr(request, 'headers', {}) or {}
        headers = {**self.default_headers, **request_headers}

        kwargs = {
            "headers": headers,
            "cookies": getattr(request, 'cookies', {}) or {},  # Safely get cookies
            "allow_redirects": getattr(request, 'allow_redirects', True),  # Safely get allow_redirects
        }

        # 代理设置
        # curl-cffi 通常使用 proxies 参数，接受字典 {'http': '...', 'https': '...'}
        if hasattr(request, 'proxy') and request.proxy:
            # 简单处理，假设 proxy URL 适用于 http 和 https
            # 你可能需要根据 request.url.scheme 来决定使用哪个
            if request.proxy.startswith(('http://', 'https://')):
                kwargs["proxies"] = {"http": request.proxy, "https": request.proxy}
            else:
                # Handle other proxy types if needed (e.g., socks)
                # For now, just pass it and let curl-cffi potentially handle it or log a warning
                self.logger.warning(
                    f"代理格式可能需要为 curl-cffi 调整: {request.proxy}。按原样传递。")
                kwargs["proxy"] = request.proxy  # Try the simpler 'proxy' kwarg if 'proxies' doesn't work

        # 智能处理请求体
        # 优先使用 _json_body (如果框架有此约定)
        if hasattr(request, "_json_body") and request._json_body is not None:
            kwargs["json"] = request._json_body
        # 其次检查 body 是否为 dict/list (兼容直接传 body=dict 的旧写法)
        elif isinstance(getattr(request, 'body', None), (dict, list)):
            kwargs["json"] = request.body
        # 最后处理其他类型的 body (str, bytes, etc.)
        elif getattr(request, 'body', None) is not None:
            # curl-cffi 通常可以处理 str 和 bytes
            kwargs["data"] = request.body

        return kwargs

    @staticmethod
    def _structure_response(request, response, body: bytes) -> Response:
        """构造框架所需的 Response 对象"""
        return Response(
            url=str(response.url),
            headers=dict(response.headers),
            status_code=response.status_code,
            body=body,
            request=request,
        )

    async def close(self) -> None:
        """关闭会话资源"""
        if self.session:
            self.logger.info("正在关闭 CurlCffiDownloader 会话...")
            try:
                await self.session.close()
            except Exception as e:
                self.logger.warning(f"关闭 curl-cffi 会话时出错: {e}")
            finally:
                self.session = None
        self.logger.debug("CurlCffiDownloader 已关闭")

    def idle(self) -> bool:
        """检查是否空闲"""
        return len(self._active_requests) == 0  # Check active requests

    def __len__(self) -> int:
        """返回活跃请求数"""
        return len(self._active_requests)
