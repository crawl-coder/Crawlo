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
        self.settings.set('PROXY_ENABLED', True)
        self.settings.set('PROXY_API_URL', None)
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该抛出NotConfiguredError异常
        with self.assertRaises(NotConfiguredError):
            ProxyMiddleware.create_instance(self.crawler)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_disabled_proxy(self, mock_get_logger):
        """测试禁用代理时中间件初始化"""
        self.settings.set('PROXY_ENABLED', False)
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该正常创建实例
        middleware = ProxyMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertFalse(middleware.enabled)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_api_url(self, mock_get_logger):
        """测试配置API URL时中间件初始化"""
        self.settings.set('PROXY_ENABLED', True)
        self.settings.set('PROXY_API_URL', 'http://proxy-api.example.com')
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('ProxyMiddleware')
        
        # 应该正常创建实例
        middleware = ProxyMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://proxy-api.example.com')

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


if __name__ == '__main__':
    unittest.main()