#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合测试脚本
测试Crawlo框架的所有优化功能
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request
from crawlo.crawler import CrawlerProcess


class ComprehensiveSpider(Spider):
    name = 'comprehensive_test'
    
    def start_requests(self):
        # 测试多个URL
        urls = [
            'https://www.baidu.com/',
            'https://www.baidu.com/s?wd=python',
            'https://www.baidu.com/s?wd=爬虫',
            'https://www.baidu.com/s?wd=框架',
            'https://www.baidu.com/s?wd=异步',
        ]
        
        for i, url in enumerate(urls):
            # 设置不同的优先级
            priority = -i  # 负数表示优先级，数值越小优先级越高
            yield Request(url, callback=self.parse, priority=priority)
    
    def parse(self, response):
        self.logger.info(f"访问URL: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"页面标题: {response.xpath('//title/text()').get()}")
        
        # 提取一些链接用于进一步测试
        links = response.xpath('//a/@href').getall()[:3]  # 只取前3个链接
        
        # 跟进链接，设置不同的深度
        for link in links:
            if link.startswith('http'):
                # 创建新的请求，增加深度
                meta = response.meta.copy()
                meta['depth'] = meta.get('depth', 0) + 1
                yield Request(link, callback=self.parse_link, meta=meta)
    
    def parse_link(self, response):
        self.logger.info(f"跟进链接: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"页面深度: {response.meta.get('depth', 0)}")


async def main():
    # 创建爬虫进程
    process = CrawlerProcess(settings={
        'CONCURRENCY': 4,  # 设置并发数
        'DOWNLOAD_DELAY': 0.5,  # 设置下载延迟
        'LOG_LEVEL': 'INFO',  # 设置日志级别
        'SCHEDULER_MAX_QUEUE_SIZE': 100,  # 设置队列最大大小
    })
    
    # 运行爬虫
    await process.crawl(ComprehensiveSpider)
    
    # 输出统计信息
    if hasattr(process, 'get_metrics'):
        metrics = process.get_metrics()
        print(f"\n=== 爬虫统计信息 ===")
        print(f"总执行时间: {metrics.get('total_duration', 0):.2f}秒")
        print(f"总请求数: {metrics.get('total_requests', 0)}")
        print(f"成功请求数: {metrics.get('total_success', 0)}")
        print(f"错误请求数: {metrics.get('total_errors', 0)}")
        print(f"平均成功率: {metrics.get('average_success_rate', 0):.2f}%")


if __name__ == '__main__':
    asyncio.run(main())