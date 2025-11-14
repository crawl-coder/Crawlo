#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
ProxyMiddleware 测试文件
用于测试代理中间件的功能
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.exceptions import NotConfiguredError
from crawlo.settings.setting_manager import SettingManager


class MockLogger:
    """Mock Logger 类，用于测试日志输出"""
    def __init__(self, name, level=None):
        self.name = name
        self.level = level
        self.logs = []

    def debug(self, msg):
        self.logs.append(('debug', msg))

    def info(self, msg):
        self.logs.append(('info', msg))

    def warning(self, msg):
        self.logs.append(('warning', msg))

    def error(self, msg):
        self.logs.append(('error', msg))


class TestProxyMiddleware(unittest.TestCase):
    """ProxyMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_without_api_url(self, mock_get_logger):
        """测试没有配置API URL时中间件初始化"""
        # 不再需要 PROXY_ENABLED，只要不配置 PROXY_API_URL 就会禁用
        self.settings.set('PROXY_API_URL', None)
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该正常创建实例，但会禁用
        middleware = ProxyMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertFalse(middleware.enabled)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_disabled_proxy(self, mock_get_logger):
        """测试禁用代理时中间件初始化"""
        # 不再需要 PROXY_ENABLED，只要不配置 PROXY_API_URL 就会禁用
        self.settings.set('PROXY_API_URL', None)
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该正常创建实例，但会禁用
        middleware = ProxyMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertFalse(middleware.enabled)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_api_url(self, mock_get_logger):
        """测试配置API URL时中间件初始化"""
        # 不再需要 PROXY_ENABLED，只要配置了 PROXY_API_URL 就会启用
        self.settings.set('PROXY_API_URL', 'http://proxy-api.example.com')
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该正常创建实例并启用
        middleware = ProxyMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://proxy-api.example.com')

    def test_middleware_initialization(self):
        """测试中间件初始化"""
        # 配置代理API URL以启用中间件
        self.settings.set('PROXY_API_URL', 'http://proxy-api.example.com')
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://proxy-api.example.com')

    def test_middleware_enabled_with_api_url(self):
        """测试配置了代理API URL时中间件启用"""
        self.settings.set('PROXY_API_URL', 'http://proxy-api.example.com')
        # 不再需要显式设置 PROXY_ENABLED = True
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://proxy-api.example.com')

    def test_middleware_disabled_without_api_url(self):
        """测试未配置代理API URL时中间件禁用"""
        # 不设置 PROXY_API_URL 或设置为空
        self.settings.set('PROXY_API_URL', '')
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertFalse(middleware.enabled)
        
    def test_middleware_disabled_explicitly(self):
        """测试显式禁用中间件（通过不配置API URL）"""
        # 不配置 PROXY_API_URL
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertFalse(middleware.enabled)

    def test_is_https_with_https_url(self):
        """测试HTTPS URL判断"""
        # 创建中间件实例
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 创建请求对象
        request = Mock()
        request.url = 'https://example.com/page'
        
        # 应该返回True
        self.assertTrue(middleware._is_https(request))

    def test_is_https_with_http_url(self):
        """测试HTTP URL判断"""
        # 创建中间件实例
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 创建请求对象
        request = Mock()
        request.url = 'http://example.com/page'
        
        # 应该返回False
        self.assertFalse(middleware._is_https(request))

    def test_proxy_extractor_field(self):
        """测试字段名提取方式"""
        self.settings.set('PROXY_API_URL', 'http://test.api/proxy')
        self.settings.set('PROXY_EXTRACTOR', 'data')  # 从data字段提取
        
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertEqual(middleware.proxy_extractor, 'data')
        
        # 测试提取逻辑
        data = {'data': 'http://proxy-from-data:8080'}
        proxy = middleware._extract_proxy_from_data(data)
        self.assertEqual(proxy, 'http://proxy-from-data:8080')

    def test_proxy_extractor_dict_field(self):
        """测试字典字段提取方式"""
        self.settings.set('PROXY_API_URL', 'http://test.api/proxy')
        self.settings.set('PROXY_EXTRACTOR', {'type': 'field', 'value': 'result'})
        
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertEqual(middleware.proxy_extractor['type'], 'field')
        self.assertEqual(middleware.proxy_extractor['value'], 'result')
        
        # 测试提取逻辑
        data = {'result': 'http://proxy-from-result:8080'}
        proxy = middleware._extract_proxy_from_data(data)
        self.assertEqual(proxy, 'http://proxy-from-result:8080')

    def test_proxy_extractor_custom_function(self):
        """测试自定义函数提取方式"""
        def custom_extractor(data):
            return data.get('custom_proxy')
            
        self.settings.set('PROXY_API_URL', 'http://test.api/proxy')
        self.settings.set('PROXY_EXTRACTOR', {'type': 'custom', 'function': custom_extractor})
        
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        
        # 测试提取逻辑
        data = {'custom_proxy': 'http://proxy-from-custom:8080'}
        proxy = middleware._extract_proxy_from_data(data)
        self.assertEqual(proxy, 'http://proxy-from-custom:8080')

    def test_proxy_extractor_callable(self):
        """测试直接函数提取方式"""
        def direct_extractor(data):
            return data.get('direct_proxy')
            
        self.settings.set('PROXY_API_URL', 'http://test.api/proxy')
        self.settings.set('PROXY_EXTRACTOR', direct_extractor)
        
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        
        # 测试提取逻辑
        data = {'direct_proxy': 'http://proxy-from-direct:8080'}
        proxy = middleware._extract_proxy_from_data(data)
        self.assertEqual(proxy, 'http://proxy-from-direct:8080')

    def test_middleware_disabled_without_list(self):
        """测试未配置代理列表时代理中间件禁用"""
        # 不设置 PROXY_LIST 或设置为空列表
        self.settings.set('PROXY_LIST', [])
        from crawlo.middleware.proxy import ProxyMiddleware
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertFalse(middleware.enabled)

if __name__ == '__main__':
    unittest.main()