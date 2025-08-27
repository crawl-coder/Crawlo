#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import socket
from typing import Optional, Dict, Any, Callable, Union
from urllib.parse import urlparse

from crawlo import Request, Response
from crawlo.exceptions import NotConfiguredError
from crawlo.utils.log import get_logger


# 尝试导入 httpx 异常
try:
    import httpx
    HTTPX_EXCEPTIONS = (httpx.NetworkError, httpx.TimeoutException, httpx.ReadError, httpx.ConnectError)
except ImportError:
    HTTPX_EXCEPTIONS = ()
    httpx = None

# 尝试导入 aiohttp 异常
try:
    import aiohttp
    AIOHTTP_EXCEPTIONS = (aiohttp.ClientError, aiohttp.ClientConnectorError, aiohttp.ClientResponseError, aiohttp.ServerTimeoutError, aiohttp.ServerDisconnectedError)
    # socket.gaierror 等也可能由 aiohttp 抛出，但它们是标准异常
except ImportError:
    AIOHTTP_EXCEPTIONS = ()
    aiohttp = None

# 尝试导入 curl_cffi 异常 (假设模块名)
# 注意：curl_cffi 的异常结构可能不同，请根据实际库的文档调整
try:
    # 常见的 curl_cffi 异常基类可能是 curl_cffi.CurlError 或 requests.RequestsError (如果它模仿 requests)
    # 需要查阅具体使用的 curl_cffi 版本的文档
    from curl_cffi import requests as cffi_requests # 假设是这样导入的
    # 或者 from curl_cffi import CurlError
    CURL_CFFI_EXCEPTIONS = (cffi_requests.RequestsError,) # 根据实际情况调整
except (ImportError, AttributeError):
    CURL_CFFI_EXCEPTIONS = ()
    cffi_requests = None

# 定义一个元组，包含所有认为是网络问题的异常类型
NETWORK_EXCEPTIONS = (
    asyncio.TimeoutError, # 通用异步超时
    socket.gaierror,      # 地址解析错误
    ConnectionError,      # Python 内置连接错误 (包含 ConnectionResetError 等)
    TimeoutError,         # Python 内置超时错误
) + HTTPX_EXCEPTIONS + AIOHTTP_EXCEPTIONS + CURL_CFFI_EXCEPTIONS


# 类型定义
ProxyExtractor = Callable[[Dict[str, Any]], Union[None, str, Dict[str, str]]]


