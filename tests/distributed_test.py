#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分布式模式测试脚本
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class DistributedTestSpider(Spider):
    """分布式测试爬虫"""
    name = 'distributed_test_spider'
    
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


async def test_distributed_mode():
    """测试分布式模式"""
    print("开始测试分布式模式...")
    
    # 初始化框架，设置为分布式模式
    from crawlo.initialization import initialize_framework
    custom_settings = {
        'RUN_MODE': 'distributed',
        'QUEUE_TYPE': 'redis',
        'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'REDIS_DB': 15,  # 使用测试数据库
        'PROJECT_NAME': 'distributed_test'
    }
    settings = initialize_framework(custom_settings)
    
    # 创建爬虫进程
    from crawlo.crawler import CrawlerProcess
    process = CrawlerProcess(settings=settings)
    
    # 运行爬虫
    await process.crawl(DistributedTestSpider)
    
    print("分布式模式测试完成！")


def main():
    """主函数"""
    print("开始分布式模式测试...")
    asyncio.run(test_distributed_mode())


if __name__ == "__main__":
    main()