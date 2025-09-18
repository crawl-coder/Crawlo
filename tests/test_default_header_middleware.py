#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 测试文件
用于测试默认请求头中间件的功能
"""

import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.default_header import DefaultHeaderMiddleware
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


class TestDefaultHeaderMiddleware(unittest.TestCase):
    """DefaultHeaderMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_without_config(self, mock_get_logger):
        """测试没有配置时中间件初始化（清除默认配置）"""
        # 清除默认的请求头配置
        self.settings.set('DEFAULT_REQUEST_HEADERS', {})
        self.settings.set('USER_AGENT', None)
        self.settings.set('USER_AGENTS', [])
        self.settings.set('RANDOM_HEADERS', {})
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DefaultHeaderMiddleware')
        
        # 应该抛出NotConfiguredError异常
        with self.assertRaises(NotConfiguredError):
            DefaultHeaderMiddleware.create_instance(self.crawler)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_default_headers(self, mock_get_logger):
        """测试配置默认请求头时中间件初始化"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'User-Agent': 'Test-Agent',
            'Accept': 'text/html'
        })
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DefaultHeaderMiddleware')
        
        # 应该正常创建实例
        middleware = DefaultHeaderMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DefaultHeaderMiddleware)
        self.assertIn('User-Agent', middleware.headers)
        self.assertIn('Accept', middleware.headers)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_user_agent(self, mock_get_logger):
        """测试配置User-Agent时中间件初始化"""
        # 清除默认的请求头配置
        self.settings.set('DEFAULT_REQUEST_HEADERS', {})
        # 设置User-Agent
        self.settings.set('USER_AGENT', 'Custom-Agent')
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DefaultHeaderMiddleware')
        
        # 应该正常创建实例
        middleware = DefaultHeaderMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DefaultHeaderMiddleware)
        self.assertIn('User-Agent', middleware.headers)
        self.assertEqual(middleware.headers['User-Agent'], 'Custom-Agent')

    @patch('crawlo.utils.log.get_logger')
    def test_process_request_with_default_headers(self, mock_get_logger):
        """测试处理请求时添加默认请求头"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'User-Agent': 'Test-Agent',
            'Accept': 'text/html'
        })
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        mock_logger = MockLogger('DefaultHeaderMiddleware')
        mock_get_logger.return_value = mock_logger
        
        middleware = DefaultHeaderMiddleware.create_instance(self.crawler)
        
        # 创建请求对象
        request = Mock()
        request.headers = {}
        request.url = 'http://example.com'
        
        # 处理请求
        middleware.process_request(request, Mock())
        
        # 验证请求头被添加
        self.assertIn('User-Agent', request.headers)
        self.assertEqual(request.headers['User-Agent'], 'Test-Agent')
        self.assertIn('Accept', request.headers)
        self.assertEqual(request.headers['Accept'], 'text/html')

    @patch('crawlo.utils.log.get_logger')
    def test_process_request_without_overwriting_existing_headers(self, mock_get_logger):
        """测试处理请求时不覆盖已存在的请求头"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'User-Agent': 'Test-Agent',
            'Accept': 'text/html'
        })
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        mock_logger = MockLogger('DefaultHeaderMiddleware')
        mock_get_logger.return_value = mock_logger
        
        middleware = DefaultHeaderMiddleware.create_instance(self.crawler)
        
        # 创建请求对象，已包含User-Agent
        request = Mock()
        request.headers = {'User-Agent': 'Existing-Agent'}
        request.url = 'http://example.com'
        
        # 处理请求
        middleware.process_request(request, Mock())
        
        # 验证已存在的请求头未被覆盖
        self.assertEqual(request.headers['User-Agent'], 'Existing-Agent')
        # 验证其他请求头被添加
        self.assertIn('Accept', request.headers)
        self.assertEqual(request.headers['Accept'], 'text/html')


if __name__ == '__main__':
    unittest.main()