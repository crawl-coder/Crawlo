#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
综合测试SpiderLoader功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.spider_loader import SpiderLoader
from crawlo.crawler import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager


def test_spider_loader_comprehensive():
    """综合测试SpiderLoader功能"""
    print("综合测试SpiderLoader功能...")
    
    # 1. 测试基本的SpiderLoader功能
    print("\n1. 测试基本的SpiderLoader功能")
    settings = SettingManager({
        'SPIDER_MODULES': ['tests.test_spiders'],
        'SPIDER_LOADER_WARN_ONLY': True
    })
    
    loader = SpiderLoader.from_settings(settings)
    spider_names = loader.list()
    print(f"  发现的爬虫: {spider_names}")
    
    if spider_names:
        spider_name = spider_names[0]
        spider_class = loader.load(spider_name)
        print(f"  成功加载爬虫: {spider_name} -> {spider_class}")
    
    # 2. 测试CrawlerProcess与SPIDER_MODULES的集成
    print("\n2. 测试CrawlerProcess与SPIDER_MODULES的集成")
    process = CrawlerProcess(settings=settings)
    process_spider_names = process.get_spider_names()
    print(f"  CrawlerProcess发现的爬虫: {process_spider_names}")
    
    is_registered = process.is_spider_registered('test_spider')
    print(f"  爬虫'test_spider'是否已注册: {is_registered}")
    
    spider_class = process.get_spider_class('test_spider')
    print(f"  爬虫'test_spider'的类: {spider_class}")
    
    # 3. 测试接口规范
    print("\n3. 测试接口规范")
    # 检查SpiderLoader是否实现了ISpiderLoader接口所需的方法
    from crawlo.interfaces import ISpiderLoader
    # 由于ISpiderLoader是Protocol，我们不能直接使用isinstance检查
    # 而是检查是否实现了所需的方法
    required_methods = ['load', 'list', 'find_by_request']
    implements_interface = all(hasattr(loader, method) for method in required_methods)
    print(f"  SpiderLoader是否实现了ISpiderLoader接口: {implements_interface}")
    
    # 4. 测试方法存在性
    print("\n4. 测试方法存在性")
    required_methods = ['load', 'list', 'find_by_request', 'get_all']
    for method in required_methods:
        has_method = hasattr(loader, method)
        print(f"  SpiderLoader是否有{method}方法: {has_method}")
    
    print("\n综合测试完成!")


if __name__ == '__main__':
    test_spider_loader_comprehensive()