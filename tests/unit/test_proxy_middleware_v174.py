#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
v1.7.4 代理中间件缺陷修复回归测试（dev/V1.7.4_PLAN.md M2）

覆盖：
- B1 降级副本 dont_filter + 防环计数
- B2 失败代理 TTL 恢复
- B3 动态模式跳过已知失败代理
- B4 失败归因收窄（连接类异常 / 403·407·429 信号）
- B5 日志凭据脱敏
- B6 直连降级 stats 指标
"""
import asyncio
import time
from unittest.mock import Mock

from crawlo.http import Request, Response
from crawlo.middleware.proxy import (
    CONNECTION_EXCEPTIONS,
    ProxyMiddleware,
    mask_proxy,
)
from crawlo.settings.setting_manager import SettingManager


def make_middleware(**overrides) -> ProxyMiddleware:
    settings = SettingManager()
    for key, value in overrides.items():
        settings.set(key, value)
    return ProxyMiddleware(settings, stats=Mock())


def make_request(url="http://target.example/page", proxy=None, **meta) -> Request:
    request = Request(url=url)
    if proxy:
        request.proxy = proxy
    request.meta.update(meta)
    return request


def make_response(request, status=200) -> Response:
    return Response(url=request.url, status=status)


# ----------------------------------------------------------------------
# 基础行为
# ----------------------------------------------------------------------

class TestBasics:

    def test_static_mode_enabled(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"])
        assert mw.enabled and mw.mode == "static"

    def test_dynamic_mode_enabled(self):
        mw = make_middleware(PROXY_API_URL="http://api.example/get")
        assert mw.enabled and mw.mode == "dynamic"

    def test_disabled_without_config(self):
        assert not make_middleware().enabled

    def test_extractor_string_field(self):
        mw = make_middleware(PROXY_API_URL="http://api.example", PROXY_EXTRACTOR="data")
        assert mw._extract_proxy_from_data({"data": "http://ip:port"}) == "http://ip:port"

    def test_extractor_falls_back_to_default_field(self):
        mw = make_middleware(PROXY_API_URL="http://api.example")
        assert mw._extract_proxy_from_data({"proxy": "http://ip:port"}) == "http://ip:port"
        assert mw._extract_proxy_from_data({"other": "x"}) is None


# ----------------------------------------------------------------------
# B5 凭据脱敏
# ----------------------------------------------------------------------

class TestCredentialMasking:

    def test_mask_proxy_hides_credentials(self):
        masked = mask_proxy("http://user:secret@proxy.example.com:8080")
        assert "user" not in masked and "secret" not in masked
        assert masked == "http://***:***@proxy.example.com:8080"

    def test_mask_proxy_keeps_plain_url(self):
        assert mask_proxy("http://proxy.example.com:8080") == "http://proxy.example.com:8080"

    def test_assign_log_masked(self):
        mw = make_middleware(PROXY_LIST=["http://user:secret@p1:8080"])
        mw.logger = Mock()
        request = make_request()
        asyncio.run(mw.process_request(request, None))
        assert request.proxy == "http://user:secret@p1:8080"
        logged = " ".join(str(c.args) for c in mw.logger.info.call_args_list)
        assert "secret" not in logged
        assert "***:***@p1:8080" in logged

    def test_failure_log_masked(self):
        mw = make_middleware(
            PROXY_LIST=["http://user:secret@p1:8080"],
            PROXY_MAX_FAILED_ATTEMPTS=1,
        )
        mw.logger = Mock()
        request = make_request(proxy="http://user:secret@p1:8080")
        asyncio.run(mw.process_exception(request, asyncio.TimeoutError(), None))
        all_logged = (
            " ".join(str(c.args) for c in mw.logger.warning.call_args_list)
            + " ".join(str(c.args) for c in mw.logger.info.call_args_list)
        )
        assert "secret" not in all_logged
        assert "***:***@p1:8080" in all_logged


# ----------------------------------------------------------------------
# B1 降级副本绕过去重 + 防环
# ----------------------------------------------------------------------

class TestDowngradeRetryB1:

    def _downgrade_once(self, mw, request, attempts=1):
        mw.max_failed_attempts = attempts
        mw.proxy_failure_count[request.proxy] = attempts - 1
        return asyncio.run(mw.process_exception(request, asyncio.TimeoutError(), None))

    def test_downgraded_copy_sets_dont_filter(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"])
        request = make_request(proxy="http://p1:8080")
        copy = self._downgrade_once(mw, request)
        assert copy is not None
        assert copy.proxy is None
        assert copy.meta["proxy_downgraded"] is True
        assert copy.meta["dont_filter"] is True
        assert copy.meta["proxy_retry_count"] == 1

    def test_downgrade_budget_exhausted_gives_up(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"], PROXY_MAX_FAILED_ATTEMPTS=1)
        request = make_request(proxy="http://p1:8080", proxy_retry_count=1)
        result = asyncio.run(mw.process_exception(request, asyncio.TimeoutError(), None))
        assert result is None

    def test_non_blacklisting_failure_returns_none(self):
        """未达阈值：只计数，不做任何重试动作"""
        mw = make_middleware(PROXY_LIST=["http://p1:8080"], PROXY_MAX_FAILED_ATTEMPTS=5)
        request = make_request(proxy="http://p1:8080")
        result = asyncio.run(mw.process_exception(request, asyncio.TimeoutError(), None))
        assert result is None
        assert mw.proxy_failure_count["http://p1:8080"] == 1


# ----------------------------------------------------------------------
# B2 失败代理 TTL 恢复
# ----------------------------------------------------------------------

class TestFailedTtlRecoveryB2:

    def test_blacklisted_proxy_excluded_then_recovered_after_ttl(self):
        mw = make_middleware(
            PROXY_LIST=["http://p1:8080"],
            PROXY_MAX_FAILED_ATTEMPTS=1,
            PROXY_FAILED_TTL=0.1,
        )
        request = make_request()

        # 首次选择拿到 p1 并拉黑它
        asyncio.run(mw.process_request(request, None))
        assert request.proxy == "http://p1:8080"
        asyncio.run(mw.process_exception(request, asyncio.TimeoutError(), None))
        assert "http://p1:8080" in mw.failed_proxies

        # TTL 内：池空 → 直连降级指标
        direct_request = make_request()
        asyncio.run(mw.process_request(direct_request, None))
        assert direct_request.proxy is None

        # TTL 过后：代理恢复可选
        time.sleep(0.15)
        recovered = make_request()
        asyncio.run(mw.process_request(recovered, None))
        assert recovered.proxy == "http://p1:8080"
        assert mw.proxy_failure_count.get("http://p1:8080", 0) == 0

    def test_zero_ttl_recovers_immediately(self):
        mw = make_middleware(
            PROXY_LIST=["http://p1:8080"],
            PROXY_MAX_FAILED_ATTEMPTS=1,
            PROXY_FAILED_TTL=0,
        )
        mw._record_failure("http://p1:8080", "test")
        assert mw._is_failed("http://p1:8080") is False


# ----------------------------------------------------------------------
# B3 动态模式跳过已知失败代理
# ----------------------------------------------------------------------

class TestDynamicSkipsBlacklistedB3:

    def test_api_returning_blacklisted_proxy_falls_back_direct(self):
        mw = make_middleware(
            PROXY_API_URL="http://api.example/get",
            PROXY_MAX_FAILED_ATTEMPTS=1,
            PROXY_FAILED_TTL=300,
        )
        bad = "http://dead-ip:8080"
        mw._record_failure(bad, "test")

        async def fake_fetch():
            return bad

        mw._fetch_proxy_from_api = fake_fetch
        request = make_request()
        asyncio.run(mw.process_request(request, None))

        # 不再"warn 后照用"：本轮直连且打点
        assert request.proxy is None
        mw.stats.inc_value.assert_any_call("proxy/direct_downgrade")

    def test_api_returning_healthy_proxy_is_used(self):
        mw = make_middleware(PROXY_API_URL="http://api.example/get")

        async def fake_fetch():
            return "http://fresh-ip:8080"

        mw._fetch_proxy_from_api = fake_fetch
        request = make_request()
        asyncio.run(mw.process_request(request, None))
        assert request.proxy == "http://fresh-ip:8080"


# ----------------------------------------------------------------------
# B4 失败归因收窄
# ----------------------------------------------------------------------

class TestFailureAttributionB4:

    def test_connection_exception_counts_toward_proxy(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"])
        request = make_request(proxy="http://p1:8080")
        exc = asyncio.TimeoutError()
        assert exc in CONNECTION_EXCEPTIONS or isinstance(exc, CONNECTION_EXCEPTIONS)
        asyncio.run(mw.process_exception(request, exc, None))
        assert mw.proxy_failure_count["http://p1:8080"] == 1

    def test_application_exception_not_attributed(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"])
        request = make_request(proxy="http://p1:8080")
        result = asyncio.run(mw.process_exception(request, ValueError("bad data"), None))
        assert result is None
        assert mw.proxy_failure_count.get("http://p1:8080", 0) == 0
        assert mw.failed_proxies == {}

    def test_ban_status_codes_count_as_failures(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"], PROXY_MAX_FAILED_ATTEMPTS=3)
        request = make_request(proxy="http://p1:8080")
        asyncio.run(mw.process_response(request, make_response(request, status=403), None))
        assert mw.proxy_failure_count["http://p1:8080"] == 1
        asyncio.run(mw.process_response(request, make_response(request, status=429), None))
        assert mw.proxy_failure_count["http://p1:8080"] == 2
        assert "http://p1:8080" not in mw.failed_proxies

    def test_success_resets_failure_count(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"])
        mw.proxy_failure_count["http://p1:8080"] = 2
        request = make_request(proxy="http://p1:8080")
        asyncio.run(mw.process_response(request, make_response(request, status=200), None))
        assert mw.proxy_failure_count.get("http://p1:8080", 0) == 0

    def test_threshold_reached_via_ban_signals_blacklists(self):
        mw = make_middleware(PROXY_LIST=["http://p1:8080"], PROXY_MAX_FAILED_ATTEMPTS=2)
        request = make_request(proxy="http://p1:8080")
        asyncio.run(mw.process_response(request, make_response(request, status=403), None))
        asyncio.run(mw.process_response(request, make_response(request, status=407), None))
        assert "http://p1:8080" in mw.failed_proxies


# ----------------------------------------------------------------------
# B6 直连降级指标
# ----------------------------------------------------------------------

class TestDirectDowngradeMetricB6:

    def test_all_blacklisted_emits_metric(self):
        mw = make_middleware(
            PROXY_LIST=["http://p1:8080"],
            PROXY_MAX_FAILED_ATTEMPTS=1,
            PROXY_FAILED_TTL=300,
        )
        mw._record_failure("http://p1:8080", "test")
        request = make_request()
        asyncio.run(mw.process_request(request, None))
        mw.stats.inc_value.assert_any_call("proxy/direct_downgrade")


# ----------------------------------------------------------------------
# 静态模式随机选择排除失败项
# ----------------------------------------------------------------------

class TestStaticSelection:

    def test_selection_excludes_blacklisted(self):
        mw = make_middleware(
            PROXY_LIST=["http://p1:8080", "http://p2:8080"],
            PROXY_MAX_FAILED_ATTEMPTS=1,
            PROXY_FAILED_TTL=300,
        )
        mw._record_failure("http://p1:8080", "test")
        seen = set()
        for _ in range(20):
            request = make_request()
            asyncio.run(mw.process_request(request, None))
            seen.add(request.proxy)
        assert seen == {"http://p2:8080"}
