#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 统计模块
==============
提供可插拔的统计后端接口和统计收集器。

核心组件：
- StatsCollector: 统计收集器（框架主要入口）
- StatsBackend: 统计后端抽象基类
- MemoryStatsBackend: 内存存储后端（默认）
- RedisStatsBackend: Redis 存储后端
- FileStatsBackend: 文件存储后端
- StatsBackendFactory: 后端工厂

使用示例：
    from crawlo.stats import StatsCollector
    
    # 在 Crawler 中使用
    collector = StatsCollector(crawler)
    collector.inc_value('items_scraped')
    collector.get_stats()
"""

from crawlo.stats.collector import StatsCollector
from crawlo.stats.backends import (
    StatsBackend,
    MemoryStatsBackend,
    RedisStatsBackend,
    FileStatsBackend,
    StatsBackendFactory,
)

__all__ = [
    'StatsCollector',
    'StatsBackend',
    'MemoryStatsBackend',
    'RedisStatsBackend',
    'FileStatsBackend',
    'StatsBackendFactory',
]
