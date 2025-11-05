#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试
测试 Crawlo 框架的核心功能集成
"""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from crawlo import Spider, Request, Item
from crawlo.extension.memory_monitor import MemoryMonitorExtension


class MockItem(Item):
    """模拟数据项"""
    title = ''
    url = ''


class MockSpider(Spider):
    """模拟爬虫"""
    name = 'mock_spider'
    
    async def start_requests(self):
        """发起模拟请求"""
        yield Request('https://httpbin.org/get', callback=self.parse)
    
    async def parse(self, response):
        """解析响应"""
        item = MockItem(
            title='Test Item',
            url=response.url
        )
        yield item


class MockSettings:
    """模拟设置"""
    def get(self, key, default=None):
        config = {
            'PROJECT_NAME': 'integration_test',
            'LOG_LEVEL': 'WARNING',  # 减少日志输出
            'REDIS_URL': 'redis://127.0.0.1:6379/15',
            'REDIS_HOST': '127.0.0.1',
            'REDIS_PORT': 6379,
            'REDIS_DB': 15,
            'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
            'CUSTOM_PIPELINES': ['crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'],
            'CUSTOM_EXTENSIONS': [
                'crawlo.extension.memory_monitor.MemoryMonitorExtension',
            ],
            'MEMORY_MONITOR_ENABLED': True,
            'MEMORY_MONITOR_INTERVAL': 1,
            'MEMORY_WARNING_THRESHOLD': 95.0,
            'MEMORY_CRITICAL_THRESHOLD': 98.0,
            'CONCURRENT_REQUESTS': 5,
            'DOWNLOAD_DELAY': 0.1,
        }
        return config.get(key, default)
    
    def get_int(self, key, default=0):
        value = self.get(key, default)
        return int(value) if value is not None else default
        
    def get_float(self, key, default=0.0):
        value = self.get(key, default)
        return float(value) if value is not None else default
        
    def get_bool(self, key, default=False):
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
        
    def get_list(self, key, default=None):
        value = self.get(key, default or [])
        if isinstance(value, str):
            return [v.strip() for v in value.split(',') if v.strip()]
        return list(value)


async def test_crawler_integration():
    """测试爬虫集成"""
    print("🔍 测试爬虫集成...")
    
    # 创建配置
    config = CrawloConfig.standalone(
        concurrency=2,
        download_delay=0.1,
        LOG_LEVEL='WARNING'
    )
    
    # 添加自定义管道和扩展
    config.set('CUSTOM_PIPELINES', [
        'crawlo.pipelines.console_pipeline.ConsolePipeline',
    ])
    
    config.set('CUSTOM_EXTENSIONS', [
        'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    ])
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=config.to_dict())
    
    # 添加爬虫
    process.crawl(MockSpider)
    
    # 运行测试
    await process.start()
    
    print("   爬虫集成测试完成")


async def test_extension_integration():
    """测试扩展集成"""
    print("🔍 测试扩展集成...")
    
    # 创建模拟爬虫
    mock_crawler = Mock()
    mock_crawler.settings = MockSettings()
    mock_crawler.subscriber = Mock()
    mock_crawler.subscriber.subscribe = Mock()
    
    try:
        # 尝试创建内存监控扩展实例
        extension = MemoryMonitorExtension.create_instance(mock_crawler)
        print("   扩展集成测试完成")
    except Exception as e:
        if "NotConfigured" in str(type(e)):
            print("   扩展未启用（正常情况）")
        else:
            raise e


async def main():
    """主测试函数"""
    print("开始Crawlo框架集成测试...")
    print("=" * 50)
    
    try:
        await test_crawler_integration()
        await test_extension_integration()
        
        print("=" * 50)
        print("所有集成测试通过！")
        
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
