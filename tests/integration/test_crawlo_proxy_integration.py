#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawlo框架代理集成测试
测试代理中间件与框架的集成
"""

import asyncio
import sys
import os
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.core.config import CrawloConfig
from crawlo.crawler_process import CrawlerProcess
from crawlo import Spider, Request, Item
from crawlo.middleware.proxy import ProxyMiddleware


class TestItem(Item):
    """测试结果项"""
    url = ''
    status = 0
    proxy = ''


class ProxyTestSpider(Spider):
    """代理测试爬虫"""
    name = 'proxy_test_spider'
    
    async def start_requests(self):
        """发起测试请求"""
        yield Request('https://httpbin.org/ip', callback=self.parse)
    
    async def parse(self, response):
        """解析响应"""
        import json
        try:
            data = json.loads(response.text)
            ip_info = data.get('origin', 'Unknown')
        except:
            ip_info = 'Parse error'
        
        item = TestItem(
            url=response.url,
            status=response.status_code,
            proxy=str(response.meta.get('proxy', 'No proxy'))
        )
        
        self.logger.info(f"Proxy test result: IP={ip_info}, Proxy={item.proxy}")
        yield item


async def test_proxy_integration():
    """测试代理集成"""
    print("🔍 测试代理集成...")
    
    # 创建配置
    config = CrawloConfig.standalone(
        concurrency=1,
        download_delay=0.1,
        # 代理配置
        # 高级代理配置（适用于ProxyMiddleware）
        # 只要配置了代理API URL，中间件就会自动启用
        PROXY_API_URL="https://proxy-api.example.com/get",  # 模拟代理API
        
        # 代理配置（适用于ProxyMiddleware）
        # 只要配置了代理列表，中间件就会自动启用
        # PROXY_LIST=["http://proxy1:8080", "http://proxy2:8080"],
        LOG_LEVEL='WARNING'  # 减少日志输出
    )
    
    # 添加代理中间件
    config.set('CUSTOM_MIDDLEWARES', [
        'crawlo.middleware.proxy.ProxyMiddleware',
    ])
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=config.to_dict())
    
    # 添加爬虫
    process.crawl(ProxyTestSpider)
    
    # 运行测试
    await process.start()
    
    print("   代理集成测试完成")


async def main():
    """主测试函数"""
    print("开始Crawlo框架代理集成测试...")
    print("=" * 50)
    
    try:
        await test_proxy_integration()
        
        print("=" * 50)
        print("所有代理集成测试通过！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)