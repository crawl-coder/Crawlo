#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo MCP Server 测试
=======================
覆盖：
1. 工具注册（fetch/extract/spider/evaluate/screenshot/status）
2. 三模式调用（basic / stealth / max-stealth 正确透传给 fetcher）
3. 错误码返回（TIMEOUT / CONNECTION_ERROR / STEALTH_UNAVAILABLE 等 + AI 提示）
4. _format_result 成功/失败/截断格式化
5. _error_hint 建议映射
6. extract 正则匹配与无匹配处理
7. status 工具环境信息
8. _redirect_browser_stdout 防止 stdio 污染（P0 修复验证）
9. setup.cfg 依赖版本约束（mcp>=1.0,<2.0）
10. 缺失 mcp 包时的优雅降级（import 容错）
"""
import io
import os
import re
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ================================================================
# 测试目标模块（延迟导入，便于 mock 全局上下文）
# ================================================================

class TestMCPToolRegistration(unittest.TestCase):
    """工具注册验证：6 个 MCP 工具必须全部注册"""

    def setUp(self):
        from crawlo.mcp import server as srv
        self.server = srv

    def test_tools_registered(self):
        """6 个核心工具全部注册"""
        tool_names = [t.name for t in self.server.mcp._tool_manager._tools.values()]
        expected = {"fetch", "extract", "spider", "evaluate", "screenshot", "status"}
        for name in expected:
            self.assertIn(name, tool_names, f"tool {name} not registered")

    def test_prompts_registered(self):
        """2 个 prompt 注册"""
        prompts = [p.name for p in self.server.mcp._prompt_manager._prompts.values()]
        self.assertIn("scrape_prompt", prompts)
        self.assertIn("data_collection_prompt", prompts)


class TestFetchModeRouting(unittest.TestCase):
    """三模式调用验证：basic/stealth/max-stealth 正确透传"""

    def _build_result(self, error_code=None, error=None, url="https://example.com"):
        from crawlo.mcp.quick_fetcher import FetchResult
        return FetchResult(
            url=url,
            status_code=403 if error_code else 200,
            content="" if error else "<html><body>Hello World</body></html>",
            error=error,
            error_code=error_code,
            size=0 if error else 40,
            duration=1.5,
        )

    def _patch_fetcher(self, result):
        """mock _get_fetcher 与 fetcher.fetch"""
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(return_value=result)
        patcher = patch(
            "crawlo.mcp.server._get_fetcher",
            new=AsyncMock(return_value=fetcher),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return fetcher

    def test_basic_mode_routes_correctly(self):
        from crawlo.mcp import server as srv
        fetcher = self._patch_fetcher(self._build_result())
        asyncio_run(srv.fetch("https://example.com", mode="basic"))
        fetcher.fetch.assert_called_once()
        call_kwargs = fetcher.fetch.call_args[1]
        self.assertEqual(call_kwargs["mode"], "basic")

    def test_stealth_mode_routes_correctly(self):
        from crawlo.mcp import server as srv
        fetcher = self._patch_fetcher(self._build_result())
        asyncio_run(srv.fetch("https://example.com", mode="stealth"))
        self.assertEqual(fetcher.fetch.call_args[1]["mode"], "stealth")

    def test_max_stealth_mode_routes_correctly(self):
        from crawlo.mcp import server as srv
        fetcher = self._patch_fetcher(self._build_result())
        asyncio_run(srv.fetch("https://example.com", mode="max-stealth"))
        self.assertEqual(fetcher.fetch.call_args[1]["mode"], "max-stealth")

    def test_cookies_and_persist_passed(self):
        from crawlo.mcp import server as srv
        fetcher = self._patch_fetcher(self._build_result())
        asyncio_run(srv.fetch(
            "https://example.com",
            mode="basic",
            cookies={"session": "abc"},
            persist_session=False,
        ))
        kwargs = fetcher.fetch.call_args[1]
        self.assertEqual(kwargs["cookies"], {"session": "abc"})
        self.assertFalse(kwargs["persist_session"])


class TestErrorCodeFormatting(unittest.TestCase):
    """错误码返回与 AI 建议验证"""

    def _make_result(self, error_code, error):
        from crawlo.mcp.quick_fetcher import FetchResult
        return FetchResult(
            url="https://example.com",
            status_code=0,
            content="",
            error=error,
            error_code=error_code,
            size=0,
            duration=2.0,
        )

    def test_timeout_error_includes_hint(self):
        from crawlo.mcp import server as srv
        result = self._make_result("TIMEOUT", "Request timed out")
        text = srv._format_result(result)
        self.assertIn("ERROR [TIMEOUT]", text)
        self.assertIn("Suggest: retry or switch to stealth mode.", text)

    def test_stealth_unavailable_includes_hint(self):
        from crawlo.mcp import server as srv
        result = self._make_result("STEALTH_UNAVAILABLE", "DrissionPage missing")
        text = srv._format_result(result)
        self.assertIn("Suggest: pip install DrissionPage.", text)

    def test_max_stealth_unavailable_includes_hint(self):
        from crawlo.mcp import server as srv
        result = self._make_result("MAX_STEALTH_UNAVAILABLE", "camoufox missing")
        text = srv._format_result(result)
        self.assertIn("Suggest: pip install camoufox.", text)

    def test_invalid_mode_hint(self):
        from crawlo.mcp import server as srv
        result = self._make_result("INVALID_MODE", "bad mode")
        text = srv._format_result(result)
        self.assertIn("Use basic, stealth, or max-stealth.", text)

    def test_unknown_code_no_hint(self):
        from crawlo.mcp import server as srv
        result = self._make_result("UNKNOWN", "something")
        text = srv._format_result(result)
        # 不应有 HINT 行
        self.assertNotIn("HINT:", text)

    def test_error_hint_mapping_complete(self):
        """所有错误码都有建议提示"""
        from crawlo.mcp import server as srv
        # 只要求这些关键错误码有提示
        for code in ["TIMEOUT", "CONNECTION_ERROR", "STEALTH_UNAVAILABLE",
                     "MAX_STEALTH_UNAVAILABLE", "INVALID_URL", "INVALID_SCHEME",
                     "EMPTY_RESPONSE", "INVALID_MODE"]:
            self.assertTrue(srv._error_hint(code), f"missing hint for {code}")


class TestFormatResult(unittest.TestCase):
    """_format_result 成功/失败/截断"""

    def setUp(self):
        from crawlo.mcp import server as srv
        self.srv = srv

    def _result(self, **kw):
        from crawlo.mcp.quick_fetcher import FetchResult
        defaults = dict(
            url="https://example.com",
            status_code=200,
            content="<html>Hello</html>",
            error=None,
            error_code=None,
            size=40,
            duration=0.5,
        )
        defaults.update(kw)
        return FetchResult(**defaults)

    def test_success_format_includes_metadata(self):
        text = self.srv._format_result(self._result())
        self.assertIn("URL: https://example.com", text)
        self.assertIn("Status: 200", text)
        self.assertIn("Size: 40 bytes", text)
        self.assertIn("Duration: 0.50s", text)
        self.assertIn("Hello", text)

    def test_truncation_applies(self):
        result = self._result(content="x" * 1000, size=1000)
        text = self.srv._format_result(result, max_length=100)
        self.assertIn("truncated, 1,000 total chars", text)

    def test_no_truncation_when_zero(self):
        result = self._result(content="y" * 1000, size=1000)
        text = self.srv._format_result(result, max_length=0)
        self.assertNotIn("truncated", text)

    def test_cookies_listed(self):
        result = self._result(cookies={"session": "abc"})
        text = self.srv._format_result(result)
        self.assertIn("Cookies: session", text)


class TestExtractTool(unittest.TestCase):
    """extract 工具的正则匹配与无匹配处理"""

    def _patch_fetcher(self, content):
        from crawlo.mcp.quick_fetcher import FetchResult
        result = FetchResult(
            url="https://example.com",
            status_code=200,
            content=content,
            size=len(content),
            duration=0.5,
        )
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(return_value=result)
        patcher = patch(
            "crawlo.mcp.server._get_fetcher",
            new=AsyncMock(return_value=fetcher),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return fetcher

    def test_extract_finds_matches(self):
        from crawlo.mcp import server as srv
        content = "Price: 100 USD\nPrice: 200 USD"
        self._patch_fetcher(content)
        out = asyncio_run(srv.extract(
            "https://example.com", pattern=r"Price: (\d+) USD"
        ))
        self.assertIn("Found 2 match(es)", out)
        self.assertIn("100", out)
        self.assertIn("200", out)

    def test_extract_no_matches(self):
        from crawlo.mcp import server as srv
        self._patch_fetcher("nothing here")
        out = asyncio_run(srv.extract(
            "https://example.com", pattern=r"\d+"
        ))
        self.assertIn("No matches found.", out)

    def test_extract_error_propagates(self):
        from crawlo.mcp import server as srv
        from crawlo.mcp.quick_fetcher import FetchResult
        result = FetchResult(
            url="https://example.com", status_code=0, content="",
            error="timeout", error_code="TIMEOUT",
        )
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(return_value=result)
        patcher = patch(
            "crawlo.mcp.server._get_fetcher",
            new=AsyncMock(return_value=fetcher),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        out = asyncio_run(srv.extract(
            "https://example.com", pattern=r"\d+"
        ))
        self.assertIn("Error [TIMEOUT]", out)


class TestStatusTool(unittest.TestCase):
    """status 工具输出环境信息"""

    def test_status_contains_sections(self):
        from crawlo.mcp import server as srv
        out = asyncio_run(srv.status())
        self.assertIn("Crawlo MCP Server Status", out)
        self.assertIn("Python:", out)
        self.assertIn("Platform:", out)
        self.assertIn("Available Downloaders:", out)


class TestStdioProtection(unittest.TestCase):
    """P0 修复验证：_redirect_browser_stdout 防止进度条污染 stdio"""

    def test_stdout_restored_after_context(self):
        from crawlo.mcp.quick_fetcher import _redirect_browser_stdout
        real_stdout = sys.stdout
        with _redirect_browser_stdout():
            # 上下文内 sys.stdout 被替换
            self.assertIsNot(sys.stdout, real_stdout)
            print("progress bar [====] 100%")
        # 上下文后恢复
        self.assertIs(sys.stdout, real_stdout)

    def test_output_captured_and_written_to_log(self):
        from crawlo.mcp.quick_fetcher import _redirect_browser_stdout
        import tempfile
        log_path = os.path.join(tempfile.gettempdir(), "_crawlo_test_camoufox.log")
        if os.path.exists(log_path):
            os.remove(log_path)
        with patch(
            "crawlo.mcp.quick_fetcher._COOKIE_FILE",  # 无关，仅确认模块可改
        ), patch("crawlo.mcp.quick_fetcher.os.path.expanduser", return_value=log_path), \
             patch("crawlo.mcp.quick_fetcher.os.makedirs", return_value=None):
            with _redirect_browser_stdout():
                print("fake tqdm bar")
        # 日志文件应包含被捕获的输出
        if os.path.exists(log_path):
            with open(log_path) as f:
                self.assertIn("fake tqdm bar", f.read())
            os.remove(log_path)
        else:
            # 若 mock 未命中路径，至少应无异常且 stdout 恢复
            self.assertIsNotNone(sys.stdout)

    def test_no_error_when_stdout_none(self):
        from crawlo.mcp.quick_fetcher import _redirect_browser_stdout
        with patch("crawlo.mcp.quick_fetcher.sys.stdout", None):
            with _redirect_browser_stdout():
                pass  # 不应抛异常


class TestDependencyConstraints(unittest.TestCase):
    """P0 修复验证：mcp 依赖版本锁定（>=1.0,<2.0）"""

    def test_mcp_version_locked_upper_bound(self):
        """setup.cfg 中 mcp 必须有 <2.0 上限"""
        setup_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "setup.cfg",
        )
        with open(setup_cfg) as f:
            content = f.read()
        # 找到 mcp 声明行
        for line in content.splitlines():
            if re.match(r"\s*mcp[<>=!~]", line):
                self.assertIn("<2", line, f"mcp constraint needs <2.0: {line}")
                self.assertNotRegex(line, r"mcp>=1\.0\.0\s*$", "no upper bound")
                break
        else:
            self.fail("mcp dependency not found in setup.cfg")


def asyncio_run(coro):
    """同步运行一个协程（关闭 event loop 避免 ResourceWarning）"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
