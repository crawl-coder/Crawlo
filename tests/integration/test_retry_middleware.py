#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重试中间件功能
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.retry import RetryMiddleware
from crawlo.stats import StatsCollector
from crawlo.settings.setting_manager import SettingManager


class MockRequest:
    def __init__(self, url="http://example.com", meta=None):
        self.url = url
        self.meta = meta or {}
        self.priority = 0
        self.proxy = None

    def copy(self):
        new = MockRequest(url=self.url, meta=dict(self.meta))
        new.priority = self.priority
        new.proxy = self.proxy
        return new

    def __str__(self):
        return f"<Request {self.url}>"


class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.status = status_code


class MockSpider:
    def __init__(self, name="test_spider"):
        self.name = name
        
    def __str__(self):
        return self.name


def test_retry_middleware_creation():
    """测试重试中间件创建"""
    print("=== 测试重试中间件创建 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504])
    settings.set('IGNORE_HTTP_CODES', [404])
    settings.set('MAX_RETRY_TIMES', 3)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    # 创建统计收集器
    class MockCrawler:
        def __init__(self):
            self.settings = settings
    
    crawler = MockCrawler()
    stats = StatsCollector(crawler)
    crawler.stats = stats
    
    # 创建爬虫对象
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    
    # 创建重试中间件
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 验证配置
    assert middleware.retry_http_codes == [500, 502, 503, 504]
    assert middleware.ignore_http_codes == [404]
    assert middleware.max_retry_times == 3
    assert middleware.retry_priority == -1
    
    print("✅ 重试中间件创建测试通过")
    return middleware


def test_retry_http_codes():
    """测试HTTP状态码重试"""
    print("\n=== 测试HTTP状态码重试 ===")
    
    # 创建重试中间件
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504])
    settings.set('IGNORE_HTTP_CODES', [404])
    settings.set('MAX_RETRY_TIMES', 3)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    class MockCrawler:
        def __init__(self):
            self.settings = settings
    
    crawler = MockCrawler()
    stats = StatsCollector(crawler)
    crawler.stats = stats
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建请求和爬虫
    request = MockRequest()
    spider = MockSpider()
    
    # 测试需要重试的状态码
    for status_code in [500, 502, 503, 504]:
        # 为每个测试创建新的请求实例
        test_request = MockRequest()
        response = MockResponse(status_code)
        original_retry_times = test_request.meta.get('retry_times', 0)
        result = middleware.process_response(test_request, response, spider)
        
        # 应该返回重试的请求
        assert result is not None
        # 重构后中间件通过 request.copy() 返回新对象
        assert result is not test_request
        assert result.meta.get('retry_times', 0) == original_retry_times + 1
        assert result.meta.get('is_retry', False) is True
        print(f"  ✅ 状态码 {status_code} 重试测试通过")
    
    # 测试忽略的状态码
    test_request = MockRequest()
    response = MockResponse(404)
    result = middleware.process_response(test_request, response, spider)
    
    # 应该返回原始响应
    assert result == response
    print("  ✅ 忽略状态码 404 测试通过")
    
    # 测试正常状态码
    test_request = MockRequest()
    response = MockResponse(200)
    result = middleware.process_response(test_request, response, spider)
    
    # 应该返回原始响应
    assert result == response
    print("  ✅ 正常状态码 200 测试通过")


