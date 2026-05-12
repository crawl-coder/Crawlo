#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
浏览器下载器代理切换功能测试
============================

测试覆盖：
1. CloakBrowserDownloader: Context 级代理切换
2. PlaywrightDownloader: Context 级代理切换
3. CamoufoxDownloader: 浏览器重启式代理切换

测试场景：
- 代理变化检测（request.proxy 与当前代理不同）
- 代理降级（proxy_downgraded 标记）
- 无代理变化（request.proxy 为 None，无 downgrade 标记）
- 持久化模式无法重建 Context（CloakBrowser）
- Context/浏览器重建逻辑
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==============================================================================
# 通用 Mock 工具
# ==============================================================================

def make_mock_request(url="https://example.com", proxy=None, proxy_downgraded=False, meta=None):
    """创建模拟 Request 对象"""
    request = Mock()
    request.url = url
    request.proxy = proxy
    request.meta = meta or {}
    if proxy_downgraded:
        request.meta['proxy_downgraded'] = True
    request.headers = {}
    request.cookies = {}
    return request


def make_cloakbrowser_mock_crawler(**overrides):
    """创建 CloakBrowser 下载器的模拟 Crawler"""
    crawler = Mock()
    defaults = {
        'CLOAKBROWSER_HEADLESS': True,
        'CLOAKBROWSER_HUMANIZE': False,
        'CLOAKBROWSER_GEOIP': False,
        'CLOAKBROWSER_STEALTH_ARGS': True,
        'CLOAKBROWSER_AUTO_SCROLL': False,
        'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
        'DOWNLOAD_STATS': True,
    }
    bool_overrides = overrides.pop('bool_overrides', {})
    defaults.update(bool_overrides)

    crawler.settings = Mock()
    crawler.settings.get_bool = Mock(side_effect=lambda key, default: defaults.get(key, default))
    crawler.settings.get = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_int = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_list = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    return crawler


def make_playwright_mock_crawler(**overrides):
    """创建 Playwright 下载器的模拟 Crawler"""
    crawler = Mock()
    bool_defaults = {
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        'PLAYWRIGHT_BLOCK_ADS': True,
        'PLAYWRIGHT_BLOCK_WEBRTC': False,
        'PLAYWRIGHT_HIDE_CANVAS': False,
        'PLAYWRIGHT_ALLOW_WEBGL': True,
        'PLAYWRIGHT_REAL_CHROME': False,
        'PLAYWRIGHT_GOOGLE_REFERER': True,
        'PLAYWRIGHT_IGNORE_HTTPS_ERRORS': True,
        'PLAYWRIGHT_AUTO_SCROLL': False,
        'DOWNLOAD_STATS': True,
    }
    crawler.settings = Mock()
    crawler.settings.get_bool = Mock(side_effect=lambda key, default: bool_defaults.get(key, default))
    crawler.settings.get = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_int = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_list = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    return crawler


def make_camoufox_mock_crawler(**overrides):
    """创建 Camoufox 下载器的模拟 Crawler"""
    crawler = Mock()
    bool_defaults = {
        'CAMOUFOX_HEADLESS': True,
        'CAMOUFOX_HUMANIZE': True,
        'CAMOUFOX_SOLVE_CLOUDFLARE': True,
        'CAMOUFOX_AUTO_SCROLL': False,
        'DOWNLOAD_STATS': True,
    }
    crawler.settings = Mock()
    crawler.settings.get_bool = Mock(side_effect=lambda key, default: bool_defaults.get(key, default))
    crawler.settings.get = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_int = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.settings.get_list = Mock(side_effect=lambda key, default: overrides.get(key, default))
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    return crawler


# ==============================================================================
# CloakBrowserDownloader 代理切换测试
# ==============================================================================

