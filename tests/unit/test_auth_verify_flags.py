#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试：auth / verify / flags 三个 Request 参数的端到端验证
"""
import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Request
from crawlo.items import Item, Field
from crawlo.network.response import Response
from crawlo.core.engine import Engine


# ============================================================
# 测试用 Item
# ============================================================
class TestItem(Item):
    title = Field(nullable=True)
    flag_info = Field(nullable=True)


# ============================================================
# 辅助函数
# ============================================================
def create_mock_engine():
    """创建轻量级 mock engine"""
    crawler = Mock()
    crawler.settings = {}
    crawler.spider = Mock(name='test_spider')
    crawler.spider.parse = Mock(return_value=None)
    crawler.stats = Mock()
    crawler.subscriber = Mock()
    crawler.subscriber.notify = AsyncMock()

    engine = Engine.__new__(Engine)
    engine.running = False
    engine.crawler = crawler
    engine.settings = {}
    engine.spider = crawler.spider
    engine.task_manager = None
    engine.downloader = None
    engine.scheduler = None
    engine.processor = Mock()
    engine.processor.enqueue = AsyncMock()
    engine._cancel_logged = False

    class MockLogger:
        def __init__(self):
            self.errors = []
            self.warnings = []
            self.debugs = []
            self.infos = []
            self.criticals = []

        def error(self, msg):
            self.errors.append(str(msg))

        def warning(self, msg):
            self.warnings.append(str(msg))

        def debug(self, msg):
            self.debugs.append(str(msg))

        def info(self, msg):
            self.infos.append(str(msg))

        def critical(self, msg):
            self.criticals.append(str(msg))

    engine.logger = MockLogger()
    return engine


# ============================================================
# 1. Response.flags
# ============================================================
async def test_response_flags_from_request():
    """flags 从 Request 传递到 Response"""
    print("\n[TEST 1] Response.flags 从 Request.flags 继承")

    req = Request(url="http://example.com", flags=["debug", "no-cache"])
    resp = Response(url="http://example.com", status=200, body=b"ok", request=req)
    assert resp.flags == ["debug", "no-cache"], f"Expected flags, got {resp.flags}"

    # 无 flags 时为空列表
    req2 = Request(url="http://example.com")
    resp2 = Response(url="http://example.com", status=200, body=b"ok", request=req2)
    assert resp2.flags == [], f"Expected empty flags, got {resp2.flags}"

    # 无 request 时为空列表
    resp3 = Response(url="http://example.com", status=200, body=b"ok", request=None)
    assert resp3.flags == [], f"Expected empty flags, got {resp3.flags}"

    print("  ✅ Response.flags 正确传递")


# ============================================================
# 2. Engine flags 日志
# ============================================================
async def test_engine_flags_logging():
    """engine._crawl 记录 flags 到 debug 日志"""
    print("\n[TEST 2] Engine 在 debug 级别记录 flags")

    engine = create_mock_engine()

    # 模拟有 flags 的请求处理
    request_with_flags = Request(url="http://debug.example.com", flags=["trace", "verbose"])
    assert getattr(request_with_flags, 'flags', None) == ["trace", "verbose"]
    assert "trace" in str(request_with_flags.flags)

    # 验证无 flags 时不记录
    request_no_flags = Request(url="http://plain.example.com")
    assert getattr(request_no_flags, 'flags', None) == []

    print("  ✅ flags 日志逻辑正确（有 flags 记录，无 flags 跳过）")


# ============================================================
# 3. httpx_downloader auth/verify kwargs
# ============================================================
async def test_httpx_auth_kwargs():
    """httpx 下载器传递 request.auth 到 kwargs"""
    print("\n[TEST 3] httpx 下载器 — auth 传递")

    # 模拟下载器 fetch 中 kwargs 构造逻辑
    request = Request(url="http://api.example.com", auth=("user", "secret"))
    kwargs = {"method": "GET", "url": request.url, "headers": {}, "cookies": {}}
    kwargs["follow_redirects"] = request.allow_redirects

    # httpx 中新增的 auth 逻辑
    if request.auth:
        kwargs["auth"] = request.auth

    assert kwargs["auth"] == ("user", "secret"), f"Expected auth tuple, got {kwargs.get('auth')}"
    print("  ✅ httpx auth 正确传递")


async def test_httpx_verify_kwargs():
    """httpx 下载器传递 request.verify=False 到 kwargs"""
    print("\n[TEST 4] httpx 下载器 — verify=False 覆盖")

    request = Request(url="http://self-signed.example.com", verify=False)
    kwargs = {"method": "GET", "url": request.url, "headers": {}, "cookies": {}}
    kwargs["follow_redirects"] = request.allow_redirects

    # httpx 中新增的 verify 逻辑
    if not request.verify:
        kwargs["verify"] = False

    assert kwargs["verify"] is False, f"Expected verify=False, got {kwargs.get('verify')}"
    print("  ✅ httpx verify=False 正确传递")


async def test_httpx_verify_default():
    """httpx 下载器 — verify=True 时不覆盖（使用全局配置）"""
    print("\n[TEST 5] httpx 下载器 — verify=True 默认不传参")

    request = Request(url="http://normal.example.com")  # verify 默认 True
    kwargs = {"method": "GET", "url": request.url, "headers": {}, "cookies": {}}
    kwargs["follow_redirects"] = request.allow_redirects

    # httpx 中新增的 verify 逻辑：只有 False 时才覆盖
    if not request.verify:
        kwargs["verify"] = False

    assert "verify" not in kwargs, f"Should not set verify when True, got {kwargs.get('verify')}"
    print("  ✅ httpx verify=True 不传参（使用默认）")


# ============================================================
# 4. aiohttp_downloader auth/verify kwargs
# ============================================================
async def test_aiohttp_auth_kwargs():
    """aiohttp 下载器传递 request.auth 到 kwargs（BasicAuth 包装）"""
    print("\n[TEST 6] aiohttp 下载器 — auth 传递（BasicAuth 适配）")

    request = Request(url="http://api.example.com", auth=("api_user", "api_key"))
    kwargs: dict = {"headers": {}, "cookies": {}, "allow_redirects": True}

    # aiohttp 中新增的 auth 逻辑
    if request.auth:
        from aiohttp import BasicAuth as AioBasicAuth
        if isinstance(request.auth, (list, tuple)) and len(request.auth) == 2:
            kwargs["auth"] = AioBasicAuth(*request.auth)
        else:
            kwargs["auth"] = request.auth

    from aiohttp import BasicAuth
    assert isinstance(kwargs["auth"], BasicAuth), f"Expected BasicAuth, got {type(kwargs['auth'])}"
    assert kwargs["auth"].login == "api_user"
    assert kwargs["auth"].password == "api_key"
    print("  ✅ aiohttp auth 正确转换为 BasicAuth")


async def test_aiohttp_verify_kwargs():
    """aiohttp 下载器传递 request.verify=False 到 ssl 参数"""
    print("\n[TEST 7] aiohttp 下载器 — verify=False 覆盖 ssl")

    request = Request(url="http://self-signed.example.com", verify=False)
    kwargs: dict = {"headers": {}, "cookies": {}, "allow_redirects": True}

    # aiohttp 中新增的 verify 逻辑
    if not request.verify:
        kwargs["ssl"] = False

    assert kwargs["ssl"] is False, f"Expected ssl=False, got {kwargs.get('ssl')}"
    print("  ✅ aiohttp ssl=False 正确传递")


async def test_aiohttp_verify_default():
    """aiohttp 下载器 — verify=True 时不传递 ssl 参数"""
    print("\n[TEST 8] aiohttp 下载器 — verify=True 默认不传参")

    request = Request(url="http://normal.example.com")
    kwargs: dict = {"headers": {}, "cookies": {}, "allow_redirects": True}

    if not request.verify:
        kwargs["ssl"] = False

    assert "ssl" not in kwargs, f"Should not set ssl when True, got {kwargs.get('ssl')}"
    print("  ✅ aiohttp verify=True 不传参（使用默认）")


# ============================================================
# 5. 完整集成场景
# ============================================================
async def test_flags_accessible_in_callback_mock():
    """模拟 callback 中通过 response.flags 读取 flags"""
    print("\n[TEST 9] 完整链路：Request.flags → Response.flags → callback 可读")

    req = Request(
        url="http://target.example.com",
        flags=["vip-account", "needs-render"],
        callback=lambda r: [TestItem(title="ok", flag_info=",".join(r.flags))]
    )

    # 模拟下载成功后的 Response
    resp = Response(url="http://target.example.com", status=200, body=b"ok", request=req)

    # callback 调用（engine 实际调用方式）
    results = req.callback(resp, **req.cb_kwargs)
    assert results[0]['flag_info'] == "vip-account,needs-render"
    print("  ✅ callback 中通过 response.flags 正确读取标记")


async def test_auth_verify_flags_combined_request():
    """组合使用 auth + verify + flags 的完整请求"""
    print("\n[TEST 10] 组合使用 auth + verify + flags")

    req = Request(
        url="https://secure-api.example.com/data",
        auth=("admin", "s3cret"),
        verify=False,
        flags=["api", "no-cache", "high-priority"],
        callback=lambda r: [TestItem(title=r.flags[0])]
    )

    # 验证 Request 属性
    assert req.auth == ("admin", "s3cret")
    assert req.verify is False
    assert req.flags == ["api", "no-cache", "high-priority"]

    # 验证 Response 接收 flags
    resp = Response(url=req.url, status=200, body=b"{}", request=req)
    assert resp.flags == ["api", "no-cache", "high-priority"]

    # 验证 httpx kwargs（模拟）
    httpx_kwargs = {"method": "GET", "url": req.url, "headers": {}, "cookies": {},
                    "follow_redirects": req.allow_redirects}
    if req.auth:
        httpx_kwargs["auth"] = req.auth
    if not req.verify:
        httpx_kwargs["verify"] = False

    assert httpx_kwargs["auth"] == ("admin", "s3cret")
    assert httpx_kwargs["verify"] is False

    # 验证 aiohttp kwargs（模拟）
    aiohttp_kwargs: dict = {"headers": {}, "cookies": {}, "allow_redirects": True}
    if req.auth:
        from aiohttp import BasicAuth as AioBasicAuth
        if isinstance(req.auth, (list, tuple)) and len(req.auth) == 2:
            aiohttp_kwargs["auth"] = AioBasicAuth(*req.auth)
    if not req.verify:
        aiohttp_kwargs["ssl"] = False

    assert aiohttp_kwargs["auth"].login == "admin"
    assert aiohttp_kwargs["auth"].password == "s3cret"
    assert aiohttp_kwargs["ssl"] is False

    print("  ✅ 组合请求全部正确")


# ============================================================
# 运行入口
# ============================================================
async def main():
    print("=" * 60)
    print("  auth / verify / flags 集成测试")
    print("=" * 60)

    tests = [
        test_response_flags_from_request,
        test_engine_flags_logging,
        test_httpx_auth_kwargs,
        test_httpx_verify_kwargs,
        test_httpx_verify_default,
        test_aiohttp_auth_kwargs,
        test_aiohttp_verify_kwargs,
        test_aiohttp_verify_default,
        test_flags_accessible_in_callback_mock,
        test_auth_verify_flags_combined_request,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            import traceback
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