def test_retry_max_times():
    """测试最大重试次数限制"""
    print("\n=== 测试最大重试次数限制 ===")
    
    # 创建重试中间件
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500])
    settings.set('IGNORE_HTTP_CODES', [])
    settings.set('MAX_RETRY_TIMES', 2)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    class MockCrawler:
        def __init__(self):
            self.settings = settings
    
    crawler = MockCrawler()
    stats = StatsCollector(crawler)
    crawler.stats = stats
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建请求和爬虫
    request = MockRequest()
    spider = MockSpider()
    
    # 第一次重试
    response = MockResponse(500)
    result = middleware.process_response(request, response, spider)
    print(f"  第一次重试结果: {result}, 类型: {type(result)}")
    assert result is not None
    # 重构后中间件通过 request.copy() 返回新对象
    assert result is not request
    assert result.meta.get('retry_times', 0) == 1
    print("  ✅ 第一次重试测试通过")
    
    # 链式重试：第二次用第一次的返回值，累计 retry_times
    result2 = middleware.process_response(result, response, spider)
    print(f"  第二次重试结果: {result2}, 类型: {type(result2)}")
    assert result2 is not None
    assert result2 is not result
    assert result2.meta.get('retry_times', 0) == 2
    print("  ✅ 第二次重试测试通过")
    
    # 当达到最大重试次数（2）时，继续重试应放弃，返回原始响应
    result3 = middleware.process_response(result2, response, spider)
    print(f"  第三次重试结果: {result3}, 类型: {type(result3)}")
    assert result3 is response
    print("  ✅ 达到最大重试次数测试通过")


def test_retry_exceptions():
    """测试异常重试"""
    print("\n=== 测试异常重试 ===")
    
    # 创建重试中间件
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [])
    settings.set('IGNORE_HTTP_CODES', [])
    settings.set('MAX_RETRY_TIMES', 3)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    class MockCrawler:
        def __init__(self):
            self.settings = settings
    
    crawler = MockCrawler()
    stats = StatsCollector(crawler)
    crawler.stats = stats
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建请求和爬虫
    request = MockRequest()
    spider = MockSpider()
    
    # 测试连接错误异常
    try:
        from aiohttp.client_exceptions import ClientConnectorError
        import socket
        # 创建一个模拟的socket错误
        sock_error = socket.gaierror("test error")
        exc = ClientConnectorError(None, sock_error)
        result = middleware.process_exception(request, exc, spider)
        
        # 应该返回重试的请求
        assert result is not None
        assert result.meta.get('retry_times', 0) == 1
        assert result.meta.get('is_retry', False) is True
        print("  ✅ ClientConnectorError 异常重试测试通过")
    except ImportError:
        print("  ⚠️  ClientConnectorError 未安装，跳过测试")
    except Exception as e:
        print(f"  ⚠️  ClientConnectorError 测试出现异常: {e}")
    
    # 测试超时异常（使用新的请求对象）
    new_request = MockRequest()  # 创建新的请求对象
    exc = asyncio.TimeoutError()
    result = middleware.process_exception(new_request, exc, spider)
    print(f"  TimeoutError测试结果: {result}, 类型: {type(result)}")
    
    # 应该返回重试的请求
    assert result is not None
    assert result.meta.get('retry_times', 0) == 1
    assert result.meta.get('is_retry', False) is True
    print("  ✅ TimeoutError 异常重试测试通过")


def test_dont_retry_flag():
    """测试 dont_retry 标志"""
    print("\n=== 测试 dont_retry 标志 ===")
    
    # 创建重试中间件
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500])
    settings.set('IGNORE_HTTP_CODES', [])
    settings.set('MAX_RETRY_TIMES', 3)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    class MockCrawler:
        def __init__(self):
            self.settings = settings
    
    crawler = MockCrawler()
    stats = StatsCollector(crawler)
    crawler.stats = stats
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建带有 dont_retry 标志的请求和爬虫
    request = MockRequest(meta={'dont_retry': True})
    spider = MockSpider()
    
    # 测试带有 dont_retry 标志的响应
    response = MockResponse(500)
    result = middleware.process_response(request, response, spider)
    
    # 应该返回原始响应，不进行重试
    assert result == response
    print("  ✅ dont_retry 标志测试通过")


if __name__ == "__main__":
    print("开始测试重试中间件功能...")
    
    try:
        # 运行所有测试
        middleware = test_retry_middleware_creation()
        test_retry_http_codes()
        test_retry_max_times()
        test_retry_exceptions()
        test_dont_retry_flag()
        
        print("\n🎉 所有测试通过！重试中间件功能正常。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()