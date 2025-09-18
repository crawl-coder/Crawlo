#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
代理爬虫示例
==============
展示如何在Crawlo框架中使用代理API爬取网站
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request
from crawlo.network.response import Response


class ProxyExampleSpider(Spider):
    """使用代理的示例爬虫"""
    name = 'proxy_example_spider'
    
    def __init__(self):
        super().__init__()
        # 要爬取的URL列表
        self.urls = [
            'https://httpbin.org/ip',  # 查看当前IP
            'https://httpbin.org/headers',  # 查看请求头
            'https://stock.10jqka.com.cn/20240315/c655957791.shtml',  # 测试目标链接
        ]
    
    def start_requests(self):
        """生成初始请求"""
        for i, url in enumerate(self.urls):
            # 为每个请求添加一些元数据
            request = Request(
                url=url,
                callback=self.parse,
                meta={'request_id': i}
            )
            yield request
    
    def parse(self, response: Response):
        """解析响应"""
        request_id = response.request.meta.get('request_id', 'unknown')
        
        print(f"\n{'='*50}")
        print(f"请求 #{request_id}: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"{'='*50}")
        
        # 特殊处理httpbin.org的响应
        if 'httpbin.org/ip' in response.url:
            print("当前IP信息:")
            print(response.text[:500])
            
        elif 'httpbin.org/headers' in response.url:
            print("请求头信息:")
            print(response.text[:500])
            
        else:
            # 处理目标网站
            print("页面标题:")
            title = response.css('title::text').get()
            if title:
                print(f"  {title}")
            else:
                print("  未找到标题")
            
            print("\n页面内容预览:")
            # 清理HTML标签，只显示文本内容
            text_content = response.css('*::text').getall()
            if text_content:
                # 合并前几个文本片段
                content = ''.join(text_content[:10])
                print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
            else:
                print("  无文本内容")
        
        # 返回结果
        return {
            'request_id': request_id,
            'url': response.url,
            'status_code': response.status_code,
            'title': response.css('title::text').get(),
        }


# 配置说明
SETTINGS = {
    # 基础配置
    'LOG_LEVEL': 'INFO',
    'CONCURRENCY': 2,
    
    # 代理配置
    'PROXY_ENABLED': True,
    'PROXY_API_URL': 'http://test.proxy.api:8080/proxy/getitem/',
    'PROXY_EXTRACTOR': 'proxy',
    'PROXY_REFRESH_INTERVAL': 60,  # 1分钟刷新一次
    'PROXY_API_TIMEOUT': 10,
    'PROXY_POOL_SIZE': 5,
    'PROXY_HEALTH_CHECK_THRESHOLD': 0.5,
    
    # 下载延迟
    'DOWNLOAD_DELAY': 1,
    'RANDOMNESS': True,
    
    # 中间件
    'MIDDLEWARES': [
        'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
        'crawlo.middleware.download_delay.DownloadDelayMiddleware',
        'crawlo.middleware.default_header.DefaultHeaderMiddleware',
        'crawlo.middleware.proxy.ProxyMiddleware',
        'crawlo.middleware.retry.RetryMiddleware',
        'crawlo.middleware.response_code.ResponseCodeMiddleware',
        'crawlo.middleware.response_filter.ResponseFilterMiddleware',
    ],
    
    # 管道
    'PIPELINES': [
        'crawlo.pipelines.console_pipeline.ConsolePipeline',
    ],
    
    # 默认请求头
    'DEFAULT_REQUEST_HEADERS': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
}


def main():
    """主函数"""
    print("代理爬虫示例")
    print("=" * 50)
    print("此示例展示如何在Crawlo框架中使用代理API")
    print("代理API: http://test.proxy.api:8080/proxy/getitem/")
    print("目标网站: https://stock.10jqka.com.cn/20240315/c655957791.shtml")
    print("=" * 50)
    
    print("\n使用方法:")
    print("1. 确保在settings.py中配置了代理参数")
    print("2. 运行爬虫: crawlo run proxy_example_spider")
    print("3. 爬虫会自动使用代理API获取代理并应用到请求中")
    
    print("\n配置示例:")
    for key, value in SETTINGS.items():
        if key in ['MIDDLEWARES', 'PIPELINES', 'DEFAULT_REQUEST_HEADERS']:
            print(f"{key}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")


if __name__ == '__main__':
    main()