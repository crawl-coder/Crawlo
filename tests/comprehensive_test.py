#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合测试脚本
测试框架的核心功能
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class TestSpider(Spider):
    """测试爬虫"""
    name = 'comprehensive_test_spider'
    
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


async def test_framework_features():
    """测试框架功能"""
    print("开始综合测试...")
    
    # 1. 测试框架初始化
    print("\n1. 测试框架初始化...")
    from crawlo.initialization import initialize_framework
    
    # 测试默认配置
    settings = initialize_framework()
    print(f"默认配置 - RUN_MODE: {settings.get('RUN_MODE')}")
    print(f"默认配置 - QUEUE_TYPE: {settings.get('QUEUE_TYPE')}")
    
    # 2. 测试自定义配置
    print("\n2. 测试自定义配置...")
    custom_settings = {
        'RUN_MODE': 'distributed',
        'QUEUE_TYPE': 'memory',  # 使用内存队列进行测试
        'PROJECT_NAME': 'comprehensive_test'
    }
    
    # 重新初始化框架
    settings = initialize_framework(custom_settings)
    print(f"自定义配置 - RUN_MODE: {settings.get('RUN_MODE')}")
    print(f"自定义配置 - QUEUE_TYPE: {settings.get('QUEUE_TYPE')}")
    
    # 3. 测试爬虫运行
    print("\n3. 测试爬虫运行...")
    from crawlo.crawler import CrawlerProcess
    process = CrawlerProcess(settings=settings)
    await process.crawl(TestSpider)
    
    # 4. 测试队列系统
    print("\n4. 测试队列系统...")
    from crawlo.queue.queue_manager import QueueConfig, QueueManager
    
    # 创建队列配置
    queue_config = QueueConfig(
        queue_type='memory',
        max_queue_size=5
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    await queue_manager.initialize()
    
    # 测试添加请求
    request = Request('https://example.com/test')
    success = await queue_manager.put(request)
    print(f"添加请求到队列: {'成功' if success else '失败'}")
    
    # 测试获取请求
    retrieved_request = await queue_manager.get(timeout=1.0)
    print(f"从队列获取请求: {'成功' if retrieved_request else '失败'}")
    
    # 关闭队列
    await queue_manager.close()
    
    print("\n综合测试完成！")


def main():
    """主函数"""
    asyncio.run(test_framework_features())


if __name__ == "__main__":
    main()