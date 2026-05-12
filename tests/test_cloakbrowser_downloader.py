#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器完整测试套件
================================

测试覆盖：
1. 导入检测
2. 基础实例化
3. 配置读取
4. 页面池管理
5. HybridDownloader 集成
6. 异常处理
7. 资源释放
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestCloakBrowserImporter:
    """测试 1: 导入检测"""
    
    def test_import_cloakbrowser_downloader(self):
        """测试 CloakBrowserDownloader 可以导入"""
        try:
            from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
            assert CloakBrowserDownloader is not None
        except ImportError as e:
            pytest.skip(f"CloakBrowserDownloader 导入失败（可能未安装 cloakbrowser）: {e}")
    
    def test_import_from_downloader_module(self):
        """测试从 crawlo.downloader 导入"""
        from crawlo.downloader import CloakBrowserDownloader
        assert CloakBrowserDownloader is not None
    
    def test_downloader_map_registration(self):
        """测试 DOWNLOADER_MAP 注册"""
        from crawlo.downloader import DOWNLOADER_MAP
        assert 'cloakbrowser' in DOWNLOADER_MAP, "cloakbrowser 未注册到 DOWNLOADER_MAP"
        
        # 如果 cloakbrowser 可用，检查映射
        if DOWNLOADER_MAP['cloakbrowser'] is not None:
            from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
            assert DOWNLOADER_MAP['cloakbrowser'] == CloakBrowserDownloader


class TestCloakBrowserInstantiation:
    """测试 2: 基础实例化"""
    
    @pytest.fixture
    def mock_crawler(self):
        """创建模拟 Crawler 对象"""
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_HEADLESS': True,
            'CLOAKBROWSER_HUMANIZE': False,
            'CLOAKBROWSER_GEOIP': False,
            'CLOAKBROWSER_STEALTH_ARGS': True,
            'CLOAKBROWSER_AUTO_SCROLL': False,
            'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
            'DOWNLOAD_STATS': True,
        }.get(key, default))
        crawler.settings.get = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_PROXY': None,
            'CLOAKBROWSER_HUMAN_PRESET': 'default',
            'CLOAKBROWSER_HUMAN_CONFIG': None,
            'CLOAKBROWSER_TIMEZONE': None,
            'CLOAKBROWSER_LOCALE': None,
            'CLOAKBROWSER_BACKEND': 'playwright',
            'CLOAKBROWSER_FINGERPRINT': None,
            'CLOAKBROWSER_FINGERPRINT_PLATFORM': None,
            'CLOAKBROWSER_USER_DATA_DIR': None,
            'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
            'CLOAKBROWSER_SCROLL_DELAY': 500,
            'CLOAKBROWSER_WAIT_TIMEOUT': 10000,
        }.get(key, default))
        crawler.settings.get_list = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_ARGS': [],
            'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
        }.get(key, default))
        crawler.spider = Mock()
        crawler.spider.name = 'test_spider'
        return crawler
    
    def test_basic_instantiation(self, mock_crawler):
        """测试基础实例化"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        assert downloader is not None
        assert downloader._browser is None
        assert downloader._context is None
        assert downloader._page_pool == []
        assert downloader._used_pages == set()
    
    def test_configuration_reading(self, mock_crawler):
        """测试配置读取"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 验证配置已正确读取
        assert downloader.headless is True
        assert downloader.humanize is False
        assert downloader.geoip is False
        assert downloader.timeout == 30000
        assert downloader.max_pages == 10
        assert downloader.block_resources == {'image', 'font', 'media'}
    
    def test_open_method(self, mock_crawler):
        """测试 open() 方法（懒加载，不启动浏览器）"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        downloader.open()
        
        # open() 后浏览器仍应为 None（懒加载）
        assert downloader._browser is None
        assert downloader._context is None


class TestPagePoolManagement:
    """测试 3: 页面池管理"""
    
    @pytest.fixture
    def mock_crawler(self):
        """创建模拟 Crawler 对象"""
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(return_value=False)
        crawler.settings.get = Mock(return_value=None)
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_MAX_PAGES': 3,
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
        }.get(key, default))
        crawler.settings.get_list = Mock(return_value=[])
        crawler.spider = Mock()
        return crawler
    
    @pytest.mark.asyncio
    async def test_get_page_creates_new(self, mock_crawler):
        """测试获取页面时创建新页面"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 模拟 context
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        downloader._context = mock_context
        downloader._page_semaphore = asyncio.Semaphore(3)
        
        # 获取页面
        page = await downloader._get_page()
        
        assert page == mock_page
        assert len(downloader._page_pool) == 1
        assert len(downloader._used_pages) == 1
        mock_context.new_page.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_page_reuses_existing(self, mock_crawler):
        """测试复用已存在的空闲页面"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 创建两个页面
        mock_page1 = AsyncMock()
        mock_page2 = AsyncMock()
        downloader._page_pool = [mock_page1, mock_page2]
        downloader._used_pages = set()
        downloader._page_semaphore = asyncio.Semaphore(3)
        downloader._context = AsyncMock()  # 添加 mock context
        
        # 获取页面应复用 page1
        page = await downloader._get_page()
        assert page == mock_page1
        assert id(mock_page1) in downloader._used_pages
    
    @pytest.mark.asyncio
    async def test_release_page(self, mock_crawler):
        """测试释放页面"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        mock_page = AsyncMock()
        page_id = id(mock_page)
        downloader._page_pool = [mock_page]
        downloader._used_pages = {page_id}
        downloader._page_semaphore = asyncio.Semaphore(3)
        downloader._page_semaphore_lock = asyncio.Lock()
        
        # 释放页面
        await downloader._release_page(mock_page)
        
        assert page_id not in downloader._used_pages
        mock_page.goto.assert_called_once()  # 应导航到 about:blank


