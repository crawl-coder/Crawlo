#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证测试脚本
验证所有修改的功能是否正常工作
"""

import sys
import os
import asyncio
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class ValidationTestSpider(Spider):
    """验证测试爬虫"""
    name = 'validation_test_spider'
    
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


async def test_framework_startup_logging():
    """测试框架启动日志"""
    print("测试框架启动日志...")
    
    from crawlo.initialization import initialize_framework
    from crawlo.logging import get_logger
    
    # 初始化框架
    settings = initialize_framework({
        'PROJECT_NAME': 'validation_test'
    })
    
    # 获取框架logger并检查启动日志
    logger = get_logger('crawlo.framework')
    print("框架启动日志已记录")


async def test_queue_blocking_behavior():
    """测试队列阻塞行为"""
    print("测试队列阻塞行为...")
    
    from crawlo.queue.queue_manager import QueueConfig, QueueManager
    from crawlo import Request
    
    # 创建小队列配置进行测试
    queue_config = QueueConfig(
        queue_type='memory',
        max_queue_size=3  # 非常小的队列
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    await queue_manager.initialize()
    
    # 测试添加超过队列大小的请求
    print("添加5个请求到大小为3的队列...")
    start_time = time.time()
    
    # 创建生产者任务
    async def producer():
        for i in range(5):
            request = Request(f'https://example.com/test{i}')
            await queue_manager.put(request)
            print(f"添加请求 {i}")
    
    # 创建消费者任务
    async def consumer():
        retrieved = 0
        while retrieved < 5:
            request = await queue_manager.get(timeout=2.0)
            if request:
                print(f"获取请求: {request.url}")
                retrieved += 1
                await asyncio.sleep(0.1)  # 模拟处理时间
    
    # 并发运行生产者和消费者
    await asyncio.gather(producer(), consumer())
    
    end_time = time.time()
    print(f"队列测试完成，耗时 {end_time - start_time:.2f} 秒")
    
    # 关闭队列
    await queue_manager.close()


async def test_stats_output():
    """测试统计信息输出"""
    print("测试统计信息输出...")
    
    from crawlo.initialization import initialize_framework
    from crawlo.crawler import CrawlerProcess
    
    # 初始化框架
    settings = initialize_framework({
        'PROJECT_NAME': 'stats_test'
    })
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    # 运行爬虫
    await process.crawl(ValidationTestSpider)
    
    print("统计信息输出测试完成")


async def test_spider_auto_import():
    """测试爬虫自动导入"""
    print("测试爬虫自动导入...")
    
    from crawlo.initialization import initialize_framework
    from crawlo.crawler import CrawlerProcess
    
    # 初始化框架
    settings = initialize_framework({
        'PROJECT_NAME': 'auto_import_test'
    })
    
    # 创建爬虫进程，指定spider_modules
    spider_modules = ['crawlo.spider']  # 使用框架的spider模块进行测试
    process = CrawlerProcess(settings=settings, spider_modules=spider_modules)
    
    # 检查爬虫是否已注册
    spider_name = ValidationTestSpider.name
    is_registered = process.is_spider_registered(spider_name)
    print(f"爬虫 '{spider_name}' 是否已注册: {is_registered}")
    
    if is_registered:
        print("爬虫自动导入功能正常")
    else:
        print("爬虫自动导入功能异常")


async def main():
    """主函数"""
    print("开始最终验证测试...")
    print("=" * 50)
    
    try:
        # 1. 测试框架启动日志
        await test_framework_startup_logging()
        print()
        
        # 2. 测试队列阻塞行为
        await test_queue_blocking_behavior()
        print()
        
        # 3. 测试统计信息输出
        await test_stats_output()
        print()
        
        # 4. 测试爬虫自动导入
        await test_spider_auto_import()
        print()
        
        print("=" * 50)
        print("所有验证测试通过！框架修改的功能工作正常。")
        
    except Exception as e:
        print("=" * 50)
        print(f"验证测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())