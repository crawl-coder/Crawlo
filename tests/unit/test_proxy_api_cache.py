#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
代理动态模式成本控制测试（v1.7.5 A1：PROXY_API_TTL 缓存 + 并发单飞）

约定：
- 默认 PROXY_API_TTL=0：逐请求实时拉取，行为与历史版本一致（按次轮换供应商）；
- PROXY_API_TTL>0：TTL 窗口内复用结果 + 同一时刻并发合并为一次真实调用；
- 失败（None）不缓存；缓存命中的代理若已被拉黑 → 走 B3 直连兜底。
"""
import asyncio
from unittest.mock import Mock

import pytest

from crawlo.http.request import Request
from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.settings.setting_manager import SettingManager


def make_middleware(**overrides) -> ProxyMiddleware:
    settings = SettingManager()
    settings.set("PROXY_API_URL", "http://api.example/get")
    for key, value in overrides.items():
        settings.set(key, value)
    return ProxyMiddleware(settings, stats=Mock())


def attach_counter(mw: ProxyMiddleware, result: str = "http://fresh:8080", delay: float = 0):
    """把 _fetch_proxy_from_api 替换为计数桩，返回计数容器"""
    counter = {"calls": 0}

    async def fake_fetch():
        counter["calls"] += 1
        if delay:
            await asyncio.sleep(delay)
        return result if result is not None else None

    mw._fetch_proxy_from_api = fake_fetch  # type: ignore[method-assign]
    return counter


def make_request() -> Request:
    return Request(url="http://target.example/")


class TestTtlDisabled:

    @pytest.mark.asyncio
    async def test_default_fetches_per_request(self):
        """TTL=0（默认）：逐请求实时拉取，N 请求 N 次调用（轮换语义不变）"""
        mw = make_middleware()
        counter = attach_counter(mw)
        for _ in range(5):
            request = make_request()
            await mw.process_request(request, None)
            assert request.proxy == "http://fresh:8080"
        assert counter["calls"] == 5


class TestTtlEnabled:

    @pytest.mark.asyncio
    async def test_cache_hits_within_ttl_window(self):
        """TTL 窗口内复用缓存：多次请求只触发一次真实调用"""
        mw = make_middleware(PROXY_API_TTL=60)
        counter = attach_counter(mw)
        proxies = []
        for _ in range(5):
            request = make_request()
            await mw.process_request(request, None)
            proxies.append(request.proxy)
        assert counter["calls"] == 1
        assert proxies == ["http://fresh:8080"] * 5

    @pytest.mark.asyncio
    async def test_concurrent_requests_share_single_flight(self):
        """16 个并发请求在 TTL 窗口内只触发一次 API 调用（单飞）"""
        mw = make_middleware(PROXY_API_TTL=60)
        counter = attach_counter(mw, delay=0.05)  # 模拟真实 API 延迟放大竞争窗口
        results = await asyncio.gather(*[
            mw.process_request(make_request(), None) for _ in range(16)
        ])
        assert counter["calls"] == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """TTL 过期后重新拉取"""
        mw = make_middleware(PROXY_API_TTL=0.05)
        counter = attach_counter(mw)
        await mw.process_request(make_request(), None)
        assert counter["calls"] == 1
        await asyncio.sleep(0.08)
        await mw.process_request(make_request(), None)
        assert counter["calls"] == 2

    @pytest.mark.asyncio
    async def test_failed_fetch_not_cached(self):
        """失败结果不缓存：下一个请求重新尝试"""
        mw = make_middleware(PROXY_API_TTL=60)
        counter = attach_counter(mw, result=None)  # 第一次拉取失败
        request = make_request()
        await mw.process_request(request, None)
        assert request.proxy is None and counter["calls"] == 1

        counter2 = attach_counter(mw, result="http://recovered:8080")
        request2 = make_request()
        await mw.process_request(request2, None)
        assert request2.proxy == "http://recovered:8080" and counter2["calls"] == 1

    @pytest.mark.asyncio
    async def test_cached_blacklisted_proxy_falls_back_direct(self):
        """缓存的代理被拉黑 → 走直连兜底并打点（B3 路径）"""
        mw = make_middleware(PROXY_API_TTL=60, PROXY_MAX_FAILED_ATTEMPTS=1)
        attach_counter(mw, result="http://cached:8080")
        await mw.process_request(make_request(), None)  # 填充缓存
        # 人为拉黑缓存中的代理
        mw._record_failure("http://cached:8080", "test")

        request = make_request()
        await mw.process_request(request, None)
        assert request.proxy is None
        mw.stats.inc_value.assert_any_call("proxy/direct_downgrade")


class TestSingleFlightFailureSharing:

    @pytest.mark.asyncio
    async def test_waiters_share_failed_result_without_refetch(self):
        """在途等待者共享失败结果，不各自重试（避免惊群二次打爆 API）"""
        mw = make_middleware(PROXY_API_TTL=60)
        counter = attach_counter(mw, result=None, delay=0.03)
        await asyncio.gather(*[
            mw.process_request(make_request(), None) for _ in range(4)
        ])
        assert counter["calls"] == 1
