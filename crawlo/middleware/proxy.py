#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import socket
from typing import Optional, Dict, Any, Callable, Union
from urllib.parse import urlparse

from crawlo import Request, Response
from crawlo.exceptions import NotConfiguredError
from crawlo.utils.log import get_logger

try:
    import httpx

    HTTPX_EXCEPTIONS = (httpx.NetworkError, httpx.TimeoutException, httpx.ReadError, httpx.ConnectError)
except ImportError:
    HTTPX_EXCEPTIONS = ()
    httpx = None

try:
    import aiohttp

    AIOHTTP_EXCEPTIONS = (
    aiohttp.ClientError, aiohttp.ClientConnectorError, aiohttp.ClientResponseError, aiohttp.ServerTimeoutError,
    aiohttp.ServerDisconnectedError)
except ImportError:
    AIOHTTP_EXCEPTIONS = ()
    aiohttp = None

try:
    from curl_cffi import requests as cffi_requests

    CURL_CFFI_EXCEPTIONS = (cffi_requests.RequestsError,)
except (ImportError, AttributeError):
    CURL_CFFI_EXCEPTIONS = ()
    cffi_requests = None

NETWORK_EXCEPTIONS = (
                         asyncio.TimeoutError,
                         socket.gaierror,
                         ConnectionError,
                         TimeoutError,
                     ) + HTTPX_EXCEPTIONS + AIOHTTP_EXCEPTIONS + CURL_CFFI_EXCEPTIONS

ProxyExtractor = Callable[[Dict[str, Any]], Union[None, str, Dict[str, str]]]


class ProxyMiddleware:
    def __init__(self, settings, log_level):
        self.logger = get_logger(self.__class__.__name__, log_level)

        self._session: Optional[aiohttp.ClientSession] = None
        self._current_proxy: Optional[Union[str, Dict[str, str]]] = None
        self._last_fetch_time: float = 0

        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")
        self.refresh_interval = settings.get_float("PROXY_REFRESH_INTERVAL", 60)
        self.timeout = settings.get_float("PROXY_API_TIMEOUT", 10)

        self.enabled = settings.get_bool("PROXY_ENABLED", True)

        if not self.enabled:
            self.logger.info("ProxyMiddleware 已被禁用 (PROXY_ENABLED=False)")
            return

        self.api_url = settings.get("PROXY_API_URL")
        if not self.api_url:
            raise NotConfiguredError("PROXY_API_URL 未配置，ProxyMiddleware 已禁用")

        self.logger.info(f"代理中间件已启用 | API: {self.api_url} | 刷新间隔: {self.refresh_interval}s")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings, log_level=crawler.settings.get("LOG_LEVEL"))

    def _compile_extractor(self) -> ProxyExtractor:
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

    async def _close_session(self):
        if self._session:
            try:
                await self._session.close()
                self.logger.debug("已关闭 aiohttp session.")
            except Exception as e:
                self.logger.warning(f"关闭 aiohttp session 时出错: {e}")
            finally:
                self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._session and self._session.closed:
                self.logger.debug("现有 session 已关闭，正在创建新 session...")
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            self.logger.debug("已创建新的 aiohttp session.")
        return self._session

    async def _fetch_raw_data(self) -> Optional[Dict[str, Any]]:
        max_retries = 2
        retry_count = 0

        while retry_count <= max_retries:
            session = await self._get_session()
            try:
                async with session.get(self.api_url) as resp:
                    content_type = resp.content_type.lower()
                    if 'application/json' not in content_type:
                        self.logger.warning(f"代理 API 返回非 JSON 内容类型: {content_type} (URL: {self.api_url})")
                        try:
                            text = await resp.text()
                            return {"__raw_text__": text.strip(), "__content_type__": content_type}
                        except Exception as e:
                            self.logger.error(f"读取非 JSON 响应体失败: {repr(e)}")
                            return None

                    if resp.status != 200:
                        try:
                            error_text = await resp.text()
                        except:
                            error_text = "<无法读取响应体>"
                        self.logger.error(f"代理 API 状态码异常: {resp.status}, 响应体: {error_text}")
                        if 400 <= resp.status < 500:
                            return None
                        return None

                    return await resp.json()

            except NETWORK_EXCEPTIONS as e:
                retry_count += 1
                self.logger.warning(f"请求代理 API 失败 (尝试 {retry_count}/{max_retries + 1}): {repr(e)}")
                if retry_count <= max_retries:
                    self.logger.info("正在关闭并重建 session 以进行重试...")
                    await self._close_session()
                else:
                    self.logger.error(f"请求代理 API 失败，已达到最大重试次数 ({max_retries + 1}): {repr(e)}")
                    return None

            except aiohttp.ContentTypeError as e:
                self.logger.error(f"代理 API 响应内容类型错误: {repr(e)}")
                return None

            except Exception as e:
                self.logger.critical(f"请求代理 API 时发生未预期错误: {repr(e)}", exc_info=True)
                return None

        return None

    async def _extract_proxy(self, data: Dict[str, Any]) -> Optional[Union[str, Dict[str, str]]]:
        extractor = self._compile_extractor()
        try:
            result = extractor(data)
            if isinstance(result, str) and result.strip():
                return result.strip()
            elif isinstance(result, dict):
                cleaned = {k: v.strip() for k, v in result.items() if v and isinstance(v, str)}
                return cleaned if cleaned else None
            return None
        except Exception as e:
            self.logger.error(f"执行 PROXY_EXTRACTOR 时出错: {repr(e)}")
            return None

    async def _get_proxy_from_api(self) -> Optional[Union[str, Dict[str, str]]]:
        raw_data = await self._fetch_raw_data()
        if not raw_data:
            return None

        if "__raw_text__" in raw_data:
            text = raw_data["__raw_text__"]
            if text.startswith("http://") or text.startswith("https://"):
                return text

        return await self._extract_proxy(raw_data)

    async def _get_cached_proxy(self) -> Optional[str]:
        if not self.enabled:
            self.logger.debug("ProxyMiddleware 已禁用，跳过代理获取。")
            return None

        now = asyncio.get_event_loop().time()
        if self._current_proxy and (now - self._last_fetch_time) < self.refresh_interval:
            pass
        else:
            proxy = await self._get_proxy_from_api()
            if proxy:
                self._current_proxy = proxy
                self._last_fetch_time = now
                self.logger.debug(f"更新代理缓存: {proxy}")
            else:
                self.logger.warning("无法获取新代理，请求将直连。")

        return self._current_proxy

    @staticmethod
    def _is_https(request: Request) -> bool:
        return urlparse(request.url).scheme == "https"

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        if not self.enabled:
            self.logger.debug(f"ProxyMiddleware 已禁用，请求将直连: {request.url}")
            return None

        if request.proxy:
            return None

        proxy = await self._get_cached_proxy()
        if proxy:
            request.proxy = proxy
            self.logger.info(f"分配代理 → {proxy} | {request.url}")
        else:
            self.logger.warning(f"未获取到代理，请求直连: {request.url}")

        return None

    def process_response(self, request: Request, response: Response, spider) -> Response:
        proxy = request.proxy
        if proxy:
            status_code = getattr(response, 'status_code', 'N/A')
            self.logger.debug(f"代理成功: {proxy} | {request.url} | Status: {status_code}")
        return response

    def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        proxy = request.proxy
        if proxy:
            self.logger.warning(f"代理请求失败: {proxy} | {request.url} | {repr(exception)}")
        return None

    async def close(self):
        await self._close_session()