#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
百度网站测试脚本
测试Crawlo框架的基本功能
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request
from crawlo.crawler import CrawlerProcess


class BaiduSpider(Spider):
    name = 'baidu_test'
    
    def start_requests(self):
        # 测试百度首页
        yield Request('https://www.baidu.com/', callback=self.parse_home)
    
    def parse_home(self, response):
        self.logger.info(f"成功访问百度首页: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"页面标题: {response.xpath('//title/text()').get()}")
        
        # 测试提取一些链接
        links = response.xpath('//a/@href').getall()[:5]  # 只取前5个链接
        self.logger.info(f"提取到链接数量: {len(links)}")
        
        # 可以选择跟进一些链接进行测试
        for i, link in enumerate(links):
            if i >= 2:  # 只跟进前2个链接
                break
            # 确保链接是完整的URL
            if link.startswith('http'):
                yield Request(link, callback=self.parse_link)
    
    def parse_link(self, response):
        self.logger.info(f"访问链接: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")


async def main():
    # 创建爬虫进程
    process = CrawlerProcess(settings={
        'CONCURRENCY': 4,  # 设置并发数
        'DOWNLOAD_DELAY': 1,  # 设置下载延迟
        'LOG_LEVEL': 'INFO',  # 设置日志级别
    })
    
    # 运行爬虫
    await process.crawl(BaiduSpider)


if __name__ == '__main__':
    asyncio.run(main())