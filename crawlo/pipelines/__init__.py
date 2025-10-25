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

使用示例：
    # 在settings.py中配置
    PIPELINES = [
        'crawlo.pipelines.RedisDedupPipeline',
        'your_project.pipelines.MongoPipeline',
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
    'DatabaseDedupPipeline'
]