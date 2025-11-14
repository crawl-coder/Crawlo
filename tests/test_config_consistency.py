#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置一致性优化
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.project import get_settings
from crawlo.crawler import Crawler
from crawlo.spider import Spider
from crawlo.utils.log import get_logger
from crawlo import Request


class TestSpider(Spider):
    name = "test_spider"
    
    def start_requests(self):
        yield Request("https://example.com")


async def test_config_consistency():
    """测试配置一致性优化"""
    print("测试配置一致性优化...")
    
    # 模拟单机模式配置但Redis可用的情况
    custom_settings = {
        'QUEUE_TYPE': 'auto',  # 自动检测模式
        'CONCURRENCY': 4,
        'DOWNLOAD_DELAY': 1.0,
        'LOG_LEVEL': 'INFO'
    }
    
    try:
        # 获取配置
        settings = get_settings(custom_settings)
        
        # 创建爬虫实例
        crawler = Crawler(TestSpider, settings)
        
        # 启动爬虫（这会触发调度器初始化）
        print("开始初始化爬虫...")
        await crawler.crawl()
        
        print("配置一致性测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试配置一致性优化...")
    print("=" * 50)
    
    try:
        await test_config_consistency()
        
        print("=" * 50)
        print("配置一致性优化测试完成！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置日志级别
    import logging
    logging.basicConfig(level=logging.INFO)
    
    asyncio.run(main())