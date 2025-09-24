#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重构后的Crawlo使用示例
展示新的API和最佳实践
"""

import asyncio
from crawlo.framework import CrawloFramework, run_spider
from spider import OfweekSpider


async def example_1_simple_usage():
    """示例1：最简单的使用方式"""
    print("=== 示例1：简单使用 ===")
    
    # 直接运行爬虫，框架自动初始化
    await run_spider(OfweekSpider, {
        'LOG_LEVEL': 'INFO',
        'CONCURRENCY': 8
    })


async def example_2_framework_instance():
    """示例2：使用框架实例"""
    print("=== 示例2：框架实例 ===")
    
    # 创建框架实例
    framework = CrawloFramework({
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': 'logs/crawler.log',
        'CONCURRENCY': 16,
        'DOWNLOAD_DELAY': 1.0
    })
    
    # 运行爬虫
    crawler = await framework.run(OfweekSpider)
    
    # 获取指标
    metrics = crawler.metrics
    print(f"总耗时: {metrics.get_total_duration():.2f}秒")
    print(f"成功率: {metrics.get_success_rate():.1f}%")


async def example_3_multiple_spiders():
    """示例3：运行多个爬虫"""
    print("=== 示例3：多爬虫并发 ===")
    
    framework = CrawloFramework({
        'LOG_LEVEL': 'INFO',
        'CONCURRENCY': 12
    })
    
    # 同时运行多个爬虫（这里用同一个Spider演示）
    spiders = [OfweekSpider, OfweekSpider, OfweekSpider]
    results = await framework.run_multiple(spiders)
    
    print(f"完成 {len(results)} 个爬虫任务")
    
    # 框架整体指标
    framework_metrics = framework.get_metrics()
    print(f"总请求数: {framework_metrics.get('total_requests', 0)}")
    print(f"平均成功率: {framework_metrics.get('average_success_rate', 0):.1f}%")


async def example_4_error_handling():
    """示例4：错误处理演示"""
    print("=== 示例4：错误处理 ===")
    
    try:
        framework = CrawloFramework({'LOG_LEVEL': 'DEBUG'})
        await framework.run(OfweekSpider)
    except Exception as e:
        print(f"爬虫执行失败: {e}")
        # 框架提供了优雅的错误处理和降级策略


async def main():
    """主函数"""
    print("🚀 Crawlo重构版本示例\n")
    
    # 运行各个示例
    await example_1_simple_usage()
    print()
    
    await example_2_framework_instance()
    print()
    
    await example_3_multiple_spiders()
    print()
    
    await example_4_error_handling()
    print()
    
    print("✅ 所有示例执行完成")


if __name__ == '__main__':
    asyncio.run(main())