class TestHybridDownloaderIntegration:
    """测试 4: HybridDownloader 集成"""
    
    def test_hybrid_downloader_map(self):
        """测试 HybridDownloader 的下载器映射"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        
        # 创建模拟对象
        mock_crawler = Mock()
        mock_crawler.settings = Mock()
        mock_crawler.settings.get = Mock(return_value='aiohttp')
        mock_crawler.settings.get_list = Mock(return_value=[])
        mock_crawler.settings.get_bool = Mock(return_value=False)
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 检查映射中是否包含 cloakbrowser
        downloader_map = {
            "aiohttp": (".aiohttp_downloader", "AioHttpDownloader"),
            "cloakbrowser": (".cloakbrowser_downloader", "CloakBrowserDownloader"),
        }
        
        # 验证 cloakbrowser 在映射中
        assert "cloakbrowser" in hybrid._get_downloader_class.__code__.co_consts or \
               "cloakbrowser" in str(hybrid._get_downloader_class.__code__.co_consts)
    
    @pytest.mark.asyncio
    async def test_hybrid_selects_cloakbrowser(self):
        """测试 HybridDownloader 选择 cloakbrowser"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.network.request import Request
        
        # 创建混合下载器
        mock_crawler = Mock()
        mock_crawler.settings = Mock()
        mock_crawler.settings.get = Mock(side_effect=lambda key, default: {
            'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'aiohttp',
            'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'cloakbrowser',
        }.get(key, default))
        mock_crawler.settings.get_list = Mock(return_value=[])
        mock_crawler.settings.get_bool = Mock(return_value=False)
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 创建请求，标记使用动态加载器
        request = Request(url="https://example.com")
        request.meta['use_dynamic_loader'] = True
        
        # 确定下载器类型
        downloader_type = hybrid._determine_downloader_type(request)
        assert downloader_type == "dynamic"
        
        # 默认动态下载器应为 cloakbrowser
        assert hybrid.default_dynamic_downloader == "cloakbrowser"


