#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Shell 模块修复

验证 P1 和 P2 问题是否已正确修复。
"""
import pytest
import asyncio
import threading
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestRunAsyncFix:
    """测试 _run_async 事件循环处理修复"""
    
    def test_run_async_without_event_loop(self):
        """测试无事件循环时正常运行"""
        from crawlo.shell.core import CrawloShell
        
        shell = CrawloShell()
        
        async def sample_coro():
            return "success"
        
        result = shell._run_async(sample_coro())
        assert result == "success"
    
    def test_run_async_with_event_loop(self):
        """测试有事件循环时在新线程中运行"""
        from crawlo.shell.core import CrawloShell
        
        shell = CrawloShell()
        
        async def sample_coro():
            # 验证在新的事件循环中运行
            loop = asyncio.get_running_loop()
            return loop
        
        # 在事件循环中运行
        async def test_in_loop():
            result = shell._run_async(sample_coro())
            return result
        
        # 创建事件循环并测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_in_loop())
            # 验证返回的是一个新的事件循环（不是当前的）
            assert isinstance(result, asyncio.AbstractEventLoop)
            assert result is not loop
        finally:
            loop.close()
    
    def test_run_async_propagates_exception(self):
        """测试异常正确传播"""
        from crawlo.shell.core import CrawloShell
        
        shell = CrawloShell()
        
        async def failing_coro():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            shell._run_async(failing_coro())


class TestSimpleFetcherHTTPMethods:
    """测试 _SimpleFetcher 支持完整 HTTP 方法"""
    
    @pytest.mark.asyncio
    async def test_simple_fetcher_get_method(self):
        """测试 GET 方法"""
        from crawlo.shell.core import _SimpleFetcher
        from crawlo.network.request import Request
        
        fetcher = _SimpleFetcher()
        request = Request(url="https://httpbin.org/get", method="GET")
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'application/json'}
            mock_response.read = AsyncMock(return_value=b'{}')
            
            mock_request_context = AsyncMock()
            mock_request_context.__aenter__.return_value = mock_response
            mock_session.request.return_value = mock_request_context
            
            result = await fetcher.fetch(request)
            
            # 验证使用了 request 方法而非 get
            mock_session.request.assert_called_once()
            call_args = mock_session.request.call_args
            assert call_args[0][0] == 'GET'
    
    @pytest.mark.asyncio
    async def test_simple_fetcher_post_method(self):
        """测试 POST 方法"""
        from crawlo.shell.core import _SimpleFetcher
        from crawlo.network.request import Request
        
        fetcher = _SimpleFetcher()
        request = Request(
            url="https://httpbin.org/post",
            method="POST",
            headers={'Content-Type': 'application/json'},
            body=b'{"key": "value"}'
        )
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = AsyncMock(return_value=b'{}')
            
            mock_request_context = AsyncMock()
            mock_request_context.__aenter__.return_value = mock_response
            mock_session.request.return_value = mock_request_context
            
            result = await fetcher.fetch(request)
            
            # 验证使用了 POST 方法和 body
            call_args = mock_session.request.call_args
            assert call_args[0][0] == 'POST'
            assert call_args[1]['data'] == b'{"key": "value"}'
    
    @pytest.mark.asyncio
    async def test_simple_fetcher_with_headers(self):
        """测试传递 headers"""
        from crawlo.shell.core import _SimpleFetcher
        from crawlo.network.request import Request
        
        fetcher = _SimpleFetcher()
        request = Request(
            url="https://httpbin.org/headers",
            headers={'Authorization': 'Bearer token', 'X-Custom': 'value'}
        )
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read = AsyncMock(return_value=b'{}')
            
            mock_request_context = AsyncMock()
            mock_request_context.__aenter__.return_value = mock_response
            mock_session.request.return_value = mock_request_context
            
            await fetcher.fetch(request)
            
            # 验证 headers 被传递
            call_args = mock_session.request.call_args
            assert call_args[1]['headers'] == {'Authorization': 'Bearer token', 'X-Custom': 'value'}


class TestMockCrawlerSettings:
    """测试 _MockCrawler.settings 类型统一"""
    
    def test_mock_crawler_no_settings(self):
        """测试无 settings 时创建 SettingManager"""
        from crawlo.shell.core import _MockCrawler
        
        with patch('crawlo.settings.setting_manager.SettingManager') as mock_sm:
            mock_instance = Mock()
            mock_sm.return_value = mock_instance
            
            crawler = _MockCrawler()
            
            # 验证创建了 SettingManager
            mock_sm.assert_called_once()
            assert crawler.settings == mock_instance
    
    def test_mock_crawler_dict_settings(self):
        """测试 dict settings 合并到 SettingManager"""
        from crawlo.shell.core import _MockCrawler
        
        with patch('crawlo.settings.setting_manager.SettingManager') as mock_sm:
            mock_instance = Mock()
            mock_instance.attributes = {}
            mock_sm.return_value = mock_instance
            
            crawler = _MockCrawler(settings={'KEY1': 'value1', 'KEY2': 'value2'})
            
            # 验证合并了配置
            mock_sm.assert_called_once()
            assert mock_instance.attributes['KEY1'] == 'value1'
            assert mock_instance.attributes['KEY2'] == 'value2'
    
    def test_mock_crawler_object_settings(self):
        """测试已有配置对象直接使用"""
        from crawlo.shell.core import _MockCrawler
        
        custom_settings = Mock()
        crawler = _MockCrawler(settings=custom_settings)
        
        # 验证直接使用配置对象
        assert crawler.settings == custom_settings
    
    def test_mock_crawler_setting_manager_failure(self):
        """测试 SettingManager 创建失败时回退到 dict"""
        from crawlo.shell.core import _MockCrawler
        
        with patch('crawlo.settings.setting_manager.SettingManager', side_effect=ImportError):
            crawler = _MockCrawler()
            
            # 验证回退到空 dict
            assert crawler.settings == {}


class TestExceptionHandling:
    """测试异常处理改进"""
    
    def test_cleanup_temp_files_os_error(self):
        """测试临时文件清理捕获 OSError"""
        from crawlo.shell.core import CrawloShell
        import os
        
        shell = CrawloShell()
        shell._temp_files = ['/nonexistent/file.txt']
        
        # 不应抛出异常
        shell._cleanup_temp_files()
        assert shell._temp_files == []
    
    @pytest.mark.asyncio
    async def test_downloader_adapter_close_logs_error(self):
        """测试下载器关闭时记录错误"""
        from crawlo.shell.core import _DownloaderAdapter
        
        mock_downloader = Mock()
        mock_downloader.close = MagicMock(side_effect=RuntimeError("Close error"))
        
        adapter = _DownloaderAdapter(mock_downloader)
        adapter._session_initialized = True
        
        # 不应抛出异常
        await adapter.close()
        
        # 验证调用了 close
        mock_downloader.close.assert_called_once()


class TestCurlParserValidation:
    """测试 CurlParser 导入验证"""
    
    @pytest.mark.asyncio
    async def test_from_curl_import_error(self):
        """测试 CurlParser 导入失败"""
        from crawlo.shell.core import CrawloShell
        
        shell = CrawloShell()
        
        # 模拟 ImportError
        with patch('builtins.__import__', side_effect=ImportError):
            result = await shell.from_curl('curl https://example.com')
            
            # 验证返回 None
            assert result is None


class TestDownloaderAdapterSettings:
    """测试 _DownloaderAdapter 从 settings 读取配置"""
    
    @pytest.mark.asyncio
    async def test_ensure_session_uses_settings(self):
        """测试 session 配置从 settings 读取"""
        from crawlo.shell.core import _DownloaderAdapter
        
        # 创建自定义 settings
        custom_settings = Mock()
        custom_settings.CONCURRENT_REQUESTS = 20
        custom_settings.DOWNLOAD_TIMEOUT = 60
        custom_settings.DOWNLOAD_MAXSIZE = 20 * 1024 * 1024
        
        mock_downloader = Mock()
        mock_downloader.session = None
        mock_downloader.max_download_size = 0
        
        adapter = _DownloaderAdapter(mock_downloader, settings=custom_settings)
        
        with patch('aiohttp.ClientSession') as mock_session:
            await adapter._ensure_session()
            
            # 验证使用了自定义配置
            call_kwargs = mock_session.call_args[1]
            assert call_kwargs['connector'].limit == 20
            assert call_kwargs['timeout'].total == 60
            assert mock_downloader.max_download_size == 20 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_ensure_session_default_values(self):
        """测试使用默认配置值"""
        from crawlo.shell.core import _DownloaderAdapter
        
        mock_downloader = Mock()
        mock_downloader.session = None
        mock_downloader.max_download_size = 0
        
        adapter = _DownloaderAdapter(mock_downloader, settings={})
        
        with patch('aiohttp.ClientSession') as mock_session:
            await adapter._ensure_session()
            
            # 验证使用默认值
            call_kwargs = mock_session.call_args[1]
            assert call_kwargs['connector'].limit == 10
            assert call_kwargs['timeout'].total == 30
            assert mock_downloader.max_download_size == 10 * 1024 * 1024


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
