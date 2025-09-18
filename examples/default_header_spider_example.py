#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用DefaultHeaderMiddleware的爬虫示例
展示如何在实际爬虫中使用DefaultHeaderMiddleware添加默认请求头，支持随机更换功能
"""

from crawlo.spider import Spider
from crawlo.network.request import Request


class HeaderExampleSpider(Spider):
    """
    示例爬虫，演示DefaultHeaderMiddleware的使用，包括随机更换功能
    """
    
    # 爬虫名称
    name = "header_example_spider"
    
    # 自定义设置
    custom_settings = {
        # 默认请求头配置
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        },
        
        # 启用随机User-Agent功能
        'RANDOM_USER_AGENT_ENABLED': True,
        
        # 指定User-Agent设备类型（可选值: "desktop", "mobile", "all"）
        'USER_AGENT_DEVICE_TYPE': 'all',
        
        # 或者自定义User-Agent列表（可选，如果不配置将使用内置列表）
        # 'USER_AGENTS': [
        #     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        #     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        # ],
        
        # 随机请求头配置
        'RANDOM_HEADERS': {
            'Accept': [
                'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
            ],
            'Accept-Language': [
                'zh-CN,zh;q=0.9,en;q=0.8',
                'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
            ],
            'Cache-Control': 'no-cache'
        },
        
        # 启用随机性功能
        'RANDOMNESS': True,
        
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
            'https://httpbin.org/headers',  # 可以查看发送的请求头
            'https://httpbin.org/user-agent',  # 可以查看User-Agent
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse_headers)
    
    async def parse_headers(self, response):
        """
        处理响应，查看发送的请求头
        """
        self.logger.info(f"请求URL: {response.url}")
        self.logger.info(f"状态码: {response.status_code}")
        
        # 输出响应内容（包含请求头信息）
        try:
            import json
            data = json.loads(response.body.decode('utf-8'))
            self.logger.info("发送的请求头:")
            headers = data.get('headers', {})
            for key, value in headers.items():
                self.logger.info(f"  {key}: {value}")
        except Exception as e:
            self.logger.warning(f"解析响应失败: {e}")
            self.logger.info(f"响应内容: {response.body[:200]}...")


# 运行爬虫的示例代码
if __name__ == "__main__":
    """
    运行说明:
    
    1. 确保已在项目根目录下安装了crawlo:
       pip install -e .
       
    2. 运行爬虫:
       crawlo run header_example_spider
       
    3. 观察日志输出:
       - 可以看到发送的请求头信息
       - 验证随机User-Agent是否正确更换
       - 确认随机请求头是否按预期设置
       
    DefaultHeaderMiddleware的随机功能优势:
    ✓ 自动为每个请求随机更换User-Agent，降低被识别为爬虫的风险
    ✓ 支持按设备类型选择User-Agent（桌面/移动设备）
    ✓ 支持随机更换其他请求头，增加请求的多样性
    ✓ 可配置的随机策略，灵活适应不同网站的要求
    ✓ 保持默认请求头的一致性，同时增加随机性
    """
    print("DefaultHeaderSpider示例")
    print("=" * 30)
    print("此爬虫演示了DefaultHeaderMiddleware的随机更换功能")
    print("请使用以下命令运行:")
    print("  crawlo run header_example_spider")