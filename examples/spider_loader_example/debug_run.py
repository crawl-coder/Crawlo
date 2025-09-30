#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调试Spider Loader示例
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 确保当前目录也在路径中
sys.path.insert(0, os.getcwd())

# 直接从crawler模块导入CrawlerProcess
from crawlo.crawler import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.spider_loader import SpiderLoader


def debug_spider_loader():
    """调试SpiderLoader"""
    print("调试SpiderLoader...")
    
    # 手动创建设置
    settings = SettingManager({
        'SPIDER_MODULES': ['spider_loader_example.spiders'],
        'SPIDER_LOADER_WARN_ONLY': True,
        'PROJECT_NAME': 'spider_loader_example',
        'CONCURRENCY': 1,
        'LOG_LEVEL': 'DEBUG'
    })
    
    print(f"SPIDER_MODULES配置: {settings.get('SPIDER_MODULES')}")
    
    # 创建SpiderLoader
    loader = SpiderLoader.from_settings(settings)
    spider_names = loader.list()
    print(f"SpiderLoader发现的爬虫: {spider_names}")
    
    # 创建CrawlerProcess
    process = CrawlerProcess(settings=settings)
    process_spider_names = process.get_spider_names()
    print(f"CrawlerProcess发现的爬虫: {process_spider_names}")


if __name__ == '__main__':
    debug_spider_loader()