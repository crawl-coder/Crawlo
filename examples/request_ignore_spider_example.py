#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用RequestIgnoreMiddleware的爬虫示例
展示如何在实际爬虫中利用RequestIgnoreMiddleware处理被忽略的请求
"""

from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.exceptions import IgnoreRequestError


class IgnoreExampleSpider(Spider):
    """
    示例爬虫，演示RequestIgnoreMiddleware的使用
    """
    
    # 爬虫名称
    name = "ignore_example_spider"
    
    # 自定义设置
    custom_settings = {
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
        urls = [
            'https://httpbin.org/status/200',  # 正常请求
            'https://httpbin.org/status/404',  # 404请求
            'https://httpbin.org/status/500',  # 500请求
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse_response)
        
        # 生成一些会被忽略的请求
        yield Request(url='https://example.com/ignore1', callback=self.parse_response)
        yield Request(url='https://example.com/ignore2', callback=self.parse_response)
    
    async def parse_response(self, response):
        """
        处理响应
        """
        self.logger.info(f"收到响应: {response.url} - 状态码: {response.status_code}")
        
        # 模拟某些条件下抛出IgnoreRequestError来忽略请求
        if "ignore" in response.url:
            self.logger.info(f"模拟忽略请求: {response.url}")
            # 抛出IgnoreRequestError来忽略这个请求
            raise IgnoreRequestError(f"模拟忽略请求: {response.url}")
        
        # 正常处理响应
        return None

    def handle_ignore_request(self, request, reason):
        """
        处理被忽略的请求
        这是一个自定义方法，可以用来处理特定的忽略逻辑
        """
        self.logger.info(f"处理被忽略的请求: {request.url} - 原因: {reason}")


# 运行爬虫的示例代码
if __name__ == "__main__":
    """
    运行说明:
    
    1. 确保已在项目根目录下安装了crawlo:
       pip install -e .
       
    2. 运行爬虫:
       crawlo run ignore_example_spider
       
    3. 观察日志输出:
       - 可以看到正常请求的处理
       - 可以看到被忽略请求的记录
       - 查看统计信息中的忽略计数
       
    RequestIgnoreMiddleware的优势:
    ✓ 自动记录所有被忽略的请求
    ✓ 提供详细的统计信息，便于分析爬虫行为
    ✓ 支持按原因和域名分类统计
    ✓ 无需额外代码，自动处理IgnoreRequestError异常
    """
    print("RequestIgnoreSpider示例")
    print("=" * 30)
    print("此爬虫演示了RequestIgnoreMiddleware的使用方法")
    print("请使用以下命令运行:")
    print("  crawlo run ignore_example_spider")