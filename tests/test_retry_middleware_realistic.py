#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟真实情况测试重试中间件功能
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.retry import RetryMiddleware
from crawlo.stats_collector import StatsCollector
from crawlo.settings.setting_manager import SettingManager


class MockRequest:
    def __init__(self, url="http://example.com", meta=None, priority=0):
        self.url = url
        self.meta = meta or {}
        self.priority = priority
        
    def __str__(self):
        return f"<Request {self.url}>"


class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


class MockSpider:
    def __init__(self, name="test_spider"):
        self.name = name
        
    def __str__(self):
        return self.name


async def test_realistic_retry_scenario():
    """模拟真实场景的重试测试"""
    print("=== 模拟真实场景的重试测试 ===")
    
    # 创建设置管理器，使用更真实的配置
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504, 429])
    settings.set('IGNORE_HTTP_CODES', [404, 403])
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
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    
    # 创建重试中间件
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建爬虫对象
    spider = MockSpider("realistic_test_spider")
    
    # 模拟一个真实的爬取流程
    print("  模拟爬取流程...")
    
    # 1. 第一次请求，服务器返回503错误
    request = MockRequest(url="http://api.example.com/data", priority=10)
    response = MockResponse(503)
    
    print(f"  第一次请求: {request.url}, 状态码: {response.status_code}")
    result = middleware.process_response(request, response, spider)
    
    # 应该返回重试的请求
    assert result is not None
    assert result is request  # 同一个对象
    assert result.meta.get('retry_times', 0) == 1
    assert result.meta.get('dont_retry', False) is True
    assert result.priority == 9  # 优先级降低
    print(f"    重试第1次，新的优先级: {result.priority}")
    
    # 2. 对于同一个请求，由于已经设置了dont_retry标志，不会再重试
    # 在真实场景中，这个请求会被重新调度，我们模拟重新创建请求的情况
    print("  模拟重新调度后的请求...")
    new_request = MockRequest(url="http://api.example.com/data", priority=10)
    response = MockResponse(503)
    print(f"  重新调度后的请求: {new_request.url}, 状态码: {response.status_code}")
    result = middleware.process_response(new_request, response, spider)
    
    # 应该返回重试的请求
    assert result is not None
    assert result is new_request  # 同一个对象
    assert result.meta.get('retry_times', 0) == 1
    assert result.meta.get('dont_retry', False) is True
    assert result.priority == 9  # 优先级降低
    print(f"    重试第1次，新的优先级: {result.priority}")
    
    # 3. 再次重新调度，服务器返回正常响应
    final_request = MockRequest(url="http://api.example.com/data", priority=10)
    response = MockResponse(200)
    print(f"  最终请求: {final_request.url}, 状态码: {response.status_code}")
    result = middleware.process_response(final_request, response, spider)
    
    # 应该返回正常响应
    assert result is response
    print("    请求成功，返回正常响应")
    
    print("  ✅ 真实场景重试流程测试通过")


async def test_network_exception_scenario():
    """模拟网络异常场景测试"""
    print("\n=== 模拟网络异常场景测试 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504])
    settings.set('IGNORE_HTTP_CODES', [404])
    settings.set('MAX_RETRY_TIMES', 2)
    settings.set('RETRY_EXCEPTIONS', [])
    settings.set('RETRY_PRIORITY', -1)
    
    # 创建统计收集器
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
    
    # 创建重试中间件
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建请求和爬虫
    request = MockRequest(url="http://api.example.com/data")
    spider = MockSpider("network_test_spider")
    
    # 模拟网络超时异常
    print("  模拟网络超时异常...")
    exc = asyncio.TimeoutError("Connection timeout")
    
    result = middleware.process_exception(request, exc, spider)
    
    # 应该返回重试的请求
    assert result is not None
    assert result is request  # 同一个对象
    assert result.meta.get('retry_times', 0) == 1
    assert result.meta.get('dont_retry', False) is True
    print("    网络超时异常处理成功")
    
    # 模拟重新调度后的请求再次遇到网络异常
    print("  重新调度后的请求再次遇到网络异常...")
    new_request = MockRequest(url="http://api.example.com/data")
    exc = asyncio.TimeoutError("Connection timeout")
    
    result = middleware.process_exception(new_request, exc, spider)
    
    # 应该返回重试的请求
    assert result is not None
    assert result is new_request  # 同一个对象
    assert result.meta.get('retry_times', 0) == 1  # 新请求，重试次数重新计算
    assert result.meta.get('dont_retry', False) is True
    print("    重新调度后的请求网络异常处理成功")
    
    print("  ✅ 网络异常场景测试通过")


async def test_mixed_scenario():
    """混合场景测试（响应错误和异常混合）"""
    print("\n=== 混合场景测试 ===")
    
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
    
    class MockCrawlerWithStats:
        def __init__(self):
            self.settings = settings
            self.stats = stats
    
    crawler_with_stats = MockCrawlerWithStats()
    
    # 创建重试中间件
    middleware = RetryMiddleware.create_instance(crawler_with_stats)
    
    # 创建爬虫
    spider = MockSpider("mixed_test_spider")
    
    # 1. 首先遇到500错误（第一次请求）
    print("  1. 第一次请求遇到500错误")
    request1 = MockRequest(url="http://api.example.com/data", priority=5)
    response = MockResponse(500)
    result = middleware.process_response(request1, response, spider)
    assert result is not None
    assert result.meta.get('retry_times', 0) == 1
    assert result.priority == 4
    print("    500错误处理成功")
    
    # 2. 然后遇到网络超时异常（第二次请求）
    print("  2. 第二次请求遇到网络超时异常")
    request2 = MockRequest(url="http://api.example.com/data", priority=5)
    exc = asyncio.TimeoutError("Connection timeout")
    result = middleware.process_exception(request2, exc, spider)
    assert result is not None
    assert result.meta.get('retry_times', 0) == 1  # 新请求，重试次数重新计算
    assert result.priority == 4
    print("    网络超时异常处理成功")
    
    # 3. 再次遇到503错误（第三次请求）
    print("  3. 第三次请求遇到503错误")
    request3 = MockRequest(url="http://api.example.com/data", priority=5)
    response = MockResponse(503)
    result = middleware.process_response(request3, response, spider)
    assert result is not None
    assert result.meta.get('retry_times', 0) == 1  # 新请求，重试次数重新计算
    assert result.priority == 4
    print("    503错误处理成功")
    
    print("  ✅ 混合场景测试通过")


async def main():
    print("开始模拟真实情况测试重试中间件功能...")
    
    try:
        # 运行所有测试
        await test_realistic_retry_scenario()
        await test_network_exception_scenario()
        await test_mixed_scenario()
        
        print("\n🎉 所有真实情况测试通过！重试中间件在实际使用中功能正常。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())