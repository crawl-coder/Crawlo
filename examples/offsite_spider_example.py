#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用OffsiteMiddleware的爬虫示例
展示如何在实际爬虫中使用OffsiteMiddleware限制爬取范围
"""

from crawlo.spider import Spider
from crawlo.network.request import Request


class ExampleSpider(Spider):
    """
    示例爬虫，演示OffsiteMiddleware的使用
    """
    
    # 爬虫名称
    name = "example_offsite_spider"
    
    # 自定义设置
    custom_settings = {
        # 允许的域名列表
        'ALLOWED_DOMAINS': [
            'httpbin.org',
            'example.com',
            'www.example.com'
        ],
        
        # 请求延迟（秒）
        'DOWNLOAD_DELAY': 1,
        
        # 并发数
        'CONCURRENCY': 4,
        
        # 日志级别
        'LOG_LEVEL': 'INFO',
    }
    
    def start_requests(self):
        """
        开始请求
        """
        # 这些URL会被允许
        allowed_urls = [
            'https://httpbin.org/ip',
            'https://httpbin.org/user-agent',
            'https://example.com/page1',
            'https://www.example.com/page2'
        ]
        
        # 这些URL会被过滤（站外请求）
        offsite_urls = [
            'https://google.com',
            'https://github.com',
            'https://stackoverflow.com'
        ]
        
        # 生成允许的请求
        for url in allowed_urls:
            yield Request(url=url, callback=self.parse_allowed)
            
        # 生成站外请求（会被OffsiteMiddleware过滤）
        for url in offsite_urls:
            yield Request(url=url, callback=self.parse_offsite)
    
    async def parse_allowed(self, response):
        """
        处理允许的请求响应
        """
        self.logger.info(f"成功处理允许的请求: {response.url}")
        self.logger.info(f"状态码: {response.status_code}")
        # 这里可以添加解析逻辑
        
    async def parse_offsite(self, response):
        """
        这个方法实际上不会被调用，因为站外请求会被过滤
        """
        self.logger.info(f"这个消息不应该出现: {response.url}")


# 运行爬虫的示例代码
if __name__ == "__main__":
    """
    运行说明:
    
    1. 确保已在项目根目录下安装了crawlo:
       pip install -e .
       
    2. 运行爬虫:
       crawlo run example_offsite_spider
       
    3. 观察日志输出:
       - 允许的域名请求会被正常处理
       - 站外请求会被OffsiteMiddleware过滤，并在日志中显示过滤信息
       - 统计信息会记录被过滤的请求数量
       
    OffsiteMiddleware的优势:
    ✓ 防止爬虫意外爬取到无关网站
    ✓ 节省带宽和服务器资源
    ✓ 提高爬取效率，专注于目标网站
    ✓ 可配置的域名白名单，灵活控制爬取范围
    """
    print("OffsiteSpider示例")
    print("=" * 30)
    print("此爬虫演示了OffsiteMiddleware的使用方法")
    print("请使用以下命令运行:")
    print("  crawlo run example_offsite_spider")