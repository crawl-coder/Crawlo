#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware 测试文件
用于测试站外请求过滤中间件的功能
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.offsite import OffsiteMiddleware
from crawlo.exceptions import NotConfiguredError, IgnoreRequestError
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


class MockStats:
    """Mock Stats 类，用于测试统计信息"""
    def __init__(self):
        self.stats = {}

    def inc_value(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value
        else:
            self.stats[key] = value


class TestOffsiteMiddleware(unittest.TestCase):
    """OffsiteMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings
        self.crawler.stats = MockStats()
        self.crawler.logger = Mock()

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_without_allowed_domains(self, mock_get_logger):
        """测试没有配置允许域名时中间件初始化"""
        mock_get_logger.return_value = MockLogger('OffsiteMiddleware')
        
        # 应该抛出NotConfiguredError异常
        with self.assertRaises(NotConfiguredError):
            OffsiteMiddleware.create_instance(self.crawler)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_allowed_domains(self, mock_get_logger):
        """测试配置允许域名时中间件初始化"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com', 'test.com'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('OffsiteMiddleware')
        
        # 应该正常创建实例
        middleware = OffsiteMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, OffsiteMiddleware)
        self.assertEqual(len(middleware.allowed_domains), 2)
        self.assertIn('example.com', middleware.allowed_domains)
        self.assertIn('test.com', middleware.allowed_domains)

    def test_is_offsite_request_with_valid_domain(self):
        """测试有效域名的站外请求判断"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        # 创建中间件实例
        middleware = OffsiteMiddleware(
            stats=MockStats(),
            log_level='INFO',
            allowed_domains=['example.com']
        )
        middleware._compile_domains()
        
        # 创建请求对象
        request = Mock()
        request.url = 'http://example.com/page'
        
        # 应该不是站外请求
        self.assertFalse(middleware._is_offsite_request(request))

    def test_is_offsite_request_with_subdomain(self):
        """测试子域名的站外请求判断"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        # 创建中间件实例
        middleware = OffsiteMiddleware(
            stats=MockStats(),
            log_level='INFO',
            allowed_domains=['example.com']
        )
        middleware._compile_domains()
        
        # 创建请求对象（子域名）
        request = Mock()
        request.url = 'http://sub.example.com/page'
        
        # 应该不是站外请求（子域名应该被允许）
        self.assertFalse(middleware._is_offsite_request(request))

    def test_is_offsite_request_with_invalid_domain(self):
        """测试无效域名的站外请求判断"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        # 创建中间件实例
        middleware = OffsiteMiddleware(
            stats=MockStats(),
            log_level='INFO',
            allowed_domains=['example.com']
        )
        middleware._compile_domains()
        
        # 创建请求对象
        request = Mock()
        request.url = 'http://other.com/page'
        
        # 应该是站外请求
        self.assertTrue(middleware._is_offsite_request(request))

    def test_is_offsite_request_with_invalid_url(self):
        """测试无效URL的站外请求判断"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        # 创建中间件实例
        middleware = OffsiteMiddleware(
            stats=MockStats(),
            log_level='INFO',
            allowed_domains=['example.com']
        )
        middleware._compile_domains()
        
        # 创建请求对象（无效URL）
        request = Mock()
        request.url = 'invalid-url'
        
        # 应该是站外请求
        self.assertTrue(middleware._is_offsite_request(request))

    @patch('crawlo.utils.log.get_logger')
    def test_process_request_with_offsite_request(self, mock_get_logger):
        """测试处理站外请求"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        mock_logger = MockLogger('OffsiteMiddleware')
        mock_get_logger.return_value = mock_logger
        
        # 创建中间件实例
        middleware = OffsiteMiddleware.create_instance(self.crawler)
        
        # 创建请求对象（站外请求）
        request = Mock()
        request.url = 'http://other.com/page'
        
        # 应该抛出IgnoreRequestError异常
        with self.assertRaises(IgnoreRequestError):
            asyncio.run(middleware.process_request(request, Mock()))
        
        # 验证统计信息
        self.assertIn('offsite_request_count', self.crawler.stats.stats)
        self.assertEqual(self.crawler.stats.stats['offsite_request_count'], 1)

    @patch('crawlo.utils.log.get_logger')
    def test_process_request_with_valid_request(self, mock_get_logger):
        """测试处理有效请求"""
        # 设置允许的域名
        self.settings.set('ALLOWED_DOMAINS', ['example.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        mock_logger = MockLogger('OffsiteMiddleware')
        mock_get_logger.return_value = mock_logger
        
        # 创建中间件实例
        middleware = OffsiteMiddleware.create_instance(self.crawler)
        
        # 创建请求对象（有效请求）
        request = Mock()
        request.url = 'http://example.com/page'
        
        # 应该正常处理，不抛出异常
        result = asyncio.run(middleware.process_request(request, Mock()))
        
        # 返回None表示继续处理
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()