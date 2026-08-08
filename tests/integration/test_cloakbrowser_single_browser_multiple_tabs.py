#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloakBrowser 单浏览器多 Tab 功能测试

核心验证点：
1. 单个浏览器实例 + 多 Tab 架构
2. 页面池的创建与复用
3. 并发控制（max_pages 信号量）
4. Tab 之间的独立性
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from crawlo import Request
from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader


class TestCloakBrowserSingleBrowserMultipleTabs:
    """测试单浏览器多 Tab 核心功能"""

    def _create_mock_crawler(self, max_pages=5):
        """创建模拟 Crawler 的辅助方法"""
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            "CLOAKBROWSER_HEADLESS": True,
            "CLOAKBROWSER_HUMANIZE": False,
            "CLOAKBROWSER_GEOIP": False,
            "CLOAKBROWSER_STEALTH_ARGS": True,
            "CLOAKBROWSER_PERSISTENT_CONTEXT": False,
            "CLOAKBROWSER_AUTO_SCROLL": False,
            "DOWNLOAD_STATS": False,
        }.get(key, default))
        crawler.settings.get = Mock(side_effect=lambda key, default: {
            "CLOAKBROWSER_PROXY": None,
            "CLOAKBROWSER_HUMAN_PRESET": "default",
            "CLOAKBROWSER_HUMAN_CONFIG": None,
            "CLOAKBROWSER_TIMEZONE": None,
            "CLOAKBROWSER_LOCALE": None,
            "CLOAKBROWSER_BACKEND": "playwright",
            "PROXY_API_URL": None,
            "CLOAKBROWSER_FINGERPRINT": None,
            "CLOAKBROWSER_FINGERPRINT_PLATFORM": None,
            "CLOAKBROWSER_WAIT_STRATEGY": "auto",
            "CLOAKBROWSER_WAIT_FOR_ELEMENT": None,
            "CLOAKBROWSER_USER_DATA_DIR": None,
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            "CLOAKBROWSER_TIMEOUT": 30000,
            "CLOAKBROWSER_LOAD_TIMEOUT": 10000,
            "CLOAKBROWSER_VIEWPORT_WIDTH": 1280,
            "CLOAKBROWSER_VIEWPORT_HEIGHT": 720,
            "CLOAKBROWSER_MAX_PAGES": max_pages,
            "CLOAKBROWSER_WAIT_TIMEOUT": 10000,
            "CLOAKBROWSER_SCROLL_DELAY": 500,
        }.get(key, default))
        crawler.settings.get_list = Mock(side_effect=lambda key, default: {
            "CLOAKBROWSER_ARGS": [],
            "CLOAKBROWSER_BLOCK_RESOURCES": ["image", "font", "media"],
        }.get(key, default))
        return crawler

    @pytest.mark.asyncio
    async def test_single_browser_instance_created(self):
        """验证只创建一个浏览器实例"""
        crawler = self._create_mock_crawler()
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            
            # 初始化
            await downloader._initialize_browser()
            
            # 验证：只调用一次 launch_async（单浏览器）
            mock_launch.assert_called_once()
            assert downloader._browser is not None
            assert downloader._context is not None
            
            await downloader.close()

    @pytest.mark.asyncio
    async def test_multiple_tabs_from_single_browser(self):
        """验证从单个浏览器创建多个 Tab"""
        crawler = self._create_mock_crawler(max_pages=3)
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            
            # 模拟创建 3 个 Tab
            mock_pages = [AsyncMock() for _ in range(3)]
            mock_context.new_page = AsyncMock(side_effect=mock_pages)
            
            await downloader._initialize_browser()
            
            # 获取 3 个页面（Tab）
            pages = []
            for _ in range(3):
                page = await downloader._get_page()
                pages.append(page)
            
            # 验证：创建了 3 个 Tab
            assert mock_context.new_page.call_count == 3
            assert len(downloader._page_pool) == 3
            assert len(downloader._used_pages) == 3
            
            await downloader.close()

    @pytest.mark.asyncio
    async def test_page_pool_reuse(self):
        """验证页面池复用机制"""
        crawler = self._create_mock_crawler()
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            
            await downloader._initialize_browser()
            
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            # 第一次获取
            page1 = await downloader._get_page()
            assert mock_context.new_page.call_count == 1
            
            # 释放页面
            await downloader._release_page(page1)
            assert len(downloader._used_pages) == 0
            
            # 第二次获取（应复用）
            page2 = await downloader._get_page()
            
            # 验证：没有创建新页面，复用了旧页面
            assert mock_context.new_page.call_count == 1
            assert page1 is page2
            
            await downloader.close()

    @pytest.mark.asyncio
    async def test_max_pages_semaphore_limit(self):
        """验证 max_pages 信号量限制"""
        crawler = self._create_mock_crawler(max_pages=2)
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            
            await downloader._initialize_browser()
            
            # 验证信号量初始值为 max_pages
            assert downloader._page_semaphore._value == 2
            
            # 获取 2 个页面
            mock_pages = [AsyncMock(), AsyncMock()]
            mock_context.new_page = AsyncMock(side_effect=mock_pages)
            
            page1 = await downloader._get_page()
            page2 = await downloader._get_page()
            
            # 信号量应该为 0
            assert downloader._page_semaphore._value == 0
            
            # 尝试获取第 3 个页面会阻塞
            async def try_get_page():
                return await downloader._get_page()
            
            # 使用超时验证会阻塞
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(try_get_page(), timeout=0.1)
            
            await downloader.close()

    @pytest.mark.asyncio
    async def test_tabs_are_independent(self):
        """验证不同 Tab 可以独立访问不同 URL"""
        crawler = self._create_mock_crawler()
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            
            await downloader._initialize_browser()
            
            # 创建 2 个独立的 Tab
            page1 = AsyncMock()
            page2 = AsyncMock()
            mock_context.new_page = AsyncMock(side_effect=[page1, page2])
            
            # 获取两个 Tab
            tab1 = await downloader._get_page()
            tab2 = await downloader._get_page()
            
            # 验证是不同的 Tab
            assert tab1 is not tab2
            
            # 访问不同的 URL
            await tab1.goto("https://site1.com", timeout=10000)
            await tab2.goto("https://site2.com", timeout=10000)
            
            # 验证各自访问了正确的 URL
            tab1.goto.assert_called_with("https://site1.com", timeout=10000)
            tab2.goto.assert_called_with("https://site2.com", timeout=10000)
            
            await downloader.close()

    @pytest.mark.asyncio
    async def test_concurrent_tab_creation(self):
        """验证并发创建多个 Tab"""
        crawler = self._create_mock_crawler(max_pages=5)
        downloader = CloakBrowserDownloader(crawler)
        
        with patch('cloakbrowser.launch_async') as mock_launch:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            
            await downloader._initialize_browser()
            
            # 并发获取 5 个 Tab
            mock_pages = [AsyncMock() for _ in range(5)]
            mock_context.new_page = AsyncMock(side_effect=mock_pages)
            
            async def get_page():
                return await downloader._get_page()
            
            # 并发执行
            tasks = [get_page() for _ in range(5)]
            pages = await asyncio.gather(*tasks)
            
            # 验证：所有 Tab 都成功创建
            assert len(pages) == 5
            assert mock_context.new_page.call_count == 5
            assert len(downloader._page_pool) == 5
            
            await downloader.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
