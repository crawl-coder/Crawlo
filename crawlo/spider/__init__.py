#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo Spider Module
==================
提供爬虫基类和相关功能。

核心功能:
- Spider基类：所有爬虫的基础类
- 自动注册机制：通过元类自动注册爬虫
- 配置管理：支持自定义设置和链式调用
- 生命周期管理：开启/关闭钩子函数
- 分布式支持：智能检测运行模式

使用示例:
    class MySpider(Spider):
        name = 'my_spider'
        start_urls = ['http://example.com']
        
        # 自定义配置
        custom_settings = {
            'DOWNLOADER_TYPE': 'httpx',
            'CONCURRENCY': 10
        }
        
        def parse(self, response):
            # 解析逻辑
            yield Item(data=response.json())
"""
from .spider import (
    Spider,
    SpiderMeta,
    SpiderStatsTracker,
    create_spider_from_template,
    get_global_spider_registry,
    get_spider_by_name,
    get_all_spider_classes,
    get_spider_names,
    is_spider_registered,
    unregister_spider,
    reset_spider_registry,
)

__all__ = [
    'Spider',
    'SpiderMeta', 
    'SpiderStatsTracker',
    'create_spider_from_template',
    'get_global_spider_registry',
    'get_spider_by_name',
    'get_all_spider_classes',
    'get_spider_names',
    'is_spider_registered',
    'unregister_spider',
    'reset_spider_registry'
]
