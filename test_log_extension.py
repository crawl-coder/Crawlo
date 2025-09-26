#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试LogIntervalExtension是否能正确显示response_received_count
"""
import asyncio
import time
from crawlo import Request
from crawlo.crawler import CrawlerProcess
from crawlo.spider import Spider


class TestSpider(Spider):
    name = "test_log_extension"
    
    def start_requests(self):
        # 使用一个更快响应的网站进行测试
        urls = [
            "https://httpbin.org/status/200",
            "https://httpbin.org/status/200",
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        # 返回一个生成器
        yield {"url": response.url, "status": response.status_code}


async def main():
    print("开始测试LogIntervalExtension...")
    
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "CONCURRENCY": 2,
        "INTERVAL": 3,  # 设置为3秒以便观察日志
    })
    
    # 给一些时间让爬虫启动
    crawl_task = asyncio.create_task(process.crawl(TestSpider))
    
    # 等待一段时间让日志输出
    await asyncio.sleep(5)
    
    # 等待爬虫完成
    await crawl_task
    
    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(main())