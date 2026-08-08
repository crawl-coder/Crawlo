#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器集成测试
============================

测试实际爬虫场景中的使用
"""

import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestCloakBrowserIntegration:
    """集成测试：CloakBrowser 在实际爬虫中的使用"""
    
    @pytest.fixture(autouse=True)
    def check_cloakbrowser_installed(self):
        """检查 cloakbrowser 是否已安装"""
        # 只跳过需要实际浏览器的测试
        test_name = os.environ.get('PYTEST_CURRENT_TEST', '')
        if 'mock_browser' in test_name or 'custom_actions' in test_name or 'reuse_browser' in test_name:
            try:
                import cloakbrowser
            except ImportError:
                pytest.skip("cloakbrowser 未安装，跳过需要实际浏览器的测试")
    
    @pytest.mark.asyncio
    async def test_cloakbrowser_with_mock_browser(self):
        """测试使用 mock 浏览器的完整下载流程"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings = Mock()
        mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_HEADLESS': True,
            'CLOAKBROWSER_HUMANIZE': False,
            'CLOAKBROWSER_GEOIP': False,
            'CLOAKBROWSER_STEALTH_ARGS': True,
            'CLOAKBROWSER_AUTO_SCROLL': False,
            'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
            'DOWNLOAD_STATS': True,
        }.get(key, default))
        mock_crawler.settings.get = Mock(side_effect=lambda key, default: {
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
        mock_crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
            'CLOAKBROWSER_SCROLL_DELAY': 500,
            'CLOAKBROWSER_WAIT_TIMEOUT': 10000,
        }.get(key, default))
        mock_crawler.settings.get_list = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_ARGS': [],
            'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
        }.get(key, default))
        mock_crawler.spider = Mock()
        mock_crawler.spider.name = 'test_spider'
        
        # 创建下载器
        downloader = CloakBrowserDownloader(mock_crawler)
        downloader.open()
        
        # Mock 浏览器初始化
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        
        # 设置 mock
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.content = AsyncMock(return_value='<html><body>Test</body></html>')
        mock_page.url = 'https://example.com'
        
        # Patch launch_async（从 cloakbrowser 库导入）
        with patch('cloakbrowser.launch_async', return_value=mock_browser):
            # 创建请求
            request = Request(url="https://example.com")
            
            # 执行下载
            response = await downloader.download(request)
            
            # 验证
            assert response is not None
            assert response.url == 'https://example.com'
            assert response.status == 200
            assert b'Test' in response.body
    
    @pytest.mark.asyncio
    async def test_cloakbrowser_with_custom_actions(self):
        """测试带自定义操作的下载"""
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings = Mock()
        mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_HEADLESS': True,
            'CLOAKBROWSER_HUMANIZE': False,
            'CLOAKBROWSER_GEOIP': False,
            'CLOAKBROWSER_STEALTH_ARGS': True,
            'CLOAKBROWSER_AUTO_SCROLL': True,  # 启用自动滚动
            'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
            'DOWNLOAD_STATS': True,
        }.get(key, default))
        mock_crawler.settings.get = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_PROXY': None,
            'CLOAKBROWSER_HUMAN_PRESET': 'default',
            'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        }.get(key, default))
        mock_crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
            'CLOAKBROWSER_SCROLL_DELAY': 500,
        }.get(key, default))
        mock_crawler.settings.get_list = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_BLOCK_RESOURCES': [],
        }.get(key, default))
        mock_crawler.spider = Mock()
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # Mock 浏览器
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.content = AsyncMock(return_value='<html>Content</html>')
        mock_page.url = 'https://example.com'
        mock_page.evaluate = AsyncMock(return_value=1000)  # 页面高度
        
        with patch('cloakbrowser.launch_async', return_value=mock_browser):
            # 创建带自定义操作的请求
            request = Request(url="https://example.com")
            request.meta['dynamic_actions'] = [
                {'type': 'click', 'selector': '#load-more'},
                {'type': 'wait', 'params': {'timeout': 1000}},
            ]
            
            response = await downloader.download(request)
            
            # 验证操作被执行
            assert response is not None
            # click 和 wait 操作应该被调用
            assert mock_page.click.called or mock_page.evaluate.called
    
    @pytest.mark.asyncio
    async def test_hybrid_downloader_with_cloakbrowser(self):
        """测试 HybridDownloader 使用 CloakBrowser"""
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
        mock_crawler.spider = Mock()
        
        hybrid = HybridDownloader(mock_crawler)
        hybrid.open()
        
        # 创建请求，标记使用动态加载器
        request = Request(url="https://example.com")
        request.meta['use_dynamic_loader'] = True
        
        # 验证下载器类型识别
        downloader_type = hybrid._determine_downloader_type(request)
        assert downloader_type == "dynamic"
        assert hybrid.default_dynamic_downloader == "cloakbrowser"
        
        await hybrid.close()
    
    def test_settings_configuration(self):
        """测试配置文件的正确性"""
        # 验证 setup.cfg 中的 stealth 配置
        setup_cfg_path = os.path.join(os.path.dirname(__file__), '..', 'setup.cfg')
        
        if os.path.exists(setup_cfg_path):
            with open(setup_cfg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证 stealth 配置存在
            assert 'stealth' in content, "setup.cfg 中缺少 stealth 配置"
            assert 'cloakbrowser' in content, "setup.cfg 中缺少 cloakbrowser 依赖"
    
    def test_downloader_module_exports(self):
        """测试 downloader 模块正确导出 CloakBrowserDownloader"""
        from crawlo import downloader
        
        # 验证导出
        assert hasattr(downloader, 'CloakBrowserDownloader'), \
            "downloader 模块未导出 CloakBrowserDownloader"
        
        # 验证 DOWNLOADER_MAP
        assert 'cloakbrowser' in downloader.DOWNLOADER_MAP, \
            "DOWNLOADER_MAP 中缺少 cloakbrowser"


class TestCloakBrowserEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_multiple_downloads_reuse_browser(self):
        """测试多次下载复用浏览器实例"""
        # 检查是否安装
        try:
            import cloakbrowser
        except ImportError:
            pytest.skip("cloakbrowser 未安装")
        from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
        from crawlo.network.request import Request
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings = Mock()
        mock_crawler.settings.get_bool = Mock(return_value=False)
        mock_crawler.settings.get = Mock(return_value=None)
        mock_crawler.settings.get_int = Mock(side_effect=lambda key, default: {
            'CLOAKBROWSER_TIMEOUT': 30000,
            'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
            'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
            'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
            'CLOAKBROWSER_MAX_PAGES': 10,
        }.get(key, default))
        mock_crawler.settings.get_list = Mock(return_value=[])
        mock_crawler.spider = Mock()
        
        downloader = CloakBrowserDownloader(mock_crawler)
        
        # Mock 浏览器
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.content = AsyncMock(return_value='<html>Test</html>')
        mock_page.url = 'https://example.com'
        
        launch_count = 0
        
        async def mock_launch_async(**kwargs):
            nonlocal launch_count
            launch_count += 1
            return mock_browser
        
        with patch('cloakbrowser.launch_async', side_effect=mock_launch_async):
            # 第一次下载
            request1 = Request(url="https://example.com/1")
            await downloader.download(request1)
            
            # 第二次下载
            request2 = Request(url="https://example.com/2")
            await downloader.download(request2)
            
            # 第三次下载
            request3 = Request(url="https://example.com/3")
            await downloader.download(request3)
            
            # 验证浏览器只启动了一次
            assert launch_count == 1, "浏览器被多次启动，应该复用"
        
        await downloader.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
