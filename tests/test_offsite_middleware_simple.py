#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware 简单测试文件
用于测试站点过滤中间件的功能，特别是多个域名的情况
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.offsite import OffsiteMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.exceptions import IgnoreRequestError


class MockStats:
    """Mock Stats 类，用于测试统计信息"""
    def __init__(self):
        self.stats = {}

    def inc_value(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value
        else:
            self.stats[key] = value


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


class TestOffsiteMiddleware(unittest.TestCase):
    """OffsiteMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        self.stats = MockStats()
        self.logger = MockLogger('OffsiteMiddleware')

    def test_multiple_domains_initialization(self):
        """测试多个域名的初始化"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            # 直接创建实例，传入多个域名
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ee.ofweek.com', 'www.baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 检查域名是否正确设置
            self.assertEqual(len(middleware.allowed_domains), 2)
            self.assertIn('ee.ofweek.com', middleware.allowed_domains)
            self.assertIn('www.baidu.com', middleware.allowed_domains)
            
            # 检查是否创建了正确的正则表达式
            self.assertEqual(len(middleware._domain_regexes), 2)

    def test_allowed_requests_with_multiple_domains(self):
        """测试多个域名下允许的请求"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ee.ofweek.com', 'www.baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 创建允许的请求
            request1 = Mock()
            request1.url = 'https://ee.ofweek.com/news/article1.html'
            
            request2 = Mock()
            request2.url = 'https://www.baidu.com/s?wd=test'
            
            # 这些请求应该不被认为是站外请求
            self.assertFalse(middleware._is_offsite_request(request1))
            self.assertFalse(middleware._is_offsite_request(request2))

    def test_disallowed_requests_with_multiple_domains(self):
        """测试多个域名下不允许的请求"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ee.ofweek.com', 'www.baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 创建不允许的请求
            request1 = Mock()
            request1.url = 'https://www.google.com/search?q=test'
            
            request2 = Mock()
            request2.url = 'https://github.com/user/repo'
            
            # 这些请求应该被认为是站外请求
            self.assertTrue(middleware._is_offsite_request(request1))
            self.assertTrue(middleware._is_offsite_request(request2))

    def test_subdomain_requests_with_multiple_domains(self):
        """测试多个域名下的子域名请求"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            # 使用根域名，应该允许子域名
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ofweek.com', 'baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 创建子域名的请求
            request1 = Mock()
            request1.url = 'https://news.ofweek.com/article1.html'
            
            request2 = Mock()
            request2.url = 'https://map.baidu.com/location'
            
            # 这些请求应该不被认为是站外请求（因为允许了根域名）
            self.assertFalse(middleware._is_offsite_request(request1))
            self.assertFalse(middleware._is_offsite_request(request2))

    def test_process_allowed_request_with_multiple_domains(self):
        """测试处理多个域名下允许的请求"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ee.ofweek.com', 'www.baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 创建允许的请求
            request = Mock()
            request.url = 'https://ee.ofweek.com/news/article1.html'
            spider = Mock()
            
            # 处理请求，应该不抛出异常
            # 使用asyncio.run来运行异步方法
            result = asyncio.run(middleware.process_request(request, spider))
            self.assertIsNone(result)  # 应该返回None，表示请求被允许
            
            # 检查没有增加统计计数
            self.assertNotIn('offsite_request_count', self.stats.stats)

    def test_process_disallowed_request_with_multiple_domains(self):
        """测试处理多个域名下不允许的请求"""
        with patch('crawlo.middleware.offsite.get_logger', return_value=self.logger):
            middleware = OffsiteMiddleware(
                stats=self.stats,
                log_level='DEBUG',
                allowed_domains=['ee.ofweek.com', 'www.baidu.com']
            )
            
            # 手动调用编译域名方法
            middleware._compile_domains()
            
            # 创建不允许的请求
            request = Mock()
            request.url = 'https://www.google.com/search?q=test'
            spider = Mock()
            
            # 处理请求，应该抛出IgnoreRequestError异常
            # 使用asyncio.run来运行异步方法
            with self.assertRaises(IgnoreRequestError) as context:
                asyncio.run(middleware.process_request(request, spider))
            
            self.assertIn("站外请求被过滤", str(context.exception))
            
            # 检查增加了统计计数
            self.assertIn('offsite_request_count', self.stats.stats)
            self.assertEqual(self.stats.stats['offsite_request_count'], 1)
            self.assertIn('offsite_request_count/www.google.com', self.stats.stats)


if __name__ == '__main__':
    unittest.main()