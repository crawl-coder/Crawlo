#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试LogIntervalExtension的效率计算修复
"""
import asyncio
import time
from crawlo.crawler import CrawlerProcess
from crawlo.spider import Spider
from crawlo import Request


class TestLogIntervalSpider(Spider):
    name = "test_log_interval_fix"
    
    def start_requests(self):
        # 发送多个请求以测试效率计算
        urls = [f"https://httpbin.org/uuid?i={i}" for i in range(10)]
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        # 确保返回一个生成器
        yield {"url": response.url, "status": response.status_code}
        return  # 显式返回以确保函数结束


async def main():
    print("测试LogIntervalExtension效率计算修复...")
    
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "INFO",
        "CONCURRENCY": 3,  # 降低并发数
        "INTERVAL": 2,  # 每2秒输出一次日志
        "DOWNLOAD_DELAY": 0.5,  # 增加延迟以延长运行时间
    })
    
    # 给一些时间让爬虫运行并显示日志
    await process.crawl(TestLogIntervalSpider)
    
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())