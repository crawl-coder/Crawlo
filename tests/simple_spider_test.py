#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的爬虫测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider import Spider
from crawlo import Request


class TestSpider(Spider):
    """测试爬虫"""
    name = 'test_spider'
    
    def start_requests(self):
        """发起测试请求"""
        yield Request('https://httpbin.org/get', callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功获取响应: {response.url}")
        print(f"状态码: {response.status_code}")
        return []


def main():
    """主函数"""
    print("开始测试爬虫功能...")
    
    # 初始化框架
    from crawlo.initialization import initialize_framework
    settings = initialize_framework()
    
    # 创建爬虫进程
    from crawlo.crawler import CrawlerProcess
    process = CrawlerProcess(settings=settings)
    
    # 运行爬虫
    import asyncio
    asyncio.run(process.crawl(TestSpider))
    
    print("爬虫测试完成！")


if __name__ == "__main__":
    main()