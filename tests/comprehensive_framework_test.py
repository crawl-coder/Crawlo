#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合框架测试脚本
全面测试框架的所有核心功能
"""

import sys
import os
import asyncio
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class TestSpider(Spider):
    """测试爬虫"""
    name = 'framework_test_spider'
    
    def start_requests(self):
        """发起测试请求"""
        # 生成一些测试请求
        for i in range(3):
            yield Request(f'https://httpbin.org/get?page={i}', callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功获取响应: {response.url}")
        print(f"状态码: {response.status_code}")
        return []


async def test_framework_initialization():
    """测试框架初始化"""
    print("测试框架初始化...")
    
    from crawlo.initialization import initialize_framework
    
    # 测试默认配置
    settings = initialize_framework()
    print(f"默认配置 - RUN_MODE: {settings.get('RUN_MODE')}")
    print(f"默认配置 - QUEUE_TYPE: {settings.get('QUEUE_TYPE')}")
    
    # 测试自定义配置
    custom_settings = {
        'PROJECT_NAME': 'framework_test',
        'SCHEDULER_MAX_QUEUE_SIZE': 50
    }
    
    settings = initialize_framework(custom_settings)
    print(f"自定义配置 - PROJECT_NAME: {settings.get('PROJECT_NAME')}")
    print(f"自定义配置 - SCHEDULER_MAX_QUEUE_SIZE: {settings.get('SCHEDULER_MAX_QUEUE_SIZE')}")


async def test_crawler_execution():
    """测试爬虫执行"""
    print("测试爬虫执行...")
    
    from crawlo.initialization import initialize_framework
    from crawlo.crawler import CrawlerProcess
    
    # 初始化框架
    settings = initialize_framework({
        'PROJECT_NAME': 'framework_test'
    })
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    # 运行爬虫
    await process.crawl(TestSpider)


async def test_queue_system():
    """测试队列系统"""
    print("测试队列系统...")
    
    from crawlo.queue.queue_manager import QueueConfig, QueueManager
    from crawlo import Request
    
    # 创建小队列配置进行测试
    queue_config = QueueConfig(
        queue_type='memory',
        max_queue_size=5
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    await queue_manager.initialize()
    
    # 测试添加请求
    print("添加请求到队列...")
    for i in range(3):
        request = Request(f'https://example.com/test{i}')
        await queue_manager.put(request)
        print(f"添加请求 {i}")
    
    # 测试获取请求
    print("从队列获取请求...")
    for i in range(3):
        request = await queue_manager.get(timeout=1.0)
        if request:
            print(f"获取请求: {request.url}")
    
    # 关闭队列
    await queue_manager.close()


async def test_spider_registry():
    """测试爬虫注册系统"""
    print("测试爬虫注册系统...")
    
    from crawlo.spider import get_global_spider_registry, is_spider_registered, get_spider_names
    
    # 检查测试爬虫是否已注册
    spider_name = TestSpider.name
    is_registered = is_spider_registered(spider_name)
    print(f"爬虫 '{spider_name}' 是否已注册: {is_registered}")
    
    # 获取所有注册的爬虫名称
    spider_names = get_spider_names()
    print(f"所有注册的爬虫: {spider_names}")


async def test_logging_system():
    """测试日志系统"""
    print("测试日志系统...")
    
    from crawlo.logging import get_logger, configure_logging
    
    # 配置日志系统
    configure_logging({
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'logs/test_framework.log'
    })
    
    # 获取logger并记录日志
    logger = get_logger('test_framework')
    logger.info("这是测试日志信息")
    logger.warning("这是测试警告信息")
    logger.error("这是测试错误信息")


async def test_settings_system():
    """测试配置系统"""
    print("测试配置系统...")
    
    from crawlo.settings.setting_manager import SettingManager
    
    # 创建配置管理器
    settings = SettingManager()
    
    # 测试配置项
    settings.set('TEST_KEY', 'test_value')
    test_value = settings.get('TEST_KEY')
    print(f"配置项 TEST_KEY 的值: {test_value}")
    
    # 测试不同类型的配置项
    settings.set('TEST_INT', 42)
    test_int = settings.get_int('TEST_INT')
    print(f"配置项 TEST_INT 的值: {test_int}")
    
    settings.set('TEST_BOOL', True)
    test_bool = settings.get_bool('TEST_BOOL')
    print(f"配置项 TEST_BOOL 的值: {test_bool}")


async def main():
    """主函数"""
    print("开始综合框架测试...")
    print("=" * 50)
    
    try:
        # 1. 测试框架初始化
        await test_framework_initialization()
        print()
        
        # 2. 测试配置系统
        await test_settings_system()
        print()
        
        # 3. 测试日志系统
        await test_logging_system()
        print()
        
        # 4. 测试队列系统
        await test_queue_system()
        print()
        
        # 5. 测试爬虫注册系统
        await test_spider_registry()
        print()
        
        # 6. 测试爬虫执行
        await test_crawler_execution()
        print()
        
        print("=" * 50)
        print("所有测试通过！框架工作正常。")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())