#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import asyncio
import socket
from urllib.parse import urlparse
from typing import Optional, Dict, Any, Callable, Union, TYPE_CHECKING, List


from crawlo import Request, Response
from crawlo.exceptions import NotConfiguredError
from crawlo.utils.log import get_logger

if TYPE_CHECKING:
    import aiohttp

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

class Proxy:
    """代理对象，包含代理信息和统计数据"""
    def __init__(self, proxy_str: str):
        self.proxy_str = proxy_str
        self.success_count = 0
        self.failure_count = 0
        self.last_used_time = 0.0
        self.is_healthy = True
        
    @property
    def success_rate(self) -> float:
        """计算代理成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
        
    def mark_success(self):
        """标记代理使用成功"""
        self.success_count += 1
        self.last_used_time = time.time()
        self.is_healthy = True
        
    def mark_failure(self):
        """标记代理使用失败"""
        self.failure_count += 1
        self.last_used_time = time.time()
        # 如果失败率过高，标记为不健康
        if self.failure_count > 3 and self.success_rate < 0.5:
            self.is_healthy = False

class ProxyMiddleware:
    def __init__(self, settings, log_level):
        self.logger = get_logger(self.__class__.__name__, log_level)

        self._session: Optional[Any] = None  # aiohttp.ClientSession when aiohttp is available
        # 将单个代理改为代理池
        self._proxy_pool: List[Proxy] = []
        self._current_proxy_index: int = 0
        self._last_fetch_time: float = 0

        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")
        self.refresh_interval = settings.get_float("PROXY_REFRESH_INTERVAL", 60)
        self.timeout = settings.get_float("PROXY_API_TIMEOUT", 10)
        # 新增配置：代理池大小
        self.proxy_pool_size = settings.get_int("PROXY_POOL_SIZE", 5)
        # 新增配置：健康检查阈值
        self.health_check_threshold = settings.get_float("PROXY_HEALTH_CHECK_THRESHOLD", 0.5)

        self.enabled = settings.get_bool("PROXY_ENABLED", True)

        if not self.enabled:
            self.logger.info("ProxyMiddleware 已被禁用 (PROXY_ENABLED=False)")
            return

        self.api_url = settings.get("PROXY_API_URL")
        if not self.api_url:
            raise NotConfiguredError("PROXY_API_URL 未配置，ProxyMiddleware 已禁用")

        self.logger.info(f"代理中间件已启用 | API: {self.api_url} | 刷新间隔: {self.refresh_interval}s | 代理池大小: {self.proxy_pool_size}")

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

    async def _get_session(self) -> Any:  # returns aiohttp.ClientSession when aiohttp is available
        if aiohttp is None:
            raise RuntimeError("aiohttp 未安装，无法使用 ProxyMiddleware")
            
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
                cleaned = {k: v.strip() if isinstance(v, str) else v for k, v in result.items()}
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

    async def _update_proxy_pool(self):
        """更新代理池"""
        if not self.enabled:
            self.logger.debug("ProxyMiddleware 已禁用，跳过代理获取。")
            return

        now = asyncio.get_event_loop().time()
        if (now - self._last_fetch_time) < self.refresh_interval:
            return

        # 获取新的代理列表
        proxy_data = await self._get_proxy_from_api()
        if not proxy_data:
            self.logger.warning("无法获取新代理，代理池将保持现状。")
            return

        # 解析代理数据
        new_proxies = []
        if isinstance(proxy_data, str):
            # 单个代理
            new_proxies = [proxy_data]
        elif isinstance(proxy_data, dict):
            # 如果是字典，尝试提取代理列表
            for key, value in proxy_data.items():
                if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                    new_proxies.append(value)
                elif isinstance(value, list):
                    # 如果值是列表，添加所有有效的代理
                    for item in value:
                        if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                            new_proxies.append(item)
        
        # 创建新的代理池
        if new_proxies:
            self._proxy_pool = [Proxy(proxy_str) for proxy_str in new_proxies[:self.proxy_pool_size]]
            self._current_proxy_index = 0
            self._last_fetch_time = now
            self.logger.info(f"更新代理池，新增 {len(self._proxy_pool)} 个代理")
        else:
            self.logger.warning("未解析到有效代理，代理池将保持现状。")

    async def _get_healthy_proxy(self) -> Optional[Proxy]:
        """从代理池中获取一个健康的代理"""
        if not self._proxy_pool:
            await self._update_proxy_pool()
            
        if not self._proxy_pool:
            return None
            
        # 查找健康的代理
        healthy_proxies = [p for p in self._proxy_pool if p.is_healthy and p.success_rate >= self.health_check_threshold]
        
        if not healthy_proxies:
            # 如果没有健康的代理，尝试更新代理池
            await self._update_proxy_pool()
            healthy_proxies = [p for p in self._proxy_pool if p.is_healthy and p.success_rate >= self.health_check_threshold]
            
        if not healthy_proxies:
            return None
            
        # 使用轮询方式选择代理
        self._current_proxy_index = (self._current_proxy_index + 1) % len(healthy_proxies)
        selected_proxy = healthy_proxies[self._current_proxy_index]
        return selected_proxy

    @staticmethod
    def _is_https(request: Request) -> bool:
        return urlparse(request.url).scheme == "https"

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        if not self.enabled:
            self.logger.debug(f"ProxyMiddleware 已禁用，请求将直连: {request.url}")
            return None

        if request.proxy:
            return None

        proxy_obj = await self._get_healthy_proxy()
        if proxy_obj:
            proxy = proxy_obj.proxy_str
            # 处理带认证的代理URL
            if isinstance(proxy, str) and "@" in proxy and "://" in proxy:
                # 解析带认证的代理URL
                parsed = urlparse(proxy)
                if parsed.username and parsed.password:
                    # 对于AioHttp下载器，需要特殊处理认证信息
                    downloader_type = spider.crawler.settings.get("DOWNLOADER_TYPE", "aiohttp")
                    if downloader_type == "aiohttp":
                        # 将认证信息存储在meta中，由下载器处理
                        request.meta["proxy_auth"] = {
                            "username": parsed.username,
                            "password": parsed.password
                        }
                        # 清理URL中的认证信息
                        clean_proxy = f"{parsed.scheme}://{parsed.hostname}"
                        if parsed.port:
                            clean_proxy += f":{parsed.port}"
                        request.proxy = clean_proxy
                    else:
                        # 其他下载器可以直接使用带认证的URL
                        request.proxy = proxy
                else:
                    request.proxy = proxy
            else:
                request.proxy = proxy
            
            # 记录使用的代理
            request.meta["_used_proxy"] = proxy_obj
            self.logger.info(f"分配代理 → {proxy} | {request.url}")
        else:
            self.logger.warning(f"未获取到代理，请求直连: {request.url}")

        return None

    def process_response(self, request: Request, response: Response, spider) -> Response:
        proxy_obj = request.meta.get("_used_proxy")
        if proxy_obj and isinstance(proxy_obj, Proxy):
            proxy_obj.mark_success()
            status_code = getattr(response, 'status_code', 'N/A')
            self.logger.debug(f"代理成功: {proxy_obj.proxy_str} | {request.url} | Status: {status_code}")
        elif request.proxy:
            status_code = getattr(response, 'status_code', 'N/A')
            self.logger.debug(f"代理成功: {request.proxy} | {request.url} | Status: {status_code}")
        return response

    def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        proxy_obj = request.meta.get("_used_proxy")
        if proxy_obj and isinstance(proxy_obj, Proxy):
            proxy_obj.mark_failure()
            self.logger.warning(f"代理请求失败: {proxy_obj.proxy_str} | {request.url} | {repr(exception)}")
        elif request.proxy:
            self.logger.warning(f"代理请求失败: {request.proxy} | {request.url} | {repr(exception)}")
        return None

    async def close(self):
        await self._close_session()