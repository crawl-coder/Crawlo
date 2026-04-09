#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 HybridDownloader 的延迟加载和动态导入优化
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch


class TestHybridDownloaderLazyLoading:
    """测试 HybridDownloader 的延迟加载优化"""

    def test_downloader_class_mapping(self):
        """测试下载器类映射是否正确"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 测试各种下载器类型映射
        test_cases = [
            ("aiohttp", "AioHttpDownloader"),
            ("httpx", "HttpXDownloader"),
            ("curl_cffi", "CurlCffiDownloader"),
            ("playwright", "PlaywrightDownloader"),
            ("camoufox", "CamoufoxDownloader"),
            ("drissionpage", "DrissionPageDownloader"),
        ]
        
        for downloader_type, expected_class in test_cases:
            try:
                cls = hybrid._get_downloader_class(downloader_type)
                if cls is not None:
                    assert cls.__name__ == expected_class, \
                        f"Expected {expected_class}, got {cls.__name__}"
                    print(f"✓ {downloader_type} -> {cls.__name__}")
            except ImportError:
                # 某些依赖未安装是正常的
                print(f"⊘ {downloader_type} skipped (dependency not installed)")

    def test_unknown_downloader_type(self):
        """测试未知下载器类型"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        result = hybrid._get_downloader_class("unknown_type")
        assert result is None

    def test_no_static_imports(self):
        """验证没有静态导入下载器（应该使用延迟加载）"""
        import inspect
        from crawlo.downloader import hybrid_downloader
        
        source = inspect.getsource(hybrid_downloader)
        
        # 不应该有静态导入语句
        assert "from .aiohttp_downloader import" not in source
        assert "from .httpx_downloader import" not in source
        assert "from .playwright_downloader import" not in source
        
        # 应该有 importlib 导入
        assert "import importlib" in source
        assert "import_module" in source

    def test_regex_url_patterns(self):
        """测试正则表达式 URL 模式匹配"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        import re
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.side_effect = lambda key, default: [
            r".*\.js$",  # 匹配 JS 文件
            r".*api/v\d+",  # 匹配 API 路径
        ] if key == "HYBRID_PROTOCOL_URL_PATTERNS" else []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 验证正则表达式已编译
        assert len(hybrid.protocol_url_patterns) == 2
        assert isinstance(hybrid.protocol_url_patterns[0], re.Pattern)

    @pytest.mark.asyncio
    async def test_lazy_dynamic_downloader_init(self):
        """测试动态下载器是否懒加载"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 不初始化下载器，直接验证 _downloaders 为空
        assert len(hybrid._downloaders) == 0, "Downloaders should be empty before initialization"

    @pytest.mark.asyncio
    async def test_dynamic_downloader_created_on_demand(self):
        """测试动态下载器按需创建"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.network.request import Request
        
        # 创建 mock crawler
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 模拟需要动态下载器的请求
        request = Request(
            url="https://example.com/dynamic-page",
            meta={"use_dynamic_loader": True}
        )
        
        # 此时 dynamic 下载器应该被创建
        downloader_type = hybrid._determine_downloader_type(request)
        assert downloader_type == "dynamic"

    def test_downloader_class_cache(self):
        """测试下载器类导入缓存"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 多次获取同一个下载器类
        cls1 = hybrid._get_downloader_class("aiohttp")
        cls2 = hybrid._get_downloader_class("aiohttp")
        
        # 应该是同一个类（虽然每次都动态导入，但 Python 会缓存模块）
        if cls1 is not None and cls2 is not None:
            assert cls1 is cls2


class TestHybridDownloaderClose:
    """测试 HybridDownloader 的 close 方法简化"""

    @pytest.mark.asyncio
    async def test_close_all_downloaders(self):
        """测试关闭所有下载器"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from unittest.mock import AsyncMock
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # Mock close 方法
        mock_downloader = Mock()
        mock_downloader.close = AsyncMock()
        hybrid._downloaders["test"] = mock_downloader
        
        # 关闭
        await hybrid.close()
        
        # 验证 close 被调用
        mock_downloader.close.assert_called_once()
        
        # 验证缓存被清空
        assert len(hybrid._downloaders) == 0

    @pytest.mark.asyncio
    async def test_close_error_handling(self):
        """测试 close 时的错误处理"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from unittest.mock import AsyncMock
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 创建一个会抛出异常的下载器
        mock_downloader = Mock()
        mock_downloader.close = AsyncMock(side_effect=Exception("Close error"))
        hybrid._downloaders["error_downloader"] = mock_downloader
        
        # 关闭时不应该抛出异常
        await hybrid.close()
        
        # 验证异常被捕获并记录
        mock_downloader.close.assert_called_once()


class TestHybridDownloaderDetermineType:
    """测试下载器类型判断逻辑"""

    def test_request_meta_priority(self):
        """测试请求标记最高优先级"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.network.request import Request
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 测试 use_dynamic_loader
        request = Request(url="https://example.com", meta={"use_dynamic_loader": True})
        assert hybrid._determine_downloader_type(request) == "dynamic"
        
        # 测试 use_protocol_loader
        request = Request(url="https://example.com", meta={"use_protocol_loader": True})
        assert hybrid._determine_downloader_type(request) == "protocol"

    def test_url_pattern_matching(self):
        """测试 URL 模式匹配"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.network.request import Request
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.side_effect = lambda key, default: (
            [r".*dynamic.*"] if key == "HYBRID_DYNAMIC_URL_PATTERNS" else []
        )
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 匹配动态模式
        request = Request(url="https://example.com/dynamic-page")
        assert hybrid._determine_downloader_type(request) == "dynamic"
        
        # 不匹配任何模式，使用默认
        request = Request(url="https://example.com/static-page")
        assert hybrid._determine_downloader_type(request) == "protocol"

    def test_static_file_extensions(self):
        """测试静态文件扩展名判断"""
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.network.request import Request
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = "aiohttp"
        mock_crawler.settings.get_list.return_value = []
        mock_crawler.settings.get_bool.return_value = False
        
        hybrid = HybridDownloader(mock_crawler)
        
        # 静态文件应该使用协议下载器
        static_files = [
            "https://example.com/script.js",
            "https://example.com/style.css",
            "https://example.com/image.jpg",
            "https://example.com/document.pdf",
        ]
        
        for url in static_files:
            request = Request(url=url)
            assert hybrid._determine_downloader_type(request) == "protocol", \
                f"Static file {url} should use protocol downloader"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
