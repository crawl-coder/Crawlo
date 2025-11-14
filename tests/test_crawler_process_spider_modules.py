#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试CrawlerProcess与SPIDER_MODULES的集成
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.crawler import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager


def test_crawler_process_spider_modules():
    """测试CrawlerProcess与SPIDER_MODULES的集成"""
    print("测试CrawlerProcess与SPIDER_MODULES的集成...")
    
    # 创建一个包含SPIDER_MODULES的设置
    settings = SettingManager({
        'SPIDER_MODULES': ['tests.test_spiders'],
        'SPIDER_LOADER_WARN_ONLY': True,
        'CONCURRENCY': 1,
        'LOG_LEVEL': 'INFO'
    })
    
    # 创建CrawlerProcess实例
    process = CrawlerProcess(settings=settings)
    
    # 测试获取爬虫名称
    spider_names = process.get_spider_names()
    print(f"发现的爬虫: {spider_names}")
    
    # 测试检查爬虫是否已注册
    is_registered = process.is_spider_registered('test_spider')
    print(f"爬虫'test_spider'是否已注册: {is_registered}")
    
    # 测试获取爬虫类
    spider_class = process.get_spider_class('test_spider')
    print(f"爬虫'test_spider'的类: {spider_class}")
    
    print("测试完成!")


if __name__ == '__main__':
    test_crawler_process_spider_modules()