class TestCloakBrowserProxySwitching:
    """CloakBrowserDownloader 代理切换功能测试"""

    @pytest.fixture
    def downloader(self):
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        crawler = make_cloakbrowser_mock_crawler(
            CLOAKBROWSER_PROXY=None,
            PROXY_API_URL=None,
        )
        dl = CloakBrowserDownloader(crawler)
        # 模拟已初始化状态
        dl._browser = AsyncMock()
        dl._context = AsyncMock()
        dl._page_semaphore = asyncio.Semaphore(10)
        dl._page_pool = []
        dl._used_pages = set()
        dl._current_proxy = None
        return dl

    # ---- _check_proxy_change 测试 ----

    @pytest.mark.asyncio
    async def test_no_proxy_change_when_request_proxy_is_none(self, downloader):
        """request.proxy 为 None 且无 proxy_downgraded 标记时，不触发代理切换"""
        request = make_mock_request(proxy=None, proxy_downgraded=False)

        # _rebuild_context 不应被调用
        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_change_detected_when_proxy_differs(self, downloader):
        """request.proxy 与当前代理不同时，触发代理切换"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-b:8081")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_called_once_with("http://proxy-b:8081")

    @pytest.mark.asyncio
    async def test_proxy_change_not_triggered_when_same_proxy(self, downloader):
        """request.proxy 与当前代理相同时，不触发切换"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-a:8080")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_downgraded_to_direct(self, downloader):
        """proxy_downgraded 标记触发降级为直连"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy=None, proxy_downgraded=True)

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_proxy_downgrade_no_op_when_already_direct(self, downloader):
        """已为直连时，proxy_downgraded 不触发切换"""
        downloader._current_proxy = None
        request = make_mock_request(proxy=None, proxy_downgraded=True)

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_persistent_context_warns_on_proxy_change(self, downloader):
        """持久化模式下代理切换只打印警告，不重建 Context"""
        downloader.persistent_context = True
        downloader.user_data_dir = "/tmp/test_data"
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-b:8081")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_browser_returns_early(self, downloader):
        """browser 为 None 时直接返回"""
        downloader._browser = None
        request = make_mock_request(proxy="http://proxy-a:8080")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    # ---- _rebuild_context 测试 ----

    @pytest.mark.asyncio
    async def test_rebuild_context_closes_old_and_creates_new(self, downloader):
        """重建 Context：关闭旧 Context 和页面，创建新 Context"""
        old_context = AsyncMock()
        old_page1 = AsyncMock()
        old_page2 = AsyncMock()
        new_context = AsyncMock()

        downloader._context = old_context
        downloader._page_pool = [old_page1, old_page2]
        downloader._used_pages = {id(old_page1)}
        downloader._create_context = AsyncMock(return_value=new_context)

        await downloader._rebuild_context("http://new-proxy:8080")

        # 验证旧页面被关闭
        old_page1.close.assert_called_once()
        old_page2.close.assert_called_once()
        # 验证旧 Context 被关闭
        old_context.close.assert_called_once()
        # 验证创建了新 Context
        downloader._create_context.assert_called_once_with("http://new-proxy:8080")
        # 验证新 Context 被设置
        assert downloader._context == new_context
        # 验证页面池被清空
        assert downloader._page_pool == []
        assert downloader._used_pages == set()

    @pytest.mark.asyncio
    async def test_rebuild_context_with_none_proxy(self, downloader):
        """重建 Context 为直连模式（proxy=None）"""
        new_context = AsyncMock()
        downloader._create_context = AsyncMock(return_value=new_context)

        await downloader._rebuild_context(None)

        downloader._create_context.assert_called_once_with(None)
        assert downloader._context == new_context

    # ---- _create_context 测试 ----

    @pytest.mark.asyncio
    async def test_create_context_with_string_proxy(self, downloader):
        """创建带字符串代理的 Context"""
        mock_context = AsyncMock()
        downloader._browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context("http://proxy:8080")

        downloader._browser.new_context.assert_called_once()
        call_kwargs = downloader._browser.new_context.call_args[1]
        assert call_kwargs["proxy"] == {"server": "http://proxy:8080"}
        assert result == mock_context
        assert downloader._current_proxy == "http://proxy:8080"

    @pytest.mark.asyncio
    async def test_create_context_with_dict_proxy(self, downloader):
        """创建带字典代理的 Context"""
        proxy_dict = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        mock_context = AsyncMock()
        downloader._browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context(proxy_dict)

        call_kwargs = downloader._browser.new_context.call_args[1]
        assert call_kwargs["proxy"] == proxy_dict
        assert downloader._current_proxy == proxy_dict

    @pytest.mark.asyncio
    async def test_create_context_without_proxy(self, downloader):
        """创建无代理的直连 Context"""
        mock_context = AsyncMock()
        downloader._browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context(None)

        call_kwargs = downloader._browser.new_context.call_args[1]
        assert "proxy" not in call_kwargs
        assert downloader._current_proxy is None


# ==============================================================================
# PlaywrightDownloader 代理切换测试
# ==============================================================================

class TestPlaywrightProxySwitching:
    """PlaywrightDownloader 代理切换功能测试"""

    @pytest.fixture
    def downloader(self):
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        crawler = make_playwright_mock_crawler(
            PLAYWRIGHT_PROXY=None,
        )
        dl = PlaywrightDownloader(crawler)
        # 模拟已初始化状态
        dl.playwright = AsyncMock()
        dl.browser = AsyncMock()
        dl.context = AsyncMock()
        dl._page_pool = []
        dl._used_pages = set()
        dl._page_semaphore = asyncio.Semaphore(10)
        dl._current_proxy = None
        return dl

    # ---- _check_proxy_change 测试 ----

    @pytest.mark.asyncio
    async def test_no_proxy_change_when_request_proxy_is_none(self, downloader):
        """request.proxy 为 None 且无 proxy_downgraded 标记时，不触发切换"""
        request = make_mock_request(proxy=None, proxy_downgraded=False)

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_change_detected_when_proxy_differs(self, downloader):
        """request.proxy 与当前代理不同时，触发 Context 重建"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-b:8081")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_called_once_with("http://proxy-b:8081")

    @pytest.mark.asyncio
    async def test_proxy_change_not_triggered_when_same_proxy(self, downloader):
        """request.proxy 与当前代理相同时，不触发切换"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-a:8080")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_downgraded_to_direct(self, downloader):
        """proxy_downgraded 标记触发降级为直连"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy=None, proxy_downgraded=True)

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_no_browser_returns_early(self, downloader):
        """browser 为 None 时直接返回"""
        downloader.browser = None
        request = make_mock_request(proxy="http://proxy-a:8080")

        downloader._rebuild_context = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._rebuild_context.assert_not_called()

    # ---- _rebuild_context 测试 ----

    @pytest.mark.asyncio
    async def test_rebuild_context_closes_old_and_creates_new(self, downloader):
        """重建 Context：关闭旧 Context 和页面，创建新 Context"""
        old_context = AsyncMock()
        old_page1 = AsyncMock()
        old_page2 = AsyncMock()
        new_context = AsyncMock()

        downloader.context = old_context
        downloader._page_pool = [old_page1, old_page2]
        downloader._used_pages = {id(old_page1)}
        downloader._create_context = AsyncMock(return_value=new_context)
        downloader._apply_global_settings = AsyncMock()

        await downloader._rebuild_context("http://new-proxy:8080")

        old_page1.close.assert_called_once()
        old_page2.close.assert_called_once()
        old_context.close.assert_called_once()
        downloader._create_context.assert_called_once_with("http://new-proxy:8080")
        assert downloader.context == new_context
        assert downloader._page_pool == []
        assert downloader._used_pages == set()
        downloader._apply_global_settings.assert_called_once()

    # ---- _create_context 测试 ----

    @pytest.mark.asyncio
    async def test_create_context_with_string_proxy(self, downloader):
        """创建带字符串代理的 Context"""
        mock_context = AsyncMock()
        downloader.browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context("http://proxy:8080")

        call_kwargs = downloader.browser.new_context.call_args[1]
        assert call_kwargs["proxy"] == {"server": "http://proxy:8080"}
        assert downloader._current_proxy == "http://proxy:8080"

    @pytest.mark.asyncio
    async def test_create_context_with_dict_proxy(self, downloader):
        """创建带字典代理的 Context"""
        proxy_dict = {"server": "http://proxy:8080", "username": "user", "password": "pass"}
        mock_context = AsyncMock()
        downloader.browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context(proxy_dict)

        call_kwargs = downloader.browser.new_context.call_args[1]
        assert call_kwargs["proxy"] == proxy_dict

    @pytest.mark.asyncio
    async def test_create_context_without_proxy(self, downloader):
        """创建无代理的直连 Context"""
        mock_context = AsyncMock()
        downloader.browser.new_context = AsyncMock(return_value=mock_context)

        result = await downloader._create_context(None)

        call_kwargs = downloader.browser.new_context.call_args[1]
        assert "proxy" not in call_kwargs
        assert downloader._current_proxy is None


