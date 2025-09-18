#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架代理集成测试
====================
展示如何在Crawlo框架中集成和使用指定的代理API
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Spider, Request
from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.settings.setting_manager import SettingManager


class TestProxySpider(Spider):
    """测试代理的爬虫示例"""
    name = 'test_proxy_spider'
    
    def __init__(self):
        super().__init__()
        self.test_urls = [
            'https://httpbin.org/ip',  # 查看IP地址
            'https://httpbin.org/headers',  # 查看请求头
            'https://stock.10jqka.com.cn/20240315/c655957791.shtml',  # 测试目标链接
        ]
    
    def start_requests(self):
        """生成初始请求"""
        for url in self.test_urls:
            request = Request(url=url, callback=self.parse)
            yield request
    
    def parse(self, response):
        """解析响应"""
        print(f"\n=== 响应详情 ===")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 对于httpbin.org/ip，显示IP信息
        if 'httpbin.org/ip' in response.url:
            print(f"IP信息: {response.text[:200]}")
            
        # 对于httpbin.org/headers，显示请求头信息
        elif 'httpbin.org/headers' in response.url:
            print(f"请求头信息: {response.text[:200]}")
            
        # 对于目标链接，显示部分内容
        else:
            # 只显示前200个字符
            content_preview = response.text[:200] if response.text else ""
            print(f"内容预览: {content_preview}")
            
        # 返回一个简单的item
        return {
            'url': response.url,
            'status_code': response.status_code,
            'title': response.css('title::text').get() if response.text else None
        }


def create_proxy_settings():
    """创建代理配置"""
    settings = SettingManager()
    
    # 基础配置
    settings.set("LOG_LEVEL", "INFO")
    settings.set("CONCURRENCY", 1)  # 为了测试，设置并发数为1
    
    # 代理配置
    settings.set("PROXY_ENABLED", True)
    settings.set("PROXY_API_URL", "http://test.proxy.api:8080/proxy/getitem/")
    settings.set("PROXY_EXTRACTOR", "proxy")  # 根据API响应结构调整
    settings.set("PROXY_REFRESH_INTERVAL", 30)  # 30秒刷新一次
    settings.set("PROXY_API_TIMEOUT", 10)  # 10秒超时
    settings.set("PROXY_POOL_SIZE", 3)  # 代理池大小
    settings.set("PROXY_HEALTH_CHECK_THRESHOLD", 0.5)  # 健康检查阈值
    
    return settings


async def test_proxy_middleware_integration():
    """测试代理中间件集成"""
    print("=== 测试Crawlo代理中间件集成 ===")
    
    # 创建配置
    settings = create_proxy_settings()
    
    # 创建代理中间件实例
    proxy_middleware = ProxyMiddleware(settings, "INFO")
    
    # 测试代理API连接
    print(f"代理API URL: {proxy_middleware.api_url}")
    print(f"代理刷新间隔: {proxy_middleware.refresh_interval}秒")
    print(f"代理池大小: {proxy_middleware.proxy_pool_size}")
    
    # 测试获取代理
    print("\n--- 测试获取代理 ---")
    try:
        # 这里我们直接测试API连接，而不是完整的代理池更新
        proxy_data = await proxy_middleware._get_proxy_from_api()
        if proxy_data:
            print(f"✅ 成功从API获取代理信息: {proxy_data}")
        else:
            print("❌ 无法从API获取代理信息")
    except Exception as e:
        print(f"❌ 获取代理时出错: {e}")
    
    print("\n=== 代理中间件集成测试完成 ===")


def show_proxy_configuration_example():
    """显示代理配置示例"""
    print("\n=== 代理配置示例 ===")
    print("""
在Crawlo项目中配置代理的方法：

1. 在settings.py中添加以下配置：

```python
# 代理配置
PROXY_ENABLED = True
PROXY_API_URL = 'http://test.proxy.api:8080/proxy/getitem/'
PROXY_EXTRACTOR = 'proxy'
PROXY_REFRESH_INTERVAL = 30
PROXY_API_TIMEOUT = 10
PROXY_POOL_SIZE = 5
PROXY_HEALTH_CHECK_THRESHOLD = 0.5
```

2. 确保代理中间件在MIDDLEWARES列表中：

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',  # 代理中间件
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]
```

3. 启动爬虫后，代理中间件会自动：
   - 定期从API获取代理
   - 维护代理池
   - 自动为请求分配代理
   - 监控代理健康状态
""")


async def main():
    """主函数"""
    print("开始Crawlo代理集成测试...\n")
    
    # 1. 测试代理中间件集成
    await test_proxy_middleware_integration()
    
    # 2. 显示配置示例
    show_proxy_configuration_example()
    
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())