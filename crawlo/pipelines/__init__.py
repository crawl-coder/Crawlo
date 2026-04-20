#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Pipeline 模块
=============

Pipeline体系：
- BasePipeline: 基础抽象类，定义Pipeline接口规范
- ResourceManagedPipeline: 提供资源管理功能（推荐使用）
- FileBasedPipeline/DatabasePipeline/CacheBasedPipeline: 特定场景的专用基类

内置去重Pipeline：
- MemoryDedupPipeline: 基于内存的去重
- RedisDedupPipeline: 基于Redis的分布式去重
- BloomDedupPipeline: 基于Bloom Filter的高效去重
- DatabaseDedupPipeline: 基于数据库的去重

数据存储Pipeline（支持短路径）：
- MySQLPipeline: MySQL数据库存储（短路径：crawlo.pipelines.MySQLPipeline）
- MongoPipeline: MongoDB数据库存储
- CsvPipeline: CSV文件存储
- JsonPipeline: JSON文件存储
- ConsolePipeline: 控制台输出

使用示例：
    # 在settings.py中配置（推荐：字典格式，数字越小越先执行）
    
    # 方式1：短路径（v1.6.0+，推荐）
    PIPELINES = {
        'crawlo.pipelines.RedisDedupPipeline': 100,  # 去重
        'crawlo.pipelines.MySQLPipeline': 300,       # MySQL存储
        'crawlo.pipelines.MongoPipeline': 400,       # MongoDB存储
    }
    
    # 方式2：完整路径（兼容所有版本）
    PIPELINES = {
        'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline': 100,
        'crawlo.pipelines.mysql_pipeline.MySQLPipeline': 300,
        'crawlo.pipelines.mongo_pipeline.MongoPipeline': 400,
    }
    
    # 兼容：列表格式（按顺序执行，默认优先级500）
    PIPELINES = [
        'crawlo.pipelines.RedisDedupPipeline',
        'crawlo.pipelines.MySQLPipeline',
    ]
"""

# 导入所有基类（从base_pipeline.py）
from .base_pipeline import (
    BasePipeline,
    ResourceManagedPipeline,
    FileBasedPipeline,
    DatabasePipeline,
    CacheBasedPipeline
)

# 导出去重管道
from .memory_dedup_pipeline import MemoryDedupPipeline
from .redis_dedup_pipeline import RedisDedupPipeline
from .bloom_dedup_pipeline import BloomDedupPipeline
from .database_dedup_pipeline import DatabaseDedupPipeline

# 导入常用数据存储管道（支持短路径配置）
from .mysql_pipeline import MySQLPipeline
from .mongo_pipeline import MongoPipeline
from .csv_pipeline import CsvPipeline
from .json_pipeline import JsonPipeline
from .console_pipeline import ConsolePipeline

__all__ = [
    # 基类
    'BasePipeline',
    'ResourceManagedPipeline',
    'FileBasedPipeline', 
    'DatabasePipeline',
    'CacheBasedPipeline',
    # 去重管道
    'MemoryDedupPipeline',
    'RedisDedupPipeline', 
    'BloomDedupPipeline',
    'DatabaseDedupPipeline',
    # 数据存储管道（支持短路径：crawlo.pipelines.MySQLPipeline）
    'MySQLPipeline',
    'MongoPipeline',
    'CsvPipeline',
    'JsonPipeline',
    'ConsolePipeline'
]