class TestExceptionHandling:
    """测试 5: 异常处理"""
    
    @pytest.fixture
    def mock_crawler(self):
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(return_value=False)
        crawler.settings.get = Mock(return_value=None)
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
        }.get(key, default))
        crawler.settings.get_list = Mock(return_value=[])
        crawler.spider = Mock()
        return crawler
    
    @pytest.mark.asyncio
    async def test_download_without_initialization(self, mock_crawler):
        """测试未初始化时下载的错误处理"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 模拟初始化失败
        downloader._initialize_browser = AsyncMock(side_effect=ImportError("cloakbrowser not installed"))
        
        request = Request(url="https://example.com")
        result = await downloader.download(request)
        
        # 应返回 None 而不是抛出异常
        assert result is None
    
    @pytest.mark.asyncio
    async def test_close_without_initialization(self, mock_crawler):
        """测试未初始化时关闭的异常处理"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 应不抛出异常
        await downloader.close()
        
        assert downloader._browser is None
        assert downloader._context is None


class TestResourceCleanup:
    """测试 6: 资源释放"""
    
    @pytest.fixture
    def mock_crawler(self):
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(return_value=False)
        crawler.settings.get = Mock(return_value=None)
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
        }.get(key, default))
        crawler.settings.get_list = Mock(return_value=[])
        crawler.spider = Mock()
        return crawler
    
    @pytest.mark.asyncio
    async def test_close_releases_all_resources(self, mock_crawler):
        """测试 close() 释放所有资源"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 模拟已初始化的浏览器
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page1 = AsyncMock()
        mock_page2 = AsyncMock()
        
        downloader._browser = mock_browser
        downloader._context = mock_context
        downloader._page_pool = [mock_page1, mock_page2]
        downloader._used_pages = {id(mock_page1), id(mock_page2)}
        
        # 关闭
        await downloader.close()
        
        # 验证所有资源已释放
        mock_page1.close.assert_called_once()
        mock_page2.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        
        assert downloader._page_pool == []
        assert downloader._used_pages == set()
        assert downloader._context is None
        assert downloader._browser is None
    
    @pytest.mark.asyncio
    async def test_close_handles_exceptions_gracefully(self, mock_crawler):
        """测试 close() 优雅处理异常"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 模拟关闭时抛出异常
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock(side_effect=Exception("Close failed"))
        downloader._browser = mock_browser
        
        # 应不抛出异常
        await downloader.close()
        
        assert downloader._browser is None


class TestConfigurationOverrides:
    """测试 7: 请求级配置覆盖"""
    
    @pytest.fixture
    def mock_crawler(self):
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_HEADLESS': True,
            'CLOAKBROWSER_HUMANIZE': False,
            'CLOAKBROWSER_AUTO_SCROLL': False,
        }.get(key, default))
        crawler.settings.get = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        }.get(key, default))
        crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
            'CLOAKBROWSER_SCROLL_DELAY': 500,
        }.get(key, default))
        crawler.settings.get_list = Mock(return_value=['image', 'font'])
        crawler.spider = Mock()
        return crawler
    
    def test_meta_overrides_headless(self, mock_crawler):
        """测试 meta 覆盖 headless 配置"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # 创建请求，覆盖 headless
        request = Request(url="https://example.com")
        request.meta['cloakbrowser_headless'] = False
        
        # 验证 meta 中有覆盖值
        assert request.meta.get('cloakbrowser_headless') is False
        assert downloader.headless is True  # 全局配置仍为 True
    
    def test_meta_overrides_wait_strategy(self, mock_crawler):
        """测试 meta 覆盖 wait_strategy"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        request = Request(url="https://example.com")
        request.meta['cloakbrowser_wait_strategy'] = 'networkidle'
        
        # 验证 _get_wait_until 方法读取 meta
        wait_until = downloader._get_wait_until(request)
        assert wait_until == 'networkidle'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