class ProxyMiddleware:
    """
    通用代理中间件：支持从 API 获取代理，支持嵌套字段、多协议、自定义提取函数
    """

    def __init__(self, settings, log_level):
        self.enabled = settings.get_bool("PROXY_ENABLED", True)

        if not self.enabled:
            self.logger = get_logger(self.__class__.__name__, log_level)
            self.logger.info("ProxyMiddleware 已被禁用 (PROXY_ENABLED=False)")
            return  # 不初始化其他资源

        self.api_url = settings.get("PROXY_API_URL")
        if not self.api_url:
            raise NotConfiguredError("PROXY_API_URL 未配置，ProxyMiddleware 已禁用")

        # 提取方式：字符串路径（如 "data.proxy.http"）或 callable 函数
        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")
        # 刷新间隔（秒）
        self.refresh_interval = settings.get_float("PROXY_REFRESH_INTERVAL", 60)
        self.timeout = settings.get_float("PROXY_API_TIMEOUT", 10)

        # 内部状态
        self._session: Optional[aiohttp.ClientSession] = None
        self._current_proxy: Optional[Union[str, Dict[str, str]]] = None
        self._last_fetch_time: float = 0

        self.logger = get_logger(self.__class__.__name__, log_level)
        self.logger.info(f"代理中间件已启用 | API: {self.api_url} | 刷新间隔: {self.refresh_interval}s")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings, log_level=crawler.settings.get("LOG_LEVEL"))

    def _compile_extractor(self) -> ProxyExtractor:
        """
        将字符串字段路径（如 'a.b.c'）编译为提取函数
        支持嵌套访问：data['a']['b']['c']
        """
        if callable(self.proxy_extractor):
            return self.proxy_extractor

        if isinstance(self.proxy_extractor, str):
            keys = self.proxy_extractor.split(".")

            def extract(data: Dict[str, Any]) -> Union[None, str, Dict[str, str]]:
                for k in keys:
                    if isinstance(data, dict):
                        data = data.get(k)
                    else:
                        return None
                    if data is None:
                        break
                return data

            return extract

        raise ValueError(f"PROXY_EXTRACTOR 必须是 str 或 callable，当前类型: {type(self.proxy_extractor)}")

    async def _fetch_raw_data(self) -> Optional[Dict[str, Any]]:
        """
        从 API 获取原始数据（JSON）
        """
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        try:
            async with self._session.get(self.api_url) as resp:
                if resp.status != 200:
                    self.logger.error(f"代理 API 状态码异常: {resp.status}")
                    return None
                return await resp.json()
        except aiohttp.ContentTypeError:
            # 非 JSON 响应（可能是纯文本）
            try:
                text = await resp.text()
                return {"__raw_text__": text.strip()}
            except Exception as e:
                self.logger.error(f"读取非 JSON 响应失败: {repr(e)}")
                return None
        except Exception as e:
            self.logger.error(f"请求代理 API 失败: {repr(e)}")
            return None

    async def _extract_proxy(self, data: Dict[str, Any]) -> Optional[Union[str, Dict[str, str]]]:
        """
        使用 extractor 提取代理
        支持：
          - 字符串（如 "http://..."）
          - 字典（如 {"http": "...", "https": "..."}）
        """
        extractor = self._compile_extractor()
        try:
            result = extractor(data)
            if isinstance(result, str) and result.strip():
                return result.strip()
            elif isinstance(result, dict):
                # 清理字典中的空值
                cleaned = {k: v.strip() for k, v in result.items() if v and isinstance(v, str)}
                return cleaned if cleaned else None
            return None
        except Exception as e:
            self.logger.error(f"执行 PROXY_EXTRACTOR 时出错: {repr(e)}")
            return None

    async def _get_proxy_from_api(self) -> Optional[Union[str, Dict[str, str]]]:
        """
        获取代理：从 API 获取并提取
        """
        raw_data = await self._fetch_raw_data()
        if not raw_data:
            return None

        # 如果是纯文本响应
        if "__raw_text__" in raw_data:
            text = raw_data["__raw_text__"]
            if text.startswith("http://") or text.startswith("https://"):
                return text

        # 正常 JSON 提取
        return await self._extract_proxy(raw_data)

    async def _get_cached_proxy(self) -> Optional[str]:
        """
        获取最终代理字符串（仅返回 str 类型）
        不涉及 request，只返回原始代理值（str 或 dict）
        """
        now = asyncio.get_event_loop().time()
        if self._current_proxy and (now - self._last_fetch_time) < self.refresh_interval:
            pass  # 使用缓存
        else:
            proxy = await self._get_proxy_from_api()
            if proxy:
                self._current_proxy = proxy
                self._last_fetch_time = now
                self.logger.debug(f"更新代理缓存: {proxy}")
            else:
                self.logger.warning("无法获取新代理，使用旧代理（如有）")

        return self._current_proxy

    @staticmethod
    def _is_https(request: Request) -> bool:
        return urlparse(request.url).scheme == "https"

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        if request.proxy:
            return None  # 已有代理，跳过

        proxy = await self._get_cached_proxy()
        if proxy:
            request.proxy = proxy
            self.logger.debug(f"分配代理 → {proxy} | {request.url}")
        else:
            self.logger.warning(f"未获取到代理，请求直连: {request.url}")

        return None

    def process_response(self, request: Request, response: Response, spider) -> Response:
        # 确保访问的是正确的属性名
        proxy = request.proxy
        if proxy:
            # --- 修改点 ---
            status_code = getattr(response, 'status_code', 'N/A')  # 更安全的访问方式
            self.logger.debug(f"代理成功: {proxy} | {request.url} | Status: {status_code}")
            # --- 修改点 ---
        return response

    def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        proxy = request.proxy
        if proxy:
            self.logger.warning(f"代理请求失败: {proxy} | {request.url} | {repr(exception)}")
        return None

    async def close(self):
        """由框架调用，清理资源"""
        if self._session:
            await self._session.close()