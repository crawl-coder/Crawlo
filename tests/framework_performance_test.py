#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo 框架性能测试脚本
用于评估框架在不同场景下的性能表现
"""

import asyncio
import time
import tracemalloc
import threading
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.crawler import CrawlerProcess
from crawlo.spider import Spider


def create_test_spider_class(spider_name, page_count):
    """动态创建测试爬虫类"""
    class TestSpider(Spider):
        # 显式设置name属性
        name = spider_name
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # 使用较少的测试页面以加快测试速度
            self.start_urls = [f'https://httpbin.org/delay/0?page={i}' for i in range(page_count)]
        
        def parse(self, response):
            """简单解析响应"""
            yield {
                'url': response.url,
                'status': response.status_code,  # 修复：使用status_code而不是status
                'page_id': response.url.split('page=')[-1] if 'page=' in response.url else 'unknown'
            }
    
    return TestSpider


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = {}
    
    def test_initialization_performance(self):
        """测试初始化性能"""
        print("测试初始化性能...")
        
        start_time = time.time()
        settings = {
            'CONCURRENT_REQUESTS': 10,
        }
        process = CrawlerProcess(settings=settings)
        end_time = time.time()
        
        init_time = end_time - start_time
        print(f"初始化时间: {init_time:.4f} 秒")
        return init_time
    
    async def run_crawler_test(self, test_pages=20, concurrent_requests=10, test_name="performance_test"):
        """运行爬虫性能测试"""
        # 配置设置
        settings = {
            'CONCURRENT_REQUESTS': concurrent_requests,
            'DOWNLOAD_DELAY': 0,
            'RANDOMIZE_DOWNLOAD_DELAY': False,
            'SCHEDULER_MAX_QUEUE_SIZE': 1000,
            'BACKPRESSURE_RATIO': 0.8,
        }
        
        # 创建测试爬虫类
        TestSpiderClass = create_test_spider_class(test_name, test_pages)
        
        # 注册爬虫类
        from crawlo.spider import get_global_spider_registry
        registry = get_global_spider_registry()
        registry[TestSpiderClass.name] = TestSpiderClass
        
        # 创建爬虫进程
        process = CrawlerProcess(settings=settings)
        
        # 添加测试爬虫
        crawler = await process.crawl(TestSpiderClass.name)
        
        # 计算性能指标
        metrics = crawler.metrics
        duration = metrics.get_total_duration()
        rps = test_pages / duration if duration > 0 else 0
        
        return {
            'duration': duration,
            'rps': rps,
            'pages': test_pages,
            'concurrent': concurrent_requests
        }
    
    async def run_scale_tests(self):
        """运行不同规模的测试"""
        print("\n=== 运行规模测试 ===")
        scales = [10, 20, 50]  # 减少测试规模以加快测试速度
        results = []
        
        for i, scale in enumerate(scales):
            test_name = f"scale_test_{i}_{scale}"
            print(f"测试规模: {scale} 个页面")
            try:
                result = await self.run_crawler_test(test_pages=scale, test_name=test_name)
                results.append(result)
                print(f"  完成时间: {result['duration']:.2f} 秒")
                print(f"  每秒请求数: {result['rps']:.2f} RPS")
            except Exception as e:
                print(f"  测试失败: {e}")
                import traceback
                traceback.print_exc()
            print()
        
        return results
    
    async def run_concurrency_tests(self):
        """运行不同并发数的测试"""
        print("\n=== 运行并发测试 ===")
        concurrencies = [1, 5, 10]  # 减少并发数以避免对测试服务器造成过大压力
        results = []
        
        for i, concurrency in enumerate(concurrencies):
            test_name = f"concurrency_test_{i}_{concurrency}"
            print(f"测试并发数: {concurrency}")
            try:
                result = await self.run_crawler_test(
                    test_pages=20, 
                    concurrent_requests=concurrency,
                    test_name=test_name
                )
                results.append(result)
                print(f"  完成时间: {result['duration']:.2f} 秒")
                print(f"  每秒请求数: {result['rps']:.2f} RPS")
            except Exception as e:
                print(f"  测试失败: {e}")
                import traceback
                traceback.print_exc()
            print()
        
        return results
    
    async def run_performance_suite(self):
        """运行完整的性能测试套件"""
        print("开始 Crawlo 框架性能测试")
        print("=" * 50)
        
        # 测试初始化性能
        init_time = self.test_initialization_performance()
        
        # 运行规模测试
        scale_results = await self.run_scale_tests()
        
        # 运行并发测试
        concurrency_results = await self.run_concurrency_tests()
        
        # 汇总结果
        print("\n=== 性能测试汇总 ===")
        print(f"初始化时间: {init_time:.4f} 秒")
        
        print("\n规模测试结果:")
        for result in scale_results:
            if 'duration' in result:
                print(f"  {result['pages']} 页面: {result['duration']:.2f}s, {result['rps']:.2f} RPS")
        
        print("\n并发测试结果:")
        for result in concurrency_results:
            if 'duration' in result:
                print(f"  {result['concurrent']} 并发: {result['duration']:.2f}s, {result['rps']:.2f} RPS")
        
        return {
            'initialization': init_time,
            'scale_tests': scale_results,
            'concurrency_tests': concurrency_results
        }


async def main():
    """主函数"""
    tester = PerformanceTester()
    results = await tester.run_performance_suite()
    
    print("\n=== 测试完成 ===")
    print("性能测试已完成，结果如上所示。")
    
    # 保存结果到文件
    import json
    with open('performance_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("结果已保存到 performance_test_results.json")


if __name__ == '__main__':
    asyncio.run(main())