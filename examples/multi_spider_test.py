#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
多Spider场景测试
模拟项目中运行几百个Spider的情况
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Iterator
import sys
import os
sys.path.insert(0, '/Users/oscar/projects/Crawlo')

from crawlo.spider import Spider
from crawlo.crawler import Crawler, CrawlerProcess
from crawlo.utils.resource_manager import get_resource_manager, ResourceType
from crawlo.network.request import Request


class TestSpider(Spider):
    """测试用Spider"""
    name = "test_spider_base"  # 必须定义name属性
    
    def __init__(self, name: str = ""):
        super().__init__()
        self.name = name or f"test_spider_{int(time.time() * 1000) % 10000}"
        self.custom_settings = {
            'CONCURRENT_REQUESTS': 10,
            'DOWNLOAD_DELAY': 0.1,
        }
    
    def start_requests(self) -> Iterator[Request]:
        """开始请求"""
        # 模拟不同的起始URL，使用更稳定的测试URL
        urls = [
            f"https://httpbin.org/get?page={i}&spider={self.name}"
            for i in range(random.randint(3, 5))  # 减少请求数量以提高测试速度
        ]
        
        for url in urls:
            yield Request(url=url)
    
    def parse(self, response):
        """解析响应"""
        # 模拟解析逻辑，返回字典格式的数据
        yield {
            'url': response.url,
            'title': f"Title from {self.name}",
            'spider': self.name,
            'timestamp': time.time()
        }


