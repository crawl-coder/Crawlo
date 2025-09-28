#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的Crawlo框架优化验证测试
用于快速验证优化效果
"""

import asyncio
import time
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.crawler import CrawlerProcess
from crawlo.spider import Spider
from crawlo import Request, Item


class SimpleTestSpider(Spider):
    """简单的测试爬虫"""
    name = 'simple_test'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 使用较少的测试页面以加快测试速度
        self.start_urls = ['https://httpbin.org/delay/0' for _ in range(10)]
    
    def parse(self, response):
        """简单解析响应"""
        yield {'url': response.url, 'status': response.status_code}


async def test_concurrent_performance():
    """测试并发性能"""
    print("开始并发性能测试...")
    
    # 配置设置
    settings = {
        'CONCURRENT_REQUESTS': 10,
        'DOWNLOAD_DELAY': 0.1,
        'RANDOMIZE_DOWNLOAD_DELAY': False,
        'SCHEDULER_MAX_QUEUE_SIZE': 5000,
        'BACKPRESSURE_RATIO': 0.9,
    }
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    # 记录开始时间
    start_time = time.time()
    
    # 添加测试爬虫
    crawler = await process.crawl(SimpleTestSpider)
    
    # 计算性能指标
    metrics = crawler.metrics
    duration = metrics.get_total_duration()
    pages = 10
    rps = pages / duration if duration > 0 else 0
    
    print(f"完成时间: {duration:.2f} 秒")
    print(f"每秒请求数: {rps:.2f} RPS")
    
    return duration, rps


async def test_sequential_performance():
    """测试顺序执行性能"""
    print("\n开始顺序执行性能测试...")
    
    # 配置设置
    settings = {
        'CONCURRENT_REQUESTS': 1,  # 顺序执行
        'DOWNLOAD_DELAY': 0.1,
        'RANDOMIZE_DOWNLOAD_DELAY': False,
        'SCHEDULER_MAX_QUEUE_SIZE': 5000,
        'BACKPRESSURE_RATIO': 0.9,
    }
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    # 记录开始时间
    start_time = time.time()
    
    # 添加测试爬虫
    crawler = await process.crawl(SimpleTestSpider)
    
    # 计算性能指标
    metrics = crawler.metrics
    duration = metrics.get_total_duration()
    pages = 10
    rps = pages / duration if duration > 0 else 0
    
    print(f"完成时间: {duration:.2f} 秒")
    print(f"每秒请求数: {rps:.2f} RPS")
    
    return duration, rps


async def main():
    """主函数"""
    print("Crawlo 框架优化效果验证测试")
    print("=" * 40)
    
    # 测试并发性能
    concurrent_duration, concurrent_rps = await test_concurrent_performance()
    
    # 测试顺序执行性能
    sequential_duration, sequential_rps = await test_sequential_performance()
    
    # 输出比较结果
    print("\n=== 性能对比 ===")
    print(f"并发执行: {concurrent_duration:.2f}s, {concurrent_rps:.2f} RPS")
    print(f"顺序执行: {sequential_duration:.2f}s, {sequential_rps:.2f} RPS")
    
    if concurrent_duration < sequential_duration:
        improvement = (sequential_duration - concurrent_duration) / sequential_duration * 100
        print(f"并发执行比顺序执行快 {improvement:.1f}%")
    else:
        print("并发执行性能未达到预期，请检查优化效果")


if __name__ == '__main__':
    asyncio.run(main())