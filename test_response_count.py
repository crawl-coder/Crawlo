#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试response_received_count统计是否正常工作
"""
import asyncio
from crawlo import Request
from crawlo.crawler import CrawlerProcess
from crawlo.spider import Spider


class TestSpider(Spider):
    name = "test_response_count"
    
    def start_requests(self):
        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/uuid",
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        print(f"成功获取响应: {response.url}")
        yield {"url": response.url, "status": response.status_code}


async def main():
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "CONCURRENCY": 2,
    })
    
    await process.crawl(TestSpider)
    
    # 检查统计信息
    crawler = process._crawlers[0] if process._crawlers else None
    if crawler and crawler.stats:
        stats = crawler.stats.get_stats()
        response_count = stats.get('response_received_count', 0)
        item_count = stats.get('item_successful_count', 0)
        print(f"\n统计信息:")
        print(f"  响应接收数: {response_count}")
        print(f"  项目成功数: {item_count}")
        
        if response_count > 0:
            print("✓ response_received_count 统计正常工作")
        else:
            print("✗ response_received_count 统计未正确更新")


if __name__ == "__main__":
    asyncio.run(main())