class MultiSpiderManager:
    """多Spider管理器"""
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.spider_count = 0
        self.running_crawlers: List[Crawler] = []
        self.completed_crawlers: List[Crawler] = []
        self.resource_manager = get_resource_manager("multi_spider_manager")
        
        # 注册到资源管理器
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            "multi_spider_manager"
        )
    
    def create_spiders(self, count: int) -> List[type]:
        """创建指定数量的Spider类"""
        spiders = []
        for i in range(count):
            spider_name = f"test_spider_{int(time.time() * 1000) % 10000}_{i}"
            
            # 动态创建Spider类
            spider_class = type(
                f'TestSpider{i}',
                (TestSpider,),
                {
                    'name': spider_name,
                    '__module__': __name__
                }
            )
            spiders.append(spider_class)
        
        self.spider_count = count
        print(f"创建了 {count} 个Spider类")
        return spiders
    
    async def run_spiders_batch(self, spider_classes: List[type], 
                               batch_size: int = 10) -> Dict[str, Any]:
        """批量运行Spider"""
        results = {
            'total_spiders': len(spider_classes),
            'batches': 0,
            'completed': 0,
            'failed': 0,
            'total_runtime': 0.0,
            'resource_stats': []
        }
        
        # 分批运行
        for i in range(0, len(spider_classes), batch_size):
            batch = spider_classes[i:i + batch_size]
            results['batches'] += 1
            
            print(f"\n运行批次 {results['batches']}: {len(batch)} 个Spider")
            
            # 创建CrawlerProcess
            process = CrawlerProcess(max_concurrency=min(batch_size, self.max_concurrent))
            
            # 添加Spider到进程
            spider_names = []
            for spider_class in batch:
                spider_names.append(spider_class)
            
            # 记录开始时间
            start_time = time.time()
            
            try:
                # 运行批次
                _ = await process.crawl_multiple(spider_names)
                results['completed'] += len(batch)
                
                # 记录资源使用情况
                resource_stats = self._collect_resource_stats()
                results['resource_stats'].append(resource_stats)
                
            except Exception as e:
                print(f"批次运行失败: {e}")
                results['failed'] += len(batch)
            finally:
                # 记录运行时间
                batch_runtime = time.time() - start_time
                results['total_runtime'] += batch_runtime
                print(f"批次运行时间: {batch_runtime:.2f} 秒")
                
                # 清理资源
                await self._cleanup_process_resources(process)
        
        return results
    
    def _collect_resource_stats(self) -> Dict[str, Any]:
        """收集资源使用统计"""
        import psutil
        process = psutil.Process()
        return {
            'timestamp': time.time(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'active_resources': self.resource_manager._stats['active_resources']
        }
    
    async def _cleanup_process_resources(self, process):
        """清理进程资源"""
        # 清理CrawlerProcess中的资源
        if hasattr(process, '_crawlers'):
            for crawler in process._crawlers:
                if hasattr(crawler, '_resource_manager'):
                    await crawler._resource_manager.cleanup_all()
    
    async def run_concurrent_spiders(self, spider_classes: List[type], 
                                   max_concurrent: int = 20) -> Dict[str, Any]:
        """并发运行Spider"""
        print(f"\n并发运行 {len(spider_classes)} 个Spider (最大并发: {max_concurrent})")
        
        results = {
            'total_spiders': len(spider_classes),
            'concurrent_limit': max_concurrent,
            'completed': 0,
            'failed': 0,
            'total_runtime': 0.0,
            'peak_resources': {}
        }
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_spider(spider_class):
            async with semaphore:
                try:
                    # 创建单个爬虫实例
                    crawler = Crawler(spider_class)
                    
                    start_time = time.time()
                    await crawler.crawl()
                    runtime = time.time() - start_time
                    
                    results['completed'] += 1
                    print(f"Spider {spider_class.name} 完成，运行时间: {runtime:.2f} 秒")
                    
                    # 清理资源
                    await crawler._cleanup()
                    
                    return True
                except Exception as e:
                    results['failed'] += 1
                    print(f"Spider {spider_class.name} 失败: {e}")
                    return False
        
        # 并发运行所有Spider
        start_time = time.time()
        tasks = [run_single_spider(spider_class) for spider_class in spider_classes]
        await asyncio.gather(*tasks, return_exceptions=True)
        results['total_runtime'] = time.time() - start_time
        
        # 收集峰值资源使用情况
        results['peak_resources'] = self._collect_resource_stats()
        
        return results
    
    def _cleanup(self, resource=None):
        """清理资源"""
        print("多Spider管理器已清理")


async def test_hundreds_of_spiders(count: int = 100):
    """测试数百个Spider的运行"""
    print(f"开始测试 {count} 个Spider的运行")
    
    # 初始化框架
    from crawlo.initialization import initialize_framework
    settings = initialize_framework({
        'CONCURRENT_REQUESTS': 10,
        'DOWNLOAD_DELAY': 0.1,
        'LOG_LEVEL': 'WARNING'
    })
    
    # 创建管理器
    manager = MultiSpiderManager(max_concurrent=20)
    
    # 创建Spider
    spiders = manager.create_spiders(count)
    
    # 测试1: 分批运行
    print("\n=== 分批运行测试 ===")
    batch_results = await manager.run_spiders_batch(spiders, batch_size=10)
    print(f"分批运行结果:")
    print(f"  总Spider数: {batch_results['total_spiders']}")
    print(f"  批次数量: {batch_results['batches']}")
    print(f"  完成: {batch_results['completed']}")
    print(f"  失败: {batch_results['failed']}")
    print(f"  总运行时间: {batch_results['total_runtime']:.2f} 秒")
    
    # 测试2: 并发运行
    print("\n=== 并发运行测试 ===")
    concurrent_results = await manager.run_concurrent_spiders(spiders[:20], max_concurrent=10)
    print(f"并发运行结果:")
    print(f"  总Spider数: {concurrent_results['total_spiders']}")
    print(f"  完成: {concurrent_results['completed']}")
    print(f"  失败: {concurrent_results['failed']}")
    print(f"  总运行时间: {concurrent_results['total_runtime']:.2f} 秒")
    print(f"  峰值内存: {concurrent_results['peak_resources'].get('memory_mb', 0):.2f} MB")
    
    # 清理资源
    await manager.resource_manager.cleanup_all()
    
    # 检查是否有资源泄漏
    has_leak = batch_results['failed'] > 0 or concurrent_results['failed'] > 0
    if has_leak:
        print("⚠️  检测到运行失败，可能存在资源问题!")
        return False
    else:
        print("✅ 多Spider运行测试通过!")
        return True


if __name__ == "__main__":
    # 测试10个Spider（可以根据需要调整数量）
    spider_count = int(os.environ.get('SPIDER_COUNT', '10'))
    success = asyncio.run(test_hundreds_of_spiders(spider_count))
    
    # 根据结果返回状态码
    sys.exit(0 if success else 1)