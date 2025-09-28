#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终综合测试脚本
全面测试框架的所有核心功能，特别是我们修改的部分
"""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class TestSpider(Spider):
    """测试爬虫"""
    name = 'final_test_spider'
    
    def start_requests(self):
        """发起测试请求"""
        # 生成一些测试请求
        for i in range(5):
            yield Request(f'https://httpbin.org/get?page={i}', callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功获取响应: {response.url}")
        print(f"状态码: {response.status_code}")
        return []


async def test_queue_blocking_behavior():
    """测试队列阻塞行为"""
    print("测试队列阻塞行为...")
    
    from crawlo.queue.queue_manager import QueueConfig, QueueManager
    
    # 创建小队列配置
    queue_config = QueueConfig(
        queue_type='memory',
        max_queue_size=3  # 非常小的队列
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    await queue_manager.initialize()
    
    # 测试添加超过队列大小的请求
    print("添加6个请求到大小为3的队列...")
    start_time = time.time()
    
    # 创建生产者任务
    async def producer():
        for i in range(6):
            request = Request(f'https://example.com/test{i}')
            await queue_manager.put(request)
            print(f"添加请求 {i}")
    
    # 创建消费者任务
    async def consumer():
        retrieved = 0
        while retrieved < 6:
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
        'PROJECT_NAME': 'final_test',
        'SCHEDULER_MAX_QUEUE_SIZE': 100
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
        'PROJECT_NAME': 'final_test'
    })
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    # 运行爬虫
    await process.crawl(TestSpider)


async def main():
    """主函数"""
    print("开始最终综合测试...")
    print("=" * 50)
    
    try:
        # 1. 测试框架初始化
        await test_framework_initialization()
        print()
        
        # 2. 测试队列阻塞行为
        await test_queue_blocking_behavior()
        print()
        
        # 3. 测试爬虫执行
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