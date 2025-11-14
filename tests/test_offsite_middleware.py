#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware 测试文件
用于测试站点过滤中间件的功能，特别是多个域名的情况
"""

import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.offsite import OffsiteMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.exceptions import IgnoreRequestError, NotConfiguredError


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
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings
        self.crawler.stats = MockStats()

    def test_middleware_initialization_without_domains(self):
        """测试没有设置ALLOWED_DOMAINS时中间件初始化"""
        # 不设置ALLOWED_DOMAINS
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            # 应该抛出NotConfiguredError异常
            with self.assertRaises(NotConfiguredError) as context:
                OffsiteMiddleware.create_instance(self.crawler)
            
            self.assertIn("未配置ALLOWED_DOMAINS，OffsiteMiddleware已禁用", str(context.exception))

    def test_middleware_initialization_with_global_domains(self):
        """测试使用全局ALLOWED_DOMAINS设置时中间件初始化"""
        # 设置全局ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            # 应该正常创建实例
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            self.assertIsInstance(middleware, OffsiteMiddleware)
            self.assertEqual(len(middleware.allowed_domains), 2)
            self.assertIn('ee.ofweek.com', middleware.allowed_domains)
            self.assertIn('www.baidu.com', middleware.allowed_domains)

    def test_middleware_initialization_with_spider_domains(self):
        """测试使用Spider实例allowed_domains属性时中间件初始化"""
        # 设置Spider实例的allowed_domains
        spider = Mock()
        spider.allowed_domains = ['ee.ofweek.com', 'www.baidu.com']
        
        self.crawler.spider = spider
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            # 应该正常创建实例，使用Spider的allowed_domains
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            self.assertIsInstance(middleware, OffsiteMiddleware)
            self.assertEqual(len(middleware.allowed_domains), 2)
            self.assertIn('ee.ofweek.com', middleware.allowed_domains)
            self.assertIn('www.baidu.com', middleware.allowed_domains)

    def test_is_offsite_request_with_allowed_domains(self):
        """测试允许域名内的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建允许的请求
            request1 = Mock()
            request1.url = 'https://ee.ofweek.com/news/article1.html'
            
            request2 = Mock()
            request2.url = 'https://www.baidu.com/s?wd=test'
            
            # 这些请求应该不被认为是站外请求
            self.assertFalse(middleware._is_offsite_request(request1))
            self.assertFalse(middleware._is_offsite_request(request2))

    def test_is_offsite_request_with_subdomains(self):
        """测试子域名的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ofweek.com', 'baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建子域名的请求
            request1 = Mock()
            request1.url = 'https://news.ofweek.com/article1.html'
            
            request2 = Mock()
            request2.url = 'https://map.baidu.com/location'
            
            # 这些请求应该不被认为是站外请求（因为允许了根域名）
            self.assertFalse(middleware._is_offsite_request(request1))
            self.assertFalse(middleware._is_offsite_request(request2))

    def test_is_offsite_request_with_disallowed_domains(self):
        """测试不允许域名的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建不允许的请求
            request1 = Mock()
            request1.url = 'https://www.google.com/search?q=test'
            
            request2 = Mock()
            request2.url = 'https://github.com/user/repo'
            
            # 这些请求应该被认为是站外请求
            self.assertTrue(middleware._is_offsite_request(request1))
            self.assertTrue(middleware._is_offsite_request(request2))

    def test_process_request_with_allowed_domain(self):
        """测试处理允许域名内的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建允许的请求
            request = Mock()
            request.url = 'https://ee.ofweek.com/news/article1.html'
            spider = Mock()
            
            # 处理请求，应该不抛出异常
            result = middleware.process_request(request, spider)
            self.assertIsNone(result)  # 应该返回None，表示请求被允许
            
            # 检查没有增加统计计数
            self.assertNotIn('offsite_request_count', self.crawler.stats.stats)

    def test_process_request_with_disallowed_domain(self):
        """测试处理不允许域名的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建不允许的请求
            request = Mock()
            request.url = 'https://www.google.com/search?q=test'
            spider = Mock()
            
            # 处理请求，应该抛出IgnoreRequestError异常
            with self.assertRaises(IgnoreRequestError) as context:
                middleware.process_request(request, spider)
            
            self.assertIn("站外请求被过滤", str(context.exception))
            
            # 检查增加了统计计数
            self.assertIn('offsite_request_count', self.crawler.stats.stats)
            self.assertEqual(self.crawler.stats.stats['offsite_request_count'], 1)
            self.assertIn('offsite_request_count/www.google.com', self.crawler.stats.stats)

    def test_process_request_with_invalid_url(self):
        """测试处理无效URL的请求"""
        # 设置ALLOWED_DOMAINS
        self.settings.set('ALLOWED_DOMAINS', ['ee.ofweek.com', 'www.baidu.com'])
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        logger = MockLogger('OffsiteMiddleware')
        with patch('crawlo.middleware.offsite.get_logger', return_value=logger):
            middleware = OffsiteMiddleware.create_instance(self.crawler)
            
            # 创建无效URL的请求
            request = Mock()
            request.url = 'not_a_valid_url'
            spider = Mock()
            
            # 处理请求，应该抛出IgnoreRequestError异常
            with self.assertRaises(IgnoreRequestError) as context:
                middleware.process_request(request, spider)
            
            self.assertIn("站外请求被过滤", str(context.exception))
            
            # 检查增加了统计计数
            self.assertIn('offsite_request_count', self.crawler.stats.stats)
            self.assertEqual(self.crawler.stats.stats['offsite_request_count'], 1)
            self.assertIn('offsite_request_count/invalid_url', self.crawler.stats.stats)


if __name__ == '__main__':
    # 直接创建一个OffsiteMiddleware实例进行测试，绕过create_instance的复杂逻辑
    unittest.main()