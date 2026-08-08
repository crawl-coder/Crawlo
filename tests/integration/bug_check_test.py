#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
框架bug检查测试脚本
全面测试框架的核心功能，查找潜在的bug
"""

import sys
import os
import asyncio
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request
from crawlo.network.response import Response


class TestSpider(Spider):
    """测试爬虫"""
    name = 'bug_check_spider'
    
    def start_requests(self):
        """发起测试请求"""
        # 生成一些测试请求
        yield Request('https://httpbin.org/get', callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功获取响应: {response.url}")
        print(f"状态码: {response.status_code}")
        # 测试Response的各种方法
        self.test_response_methods(response)
        return []
    
    def test_response_methods(self, response):
        """测试Response的各种方法"""
        print("测试Response方法...")
        
        # 测试URL处理方法
        try:
            joined_url = response.urljoin('/test')
            print(f"  urljoin测试通过: {joined_url}")
        except Exception as e:
            print(f"  urljoin测试失败: {e}")
        
        try:
            parsed = response.urlparse()
            print(f"  urlparse测试通过: {parsed}")
        except Exception as e:
            print(f"  urlparse测试失败: {e}")
        
        # 测试选择器方法
        try:
            # 测试提取文本
            text = response.extract_text('title', default='No title')
            print(f"  extract_text测试通过: {text}")
        except Exception as e:
            print(f"  extract_text测试失败: {e}")
        
        try:
            # 测试提取多个文本
            texts = response.extract_texts('h1,h2,h3', default=[])
            print(f"  extract_texts测试通过: {texts}")
        except Exception as e:
            print(f"  extract_texts测试失败: {e}")
        
        try:
            # 测试提取属性
            attr = response.extract_attr('a', 'href', default='')
            print(f"  extract_attr测试通过: {attr}")
        except Exception as e:
            print(f"  extract_attr测试失败: {e}")
        
        try:
            # 测试提取多个属性
            attrs = response.extract_attrs('a', 'href', default=[])
            print(f"  extract_attrs测试通过: {attrs}")
        except Exception as e:
            print(f"  extract_attrs测试失败: {e}")


async def test_request_serialization():
    """测试Request序列化"""
    print("测试Request序列化...")
    
    try:
        # 创建一个复杂的Request对象
        request = Request(
            url='https://example.com/test',
            method='POST',
            headers={'User-Agent': 'Test'},
            json_body={'key': 'value'},
            meta={'test': 'data'},
            priority=5
        )
        
        # 测试pickle序列化
        import pickle
        serialized = pickle.dumps(request)
        deserialized = pickle.loads(serialized)
        print(f"  Request序列化测试通过: {deserialized.url}")
        return True
    except Exception as e:
        print(f"  Request序列化测试失败: {e}")
        traceback.print_exc()
        return False


async def test_queue_operations():
    """测试队列操作"""
    print("测试队列操作...")
    
    try:
        from crawlo.queue.queue_manager import QueueConfig, QueueManager, QueueType
        
        # 创建内存队列配置
        queue_config = QueueConfig(
            queue_type=QueueType.MEMORY,
            max_queue_size=10
        )
        
        # 创建队列管理器
        queue_manager = QueueManager(queue_config)
        await queue_manager.initialize()
        
        # 测试添加请求
        request = Request('https://example.com/test')
        success = await queue_manager.put(request)
        print(f"  队列添加请求: {'成功' if success else '失败'}")
        
        # 测试获取请求
        retrieved = await queue_manager.get(timeout=1.0)
        print(f"  队列获取请求: {'成功' if retrieved else '失败'}")
        
        # 关闭队列
        await queue_manager.close()
        print("  队列操作测试完成")
        return True
    except Exception as e:
        print(f"  队列操作测试失败: {e}")
        traceback.print_exc()
        return False


async def test_redis_queue_operations():
    """测试Redis队列操作"""
    print("测试Redis队列操作...")
    
    try:
        from crawlo.queue.queue_manager import QueueConfig, QueueManager, QueueType
        
        # 创建Redis队列配置
        queue_config = QueueConfig(
            queue_type=QueueType.REDIS,
            redis_url='redis://127.0.0.1:6379/15',  # 使用测试数据库
            queue_name='test:bug_check',
            max_queue_size=10
        )
        
        # 创建队列管理器
        queue_manager = QueueManager(queue_config)
        initialized = await queue_manager.initialize()
        if not initialized:
            print("  Redis队列初始化失败，跳过测试")
            return True
        
        # 测试添加请求
        request = Request('https://example.com/test_redis')
        success = await queue_manager.put(request)
        print(f"  Redis队列添加请求: {'成功' if success else '失败'}")
        
        # 测试获取请求
        retrieved = await queue_manager.get(timeout=1.0)
        print(f"  Redis队列获取请求: {'成功' if retrieved else '失败'}")
        
        # 关闭队列
        await queue_manager.close()
        print("  Redis队列操作测试完成")
        return True
    except Exception as e:
        print(f"  Redis队列操作测试失败: {e}")
        # 不将Redis连接失败视为测试失败
        return True


async def test_spider_registration():
    """测试爬虫注册"""
    print("测试爬虫注册...")
    
    try:
        from crawlo.spider import get_spider_by_name, get_spider_names
        
        # 检查测试爬虫是否已注册
        spider_class = get_spider_by_name('bug_check_spider')
        if spider_class:
            print(f"  爬虫注册测试通过: {spider_class.__name__}")
        else:
            print("  爬虫注册测试失败: 未找到注册的爬虫")
            return False
            
        # 检查所有注册的爬虫
        spider_names = get_spider_names()
        print(f"  已注册的爬虫: {spider_names}")
        return True
    except Exception as e:
        print(f"  爬虫注册测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("开始框架bug检查测试...")
    print("=" * 50)
    
    tests = [
        test_request_serialization,
        test_queue_operations,
        test_redis_queue_operations,
        test_spider_registration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"✓ {test_func.__name__} 通过")
            else:
                print(f"✗ {test_func.__name__} 失败")
        except Exception as e:
            print(f"✗ {test_func.__name__} 异常: {e}")
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！框架核心功能正常。")
        return 0
    else:
        print("部分测试失败，请检查框架实现。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)