# ==============================================================================
# CamoufoxDownloader 代理切换测试
# ==============================================================================

class TestCamoufoxProxySwitching:
    """CamoufoxDownloader 代理切换功能测试"""

    @pytest.fixture
    def downloader(self):
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader
        crawler = make_camoufox_mock_crawler(
            CAMOUFOX_PROXY=None,
        )
        dl = CamoufoxDownloader(crawler)
        # 模拟已初始化状态
        dl._browser = AsyncMock()
        dl._context = AsyncMock()
        dl._page_pool = []
        dl._used_pages = set()
        dl._current_proxy = None
        return dl

    # ---- _check_proxy_change 测试 ----

    @pytest.mark.asyncio
    async def test_no_proxy_change_when_request_proxy_is_none(self, downloader):
        """request.proxy 为 None 且无 proxy_downgraded 标记时，不触发切换"""
        request = make_mock_request(proxy=None, proxy_downgraded=False)

        downloader._restart_browser = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._restart_browser.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_change_detected_when_proxy_differs(self, downloader):
        """request.proxy 与当前代理不同时，触发浏览器重启"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-b:8081")

        downloader._restart_browser = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._restart_browser.assert_called_once_with("http://proxy-b:8081")

    @pytest.mark.asyncio
    async def test_proxy_change_not_triggered_when_same_proxy(self, downloader):
        """request.proxy 与当前代理相同时，不触发重启"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy="http://proxy-a:8080")

        downloader._restart_browser = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._restart_browser.assert_not_called()

    @pytest.mark.asyncio
    async def test_proxy_downgraded_to_direct(self, downloader):
        """proxy_downgraded 标记触发降级为直连"""
        downloader._current_proxy = "http://proxy-a:8080"
        request = make_mock_request(proxy=None, proxy_downgraded=True)

        downloader._restart_browser = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._restart_browser.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_proxy_downgrade_no_op_when_already_direct(self, downloader):
        """已为直连时，proxy_downgraded 不触发重启"""
        downloader._current_proxy = None
        request = make_mock_request(proxy=None, proxy_downgraded=True)

        downloader._restart_browser = AsyncMock()
        await downloader._check_proxy_change(request)
        downloader._restart_browser.assert_not_called()

    # ---- _restart_browser 测试 ----

    @pytest.mark.asyncio
    async def test_restart_browser_closes_and_reinitializes(self, downloader):
        """重启浏览器：先关闭旧实例，再用新代理初始化"""
        downloader.close = AsyncMock()
        downloader._initialize_browser = AsyncMock()

        await downloader._restart_browser("http://new-proxy:8080")

        downloader.close.assert_called_once()
        downloader._initialize_browser.assert_called_once_with(proxy="http://new-proxy:8080")

    @pytest.mark.asyncio
    async def test_restart_browser_with_none_proxy(self, downloader):
        """重启浏览器为直连模式（proxy=None）"""
        downloader.close = AsyncMock()
        downloader._initialize_browser = AsyncMock()

        await downloader._restart_browser(None)

        downloader._initialize_browser.assert_called_once_with(proxy=None)

    # ---- _initialize_browser 测试 ----

    @pytest.mark.asyncio
    async def test_initialize_browser_sets_current_proxy(self, downloader):
        """初始化浏览器时设置 _current_proxy"""
        # Camoufox 是在 _initialize_browser 内部 from camoufox import 的
        # 需要在 sys.modules 中预先放入 mock 模块
        mock_camoufox_instance = MagicMock()
        mock_camoufox_module = MagicMock()
        mock_camoufox_module.Camoufox = MagicMock(return_value=mock_camoufox_instance)

        with patch.dict('sys.modules', {'camoufox': mock_camoufox_module}):
            downloader.proxy = "http://static-proxy:8080"
            downloader._current_proxy = None

            await downloader._initialize_browser()

            # 验证 _current_proxy 被设置为传入的代理
            assert downloader._current_proxy == "http://static-proxy:8080"

    @pytest.mark.asyncio
    async def test_initialize_browser_with_explicit_proxy(self, downloader):
        """初始化浏览器时使用显式代理参数"""
        mock_camoufox_instance = MagicMock()
        mock_camoufox_module = MagicMock()
        mock_camoufox_module.Camoufox = MagicMock(return_value=mock_camoufox_instance)

        with patch.dict('sys.modules', {'camoufox': mock_camoufox_module}):
            await downloader._initialize_browser(proxy="http://explicit-proxy:9090")

            assert downloader._current_proxy == "http://explicit-proxy:9090"

    @pytest.mark.asyncio
    async def test_initialize_browser_without_proxy(self, downloader):
        """初始化浏览器时无代理（直连）"""
        mock_camoufox_instance = MagicMock()
        mock_camoufox_module = MagicMock()
        mock_camoufox_module.Camoufox = MagicMock(return_value=mock_camoufox_instance)

        with patch.dict('sys.modules', {'camoufox': mock_camoufox_module}):
            downloader.proxy = None
            await downloader._initialize_browser()

            assert downloader._current_proxy is None

    # ---- close 测试 ----

    @pytest.mark.asyncio
    async def test_close_resets_proxy_state(self, downloader):
        """关闭时重置代理状态"""
        downloader._current_proxy = "http://proxy:8080"

        await downloader.close()

        assert downloader._current_proxy is None
        assert downloader._context is None


