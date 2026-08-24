#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Generic Proxy Middleware
Supports static proxy list and dynamic proxy API modes

Features:
1. Static proxy mode: randomly select from configured proxy list (excluding failed ones)
2. Dynamic proxy mode: fetch proxy from external API (skip known-failed ones)
3. Failure attribution: only connection-class exceptions & 403/407/429 count
   against the proxy (target-site faults are not misattributed)
4. Failed proxies recover automatically after PROXY_FAILED_TTL (no permanent
   pool death); all-unavailable falls back to direct connection with a
   `proxy/direct_downgrade` stats counter (auto-exposed as Prometheus
   `crawlo_proxy_direct_downgrade_total`)
5. Downgraded retry requests carry `dont_filter` so they are not swallowed
   by the scheduler fingerprint dedup

v1.7.4 rework (dev/V1.7.4_PLAN.md M2):
- B1 downgraded copy is re-scheduled with dont_filter=True + bounded retry count
- B2 failed-proxies gain TTL recovery (PROXY_FAILED_TTL, default 300s)
- B3 dynamic mode no longer uses a known-failed proxy returned by the API
- B4 failure attribution narrowed to connection-class exceptions / ban signals
- B5 proxy credentials are masked in all log output
- B6 direct-downgrade events are recorded to stats
"""
import asyncio
import json
import random
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from crawlo.http import Request, Response
from crawlo.logging import get_logger
from crawlo.middleware.retry import _retry_exceptions as _RETRYABLE_EXCEPTIONS

# 归因为"代理侧问题"的异常集合：与 RetryMiddleware 的可重试异常同源，
# 另加 OSError 覆盖 DNS 解析失败（socket.gaierror）等系统级连接错误。
CONNECTION_EXCEPTIONS: Tuple[type, ...] = tuple(_RETRYABLE_EXCEPTIONS) + (OSError,)

# 视为"代理被目标站识别/封禁"信号的响应状态码
PROXY_BAN_STATUS_CODES = frozenset({403, 407, 429})


def mask_proxy(proxy: Optional[str]) -> str:
    """日志脱敏：隐藏代理 URL 中的用户名/密码（B5）"""
    if not proxy or not isinstance(proxy, str):
        return str(proxy)
    try:
        parts = urlsplit(proxy)
        if parts.username is None and parts.password is None:
            return proxy
        host = parts.hostname or ""
        netloc = f"***:***@{host}"
        if parts.port:
            netloc = f"{netloc}:{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except ValueError:
        return "***masked***"


class ProxyMiddleware:
    """Generic proxy middleware for managing proxy assignment and health tracking"""

    def __init__(self, settings, stats=None):
        self.logger = get_logger(self.__class__.__name__)
        self.stats = stats

        # Get proxy list and API URL
        self.proxies = list(settings.get("PROXY_LIST", []) or [])
        self.api_url = settings.get("PROXY_API_URL") or None
        # 仅支持 JSON 响应顶层字段名（字符串）；jsonpath/自定义函数不受支持
        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")
        # 失败阈值：达到后拉黑
        try:
            self.max_failed_attempts = max(1, int(settings.get("PROXY_MAX_FAILED_ATTEMPTS", 3)))
        except (TypeError, ValueError):
            self.max_failed_attempts = 3
        # 拉黑恢复 TTL（秒）：过期后代理重新可用（B2）
        try:
            self.failed_ttl = max(0.0, float(settings.get("PROXY_FAILED_TTL", 300)))
        except (TypeError, ValueError):
            self.failed_ttl = 300.0
        # 动态 API 结果缓存窗口（秒）：>0 启用缓存 + 并发单飞；默认 0 保持逐请求拉取
        try:
            self.api_ttl = max(0.0, float(settings.get("PROXY_API_TTL", 0)))
        except (TypeError, ValueError):
            self.api_ttl = 0.0
        # (fetched_at_monotonic, proxy)；仅缓存成功结果
        self._api_cache: Optional[Tuple[float, str]] = None
        # 在途拉取的共享 Future（并发单飞）
        self._inflight: Optional[asyncio.Future] = None

        # proxy -> 拉黑时间戳（monotonic）；TTL 过期自动恢复
        self.failed_proxies: Dict[str, float] = {}
        # proxy -> 连续失败计数
        self.proxy_failure_count: Dict[str, int] = {}

        # Determine which mode to enable based on configuration
        if self.proxies:
            self.mode = "static"
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (static mode) with {len(self.proxies)} proxies")
        elif self.api_url:
            self.mode = "dynamic"
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (dynamic mode) | API: {self.api_url}")
        else:
            self.mode = None
            self.enabled = False
            self.logger.info("ProxyMiddleware disabled (no proxy configuration)")

    @classmethod
    def create_instance(cls, crawler):
        return cls(
            settings=crawler.settings,
            stats=getattr(crawler, "stats", None),
        )

    # ------------------------------------------------------------------
    # 健康跟踪工具
    # ------------------------------------------------------------------
    def _inc_stat(self, key: str, count: int = 1) -> None:
        if self.stats is not None:
            try:
                if count == 1:
                    self.stats.inc_value(key)
                else:
                    self.stats.inc_value(key, count)
            except Exception:  # pragma: no cover - stats 故障不应影响代理主流程
                self.logger.debug(f"stats inc_value failed: {key}", exc_info=True)

    def _is_failed(self, proxy: str) -> bool:
        """是否处于拉黑状态（含 TTL 判定，惰性恢复，B2）"""
        blacklisted_at = self.failed_proxies.get(proxy)
        if blacklisted_at is None:
            return False
        if (time.monotonic() - blacklisted_at) >= self.failed_ttl:
            # TTL 过期：恢复代理并清零计数
            del self.failed_proxies[proxy]
            self.proxy_failure_count.pop(proxy, None)
            self.logger.info(f"Proxy {mask_proxy(proxy)} recovered after TTL ({self.failed_ttl:.0f}s)")
            return False
        return True

    def _record_failure(self, proxy: str, reason: str) -> bool:
        """记录一次失败；达到阈值时拉黑。返回是否触发拉黑。"""
        count = self.proxy_failure_count.get(proxy, 0) + 1
        self.proxy_failure_count[proxy] = count
        if count >= self.max_failed_attempts:
            self.failed_proxies[proxy] = time.monotonic()
            self.logger.warning(
                f"Proxy {mask_proxy(proxy)} failed {count} times ({reason}), "
                f"blacklisted for {self.failed_ttl:.0f}s"
            )
            return True
        return False

    def _reset_failure(self, proxy: str) -> None:
        self.failed_proxies.pop(proxy, None)
        self.proxy_failure_count.pop(proxy, None)

    def _fallback_direct(self, request: Request, reason: str) -> None:
        self.logger.warning(f"No proxy available ({reason}), request connecting directly: {request.url}")
        self._inc_stat("proxy/direct_downgrade")

    # ------------------------------------------------------------------
    # 动态代理 API
    # ------------------------------------------------------------------
    async def _fetch_proxy_from_api(self) -> Optional[str]:
        """Fetch proxy from API"""
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Proxy API returned status {resp.status}")
                        return None
                    content_type = resp.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = await resp.json()
                    else:
                        data = json.loads(await resp.text())

                    proxy = self._extract_proxy_from_data(data)
                    if isinstance(proxy, str) and proxy.startswith(("http://", "https://")):
                        return proxy
                    self.logger.warning(
                        f"Proxy API response has no usable http(s) proxy (extractor={self.proxy_extractor!r})"
                    )
        except json.JSONDecodeError as e:
            self.logger.warning(f"Proxy API response JSON parse error: {e}")
        except (UnicodeDecodeError, asyncio.TimeoutError, OSError) as e:
            self.logger.warning(f"Failed to fetch proxy from API: {e!r}")
        except Exception as e:  # noqa: BLE001 - 外部 API 异常不应中断爬取
            self.logger.warning(f"Failed to fetch proxy from API: {e!r}")
        return None

    async def _get_proxy(self) -> Optional[str]:
        """获取动态代理：TTL 缓存（可选）+ 并发单飞。

        - ``PROXY_API_TTL`` <= 0（默认）：每次请求实时拉取，行为与历史版本一致；
        - ``PROXY_API_TTL`` > 0：TTL 窗口内复用缓存结果，同一时刻的并发请求
          合并为一次真实调用——按次计费供应商可显著降低调用量；
          固定出口/包时供应商建议 30-60s。

        失败结果不缓存，下一个请求会重新尝试拉取。
        """
        if self.api_ttl <= 0:
            return await self._fetch_proxy_from_api()

        if self._api_cache is not None:
            fetched_at, cached = self._api_cache
            if (time.monotonic() - fetched_at) < self.api_ttl:
                return cached

        # 并发单飞：已有在途拉取则共享其结果，不重复触发 API
        if self._inflight is not None:
            try:
                return await self._inflight
            except Exception:  # noqa: BLE001 - 拉取失败按无代理处理
                return None

        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._inflight = future
        try:
            proxy = await self._fetch_proxy_from_api()
            if proxy is not None:
                self._api_cache = (time.monotonic(), proxy)
            if not future.done():
                future.set_result(proxy)
            return proxy
        except Exception as e:  # noqa: BLE001 - 防御：_fetch 内部已兜底
            if not future.done():
                future.set_result(None)
            self.logger.warning(f"Proxy fetch task failed: {e!r}")
            return None
        finally:
            self._inflight = None

    def _extract_proxy_from_data(self, data) -> Optional[str]:
        """
        Extract proxy from API response data.

        仅支持 JSON 顶层字段名（字符串）；提取结果必须是 http(s):// 字符串。
        """
        if isinstance(data, dict):
            if isinstance(self.proxy_extractor, str) and self.proxy_extractor in data:
                value = data[self.proxy_extractor]
                return str(value) if value is not None else None
            if "proxy" in data:
                value = data["proxy"]
                return str(value) if value is not None else None
        return None

    # ------------------------------------------------------------------
    # 中间件钩子
    # ------------------------------------------------------------------
    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """Assign proxy to request"""
        if not self.enabled:
            return None

        if request.proxy:
            # Request already has proxy, don't override
            return None

        proxy = None
        if self.mode == "static" and self.proxies:
            # Static mode: randomly select a proxy, excluding blacklisted ones
            available = [p for p in self.proxies if not self._is_failed(p)]
            if available:
                proxy = random.choice(available)  # nosec B311
            else:
                self._fallback_direct(request, "all static proxies blacklisted")
        elif self.mode == "dynamic" and self.api_url:
            # Dynamic mode: fetch proxy from API（经 TTL 缓存/单飞通道）
            proxy = await self._get_proxy()
            if proxy is not None and self._is_failed(proxy):
                # B3：API 返回已知失败代理（未过 TTL）→ 不再"照用"，本轮直连
                self.logger.warning(
                    f"Proxy API returned blacklisted proxy {mask_proxy(proxy)}, "
                    f"skipping to direct connection: {request.url}"
                )
                self._fallback_direct(request, "API returned blacklisted proxy")
                return None

        if proxy:
            request.proxy = proxy
            self.logger.info(f"Assigned proxy {mask_proxy(proxy)} to {request.url}")

        return None

    async def process_response(self, request: Request, response: Response, spider) -> Response:
        """Handle response: success recovers the proxy; ban signals count as failures"""
        if not request.proxy:
            return response

        if response.status in PROXY_BAN_STATUS_CODES:
            # B4：403/407/429 是 IP 被识别/封禁的典型信号，计入代理失败
            self._record_failure(request.proxy, f"HTTP {response.status}")
            self.logger.warning(
                f"Proxy ban signal HTTP {response.status} via "
                f"{mask_proxy(request.proxy)} | {request.url}"
            )
        else:
            self.logger.debug(f"Proxy request successful: {mask_proxy(request.proxy)} | {request.url}")
            self._reset_failure(request.proxy)
        return response

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """Handle proxy failure and downgrade to direct connection (B1/B4)"""
        if not request.proxy:
            return None

        # B4：仅连接类异常归因于代理；目标站故障/业务异常不拉黑代理
        if not isinstance(exception, CONNECTION_EXCEPTIONS):
            self.logger.debug(
                f"Non-connection exception {type(exception).__name__} via proxy "
                f"{mask_proxy(request.proxy)}, not attributed to proxy: {request.url}"
            )
            return None

        blacklisted = self._record_failure(request.proxy, type(exception).__name__)
        if not blacklisted:
            return None

        # 防环：同一请求的代理降级次数有上限（与 MAX_RETRY_TIMES 对齐）
        proxy_retries = int(request.meta.get("proxy_retry_count", 0))
        max_proxy_retries = self.max_failed_attempts
        if proxy_retries >= max_proxy_retries:
            self.logger.error(
                f"Proxy retry budget exhausted ({proxy_retries}), giving up "
                f"proxy switching for: {request.url}"
            )
            return None

        # B1：降级副本必须绕过调度器指纹去重（首次入队时指纹已记录），
        # 否则"换代理/直连再试一次"会被静默过滤；同时带上防环计数。
        self.logger.info(
            f"Downgrading request to direct connection (attempt {proxy_retries + 1}): {request.url}"
        )
        request_copy = request.copy()
        request_copy.proxy = None
        request_copy.meta['proxy_downgraded'] = True
        request_copy.meta['dont_filter'] = True
        request_copy.meta['proxy_retry_count'] = proxy_retries + 1
        return request_copy
