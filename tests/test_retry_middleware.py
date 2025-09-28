#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
RetryMiddleware 测试文件
用于测试重试中间件的功能
"""

import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.retry import RetryMiddleware
from crawlo.settings.setting_manager import SettingManager


class MockStats:
    """Mock Stats 类，用于测试统计信息"""
    def __init__(self):
        self.stats = {}

    def inc_value(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value
        else:
            self.stats[key] = value


class TestRetryMiddleware(unittest.TestCase):
    """RetryMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings
        self.crawler.stats = MockStats()

    def test_middleware_initialization(self):
        """测试中间件初始化"""
        # 设置重试配置
        self.settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504, 408])
        self.settings.set('IGNORE_HTTP_CODES', [404])
        self.settings.set('MAX_RETRY_TIMES', 3)
        self.settings.set('RETRY_EXCEPTIONS', [])
        self.settings.set('RETRY_PRIORITY', -10)
        
        # 应该正常创建实例
        middleware = RetryMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, RetryMiddleware)
        self.assertEqual(middleware.max_retry_times, 3)
        self.assertEqual(middleware.retry_priority, -10)

    def test_process_response_with_retry_code(self):
        """测试处理需要重试的响应码"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和响应对象
        request = Mock()
        request.meta = {}
        request.priority = 0  # 添加priority属性
        response = Mock()
        response.status_code = 500
        spider = Mock()
        
        # 处理响应
        result = middleware.process_response(request, response, spider)
        
        # 应该返回重试的请求
        self.assertEqual(result, request)
        self.assertEqual(request.meta['retry_times'], 1)
        self.assertTrue(request.meta['dont_retry'])
        self.assertEqual(request.priority, -10)

    def test_process_response_with_ignore_code(self):
        """测试处理需要忽略的响应码"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和响应对象
        request = Mock()
        request.meta = {}
        request.priority = 0  # 添加priority属性
        response = Mock()
        response.status_code = 404
        spider = Mock()
        
        # 处理响应
        result = middleware.process_response(request, response, spider)
        
        # 应该返回原始响应
        self.assertEqual(result, response)

    def test_process_response_with_dont_retry(self):
        """测试处理带有dont_retry标记的响应"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和响应对象
        request = Mock()
        request.meta = {'dont_retry': True}
        request.priority = 0  # 添加priority属性
        response = Mock()
        response.status_code = 500
        spider = Mock()
        
        # 处理响应
        result = middleware.process_response(request, response, spider)
        
        # 应该返回原始响应
        self.assertEqual(result, response)

    def test_process_response_with_max_retries_exceeded(self):
        """测试超过最大重试次数的响应"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和响应对象
        request = Mock()
        request.meta = {'retry_times': 3}  # 已达到最大重试次数
        request.priority = 0  # 添加priority属性
        response = Mock()
        response.status_code = 500
        spider = Mock()
        
        # 处理响应
        result = middleware.process_response(request, response, spider)
        
        # 应该返回原始响应
        self.assertEqual(result, response)

    def test_process_exception_with_retry_exception(self):
        """测试处理需要重试的异常"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[ValueError],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和异常对象
        request = Mock()
        request.meta = {}
        request.priority = 0  # 添加priority属性
        exc = ValueError("test error")
        spider = Mock()
        
        # 处理异常
        result = middleware.process_exception(request, exc, spider)
        
        # 应该返回重试的请求
        self.assertEqual(result, request)
        self.assertEqual(request.meta['retry_times'], 1)
        self.assertTrue(request.meta['dont_retry'])
        self.assertEqual(request.priority, -10)

    def test_process_exception_with_dont_retry(self):
        """测试处理带有dont_retry标记的异常"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[ValueError],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和异常对象
        request = Mock()
        request.meta = {'dont_retry': True}
        request.priority = 0  # 添加priority属性
        exc = ValueError("test error")
        spider = Mock()
        
        # 处理异常
        result = middleware.process_exception(request, exc, spider)
        
        # 应该返回None
        self.assertIsNone(result)

    def test_process_exception_with_non_retry_exception(self):
        """测试处理不需要重试的异常"""
        # 创建中间件实例
        middleware = RetryMiddleware(
            retry_http_codes=[500, 502, 503, 504, 408],
            ignore_http_codes=[404],
            max_retry_times=3,
            retry_exceptions=[ValueError],
            stats=MockStats(),
            retry_priority=-10
        )
        
        # 创建请求和异常对象
        request = Mock()
        request.meta = {}
        request.priority = 0  # 添加priority属性
        exc = TypeError("test error")  # 不在重试异常列表中
        spider = Mock()
        
        # 处理异常
        result = middleware.process_exception(request, exc, spider)
        
        # 应该返回None
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()