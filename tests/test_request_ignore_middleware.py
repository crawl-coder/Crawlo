#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
RequestIgnoreMiddleware 测试文件
用于测试请求忽略中间件的功能
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.request_ignore import RequestIgnoreMiddleware
from crawlo.exceptions import IgnoreRequestError
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


class TestRequestIgnoreMiddleware(unittest.TestCase):
    """RequestIgnoreMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings
        self.crawler.stats = MockStats()

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization(self, mock_get_logger):
        """测试中间件初始化"""
        self.settings.set('LOG_LEVEL', 'INFO')
        mock_get_logger.return_value = MockLogger('RequestIgnoreMiddleware')
        
        # 应该正常创建实例
        middleware = RequestIgnoreMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, RequestIgnoreMiddleware)

    @patch('crawlo.utils.log.get_logger')
    def test_request_ignore_event_handling(self, mock_get_logger):
        """测试请求忽略事件处理"""
        self.settings.set('LOG_LEVEL', 'DEBUG')
        mock_logger = MockLogger('RequestIgnoreMiddleware')
        mock_get_logger.return_value = mock_logger
        
        # 创建中间件实例
        mock_stats = MockStats()
        middleware = RequestIgnoreMiddleware(
            stats=mock_stats,
            log_level='DEBUG'
        )
        
        # 创建异常和请求对象
        exc = IgnoreRequestError("test reason")
        request = Mock()
        request.url = 'http://example.com/page'
        
        # 处理忽略事件
        asyncio.run(middleware.request_ignore(exc, request, Mock()))
        
        # 验证统计信息
        self.assertIn('request_ignore_count', mock_stats.stats)
        self.assertEqual(mock_stats.stats['request_ignore_count'], 1)
        self.assertIn('request_ignore_count/reason/test reason', mock_stats.stats)

    @patch('crawlo.utils.log.get_logger')
    def test_request_ignore_event_handling_with_domain(self, mock_get_logger):
        """测试带域名的请求忽略事件处理"""
        self.settings.set('LOG_LEVEL', 'DEBUG')
        mock_logger = MockLogger('RequestIgnoreMiddleware')
        mock_get_logger.return_value = mock_logger
        
        # 创建中间件实例
        mock_stats = MockStats()
        middleware = RequestIgnoreMiddleware(
            stats=mock_stats,
            log_level='DEBUG'
        )
        
        # 创建异常和请求对象
        exc = IgnoreRequestError("test reason")
        request = Mock()
        request.url = 'http://example.com/page'
        
        # 处理忽略事件
        asyncio.run(middleware.request_ignore(exc, request, Mock()))
        
        # 验证域名统计信息
        self.assertIn('request_ignore_count/domain/example.com', mock_stats.stats)

    @patch('crawlo.utils.log.get_logger')
    def test_request_ignore_event_handling_with_invalid_url(self, mock_get_logger):
        """测试带无效URL的请求忽略事件处理"""
        self.settings.set('LOG_LEVEL', 'DEBUG')
        mock_logger = MockLogger('RequestIgnoreMiddleware')
        mock_get_logger.return_value = mock_logger
        
        # 创建中间件实例
        mock_stats = MockStats()
        middleware = RequestIgnoreMiddleware(
            stats=mock_stats,
            log_level='DEBUG'
        )
        
        # 创建异常和请求对象（没有url属性，会触发异常）
        exc = IgnoreRequestError("test reason")
        request = Mock()
        # 不设置request.url属性，这样在访问时会抛出AttributeError
        
        # 处理忽略事件
        asyncio.run(middleware.request_ignore(exc, request, Mock()))
        
        # 验证无效URL统计信息
        self.assertIn('request_ignore_count/domain/invalid_url', mock_stats.stats)

    def test_process_exception_with_ignore_request_error(self):
        """测试处理IgnoreRequestError异常"""
        # 创建中间件实例
        middleware = RequestIgnoreMiddleware(
            stats=MockStats(),
            log_level='INFO'
        )
        
        # 创建异常和请求对象
        exc = IgnoreRequestError("test reason")
        request = Mock()
        
        # 应该返回True表示异常已被处理
        result = middleware.process_exception(request, exc, Mock())
        self.assertTrue(result)

    def test_process_exception_with_other_exception(self):
        """测试处理其他异常"""
        # 创建中间件实例
        middleware = RequestIgnoreMiddleware(
            stats=MockStats(),
            log_level='INFO'
        )
        
        # 创建异常和请求对象
        exc = ValueError("test error")
        request = Mock()
        
        # 应该返回None表示异常未被处理
        result = middleware.process_exception(request, exc, Mock())
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()