# ==============================================================================
# 跨下载器一致性测试
# ==============================================================================

class TestProxySwitchingConsistency:
    """三个浏览器下载器代理切换行为一致性测试"""

    @pytest.mark.asyncio
    async def test_all_downloaders_ignore_none_proxy_without_downgrade(self):
        """所有下载器在 request.proxy=None 且无 downgrade 时都不触发切换"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader

        request = make_mock_request(proxy=None, proxy_downgraded=False)

        # CloakBrowser
        cb_dl = CloakBrowserDownloader(make_cloakbrowser_mock_crawler())
        cb_dl._browser = AsyncMock()
        cb_dl._current_proxy = "http://existing:8080"
        cb_dl._rebuild_context = AsyncMock()
        await cb_dl._check_proxy_change(request)
        cb_dl._rebuild_context.assert_not_called()

        # Playwright
        pw_dl = PlaywrightDownloader(make_playwright_mock_crawler())
        pw_dl.browser = AsyncMock()
        pw_dl._current_proxy = "http://existing:8080"
        pw_dl._rebuild_context = AsyncMock()
        await pw_dl._check_proxy_change(request)
        pw_dl._rebuild_context.assert_not_called()

        # Camoufox
        cf_dl = CamoufoxDownloader(make_camoufox_mock_crawler())
        cf_dl._current_proxy = "http://existing:8080"
        cf_dl._restart_browser = AsyncMock()
        await cf_dl._check_proxy_change(request)
        cf_dl._restart_browser.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_downloaders_handle_proxy_downgrade(self):
        """所有下载器都能处理 proxy_downgraded 标记"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader

        request = make_mock_request(proxy=None, proxy_downgraded=True)

        # CloakBrowser
        cb_dl = CloakBrowserDownloader(make_cloakbrowser_mock_crawler())
        cb_dl._browser = AsyncMock()
        cb_dl._current_proxy = "http://existing:8080"
        cb_dl._rebuild_context = AsyncMock()
        await cb_dl._check_proxy_change(request)
        cb_dl._rebuild_context.assert_called_once_with(None)

        # Playwright
        pw_dl = PlaywrightDownloader(make_playwright_mock_crawler())
        pw_dl.browser = AsyncMock()
        pw_dl._current_proxy = "http://existing:8080"
        pw_dl._rebuild_context = AsyncMock()
        await pw_dl._check_proxy_change(request)
        pw_dl._rebuild_context.assert_called_once_with(None)

        # Camoufox
        cf_dl = CamoufoxDownloader(make_camoufox_mock_crawler())
        cf_dl._current_proxy = "http://existing:8080"
        cf_dl._restart_browser = AsyncMock()
        await cf_dl._check_proxy_change(request)
        cf_dl._restart_browser.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_all_downloaders_detect_proxy_change(self):
        """所有下载器都能检测代理变化"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader

        request = make_mock_request(proxy="http://new-proxy:9090")

        # CloakBrowser
        cb_dl = CloakBrowserDownloader(make_cloakbrowser_mock_crawler())
        cb_dl._browser = AsyncMock()
        cb_dl._current_proxy = "http://old-proxy:8080"
        cb_dl._rebuild_context = AsyncMock()
        await cb_dl._check_proxy_change(request)
        cb_dl._rebuild_context.assert_called_once_with("http://new-proxy:9090")

        # Playwright
        pw_dl = PlaywrightDownloader(make_playwright_mock_crawler())
        pw_dl.browser = AsyncMock()
        pw_dl._current_proxy = "http://old-proxy:8080"
        pw_dl._rebuild_context = AsyncMock()
        await pw_dl._check_proxy_change(request)
        pw_dl._rebuild_context.assert_called_once_with("http://new-proxy:9090")

        # Camoufox
        cf_dl = CamoufoxDownloader(make_camoufox_mock_crawler())
        cf_dl._current_proxy = "http://old-proxy:8080"
        cf_dl._restart_browser = AsyncMock()
        await cf_dl._check_proxy_change(request)
        cf_dl._restart_browser.assert_called_once_with("http://new-proxy:9090")

    @pytest.mark.asyncio
    async def test_all_downloaders_ignore_same_proxy(self):
        """所有下载器在代理相同时都不触发切换"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader

        same_proxy = "http://same-proxy:8080"
        request = make_mock_request(proxy=same_proxy)

        # CloakBrowser
        cb_dl = CloakBrowserDownloader(make_cloakbrowser_mock_crawler())
        cb_dl._browser = AsyncMock()
        cb_dl._current_proxy = same_proxy
        cb_dl._rebuild_context = AsyncMock()
        await cb_dl._check_proxy_change(request)
        cb_dl._rebuild_context.assert_not_called()

        # Playwright
        pw_dl = PlaywrightDownloader(make_playwright_mock_crawler())
        pw_dl.browser = AsyncMock()
        pw_dl._current_proxy = same_proxy
        pw_dl._rebuild_context = AsyncMock()
        await pw_dl._check_proxy_change(request)
        pw_dl._rebuild_context.assert_not_called()

        # Camoufox
        cf_dl = CamoufoxDownloader(make_camoufox_mock_crawler())
        cf_dl._current_proxy = same_proxy
        cf_dl._restart_browser = AsyncMock()
        await cf_dl._check_proxy_change(request)
        cf_dl._restart_browser.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
