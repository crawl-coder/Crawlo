#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证代理使用示例
演示如何在 Crawlo 框架中使用认证代理
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.core.config import CrawloConfig
from crawlo.crawler_process import CrawlerProcess
from crawlo import Spider, Request, Item


class ProxyItem(Item):
    """代理测试结果项"""
    url = ''
    status = 0
    proxy = ''
    response_time = 0.0


class AuthProxySpider(Spider):
    """认证代理测试爬虫"""
    name = 'auth_proxy_spider'
    
    async def start_requests(self):
        """发起测试请求"""
        urls = [
            'https://httpbin.org/ip',  # 查看IP地址
            'https://httpbin.org/headers',  # 查看请求头
        ]
        
        for url in urls:
            yield Request(url, callback=self.parse_response)
    
    async def parse_response(self, response):
        """解析响应"""
        import time
        import json
        
        # 获取代理信息
        proxy_info = response.meta.get('proxy', 'No proxy')
        
        # 解析响应内容
        try:
            data = json.loads(response.text)
            ip_info = data.get('origin', 'Unknown')
        except:
            ip_info = response.text[:100] + '...' if len(response.text) > 100 else response.text
        
        # 创建结果项
        item = ProxyItem(
            url=response.url,
            status=response.status_code,  # 修复：使用status_code而不是status
            proxy=str(proxy_info),
            response_time=response.meta.get('download_latency', 0)
        )
        
        self.logger.info(f"Proxy test result: {item}")
        yield item


async def main():
    """主函数"""
    print("🚀 开始认证代理测试...")
    
    # 创建配置（使用认证代理）
    config = CrawloConfig.standalone(
        concurrency=2,
        download_delay=1.0,
        # 代理配置
        # 高级代理配置（适用于ProxyMiddleware）
        # 只要配置了代理API URL，中间件就会自动启用
        PROXY_API_URL="http://proxy-api.example.com/get",  # 代理API地址
        
        # 代理配置（适用于ProxyMiddleware）
        # 只要配置了代理列表，中间件就会自动启用
        # PROXY_LIST=[
        #     "http://user:pass@proxy1.example.com:8080",
        #     "http://user:pass@proxy2.example.com:8080"
        # ],
        
        LOG_LEVEL='INFO'
    )
    
    # 添加自定义中间件
    config.set('CUSTOM_MIDDLEWARES', [
        'crawlo.middleware.proxy.ProxyMiddleware',
    ])
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=config.to_dict())
    
    # 添加爬虫
    process.crawl(AuthProxySpider)
    
    # 启动爬虫
    print("🔄 正在运行代理测试...")
    await process.start()
    
    print("✅ 认证代理测试完成！")


if __name__ == "__main__":
    asyncio.run(main())