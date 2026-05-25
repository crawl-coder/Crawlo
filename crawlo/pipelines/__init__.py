#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Pipeline 模块
=============

目录结构：
    base_pipeline.py        — 基类 (ResourceManagedPipeline / FileBasedPipeline / DedupPipeline)
    generic_sql.py          — SQL 通用基类
    generic_doc.py          — 文档型通用基类
    manager.py              — PipelineManager
    dedup/                  — 去重管道
    sql/                    — SQL 存储管道
    doc/                    — 文档型存储管道
    file/                   — 文件型输出管道
    hbase.py                — HBase 管道
    console.py              — 控制台输出

使用示例：
    PIPELINES = {
        'crawlo.pipelines.RedisDedupPipeline': 100,
        'crawlo.pipelines.MySQLPipeline': 300,
    }
"""

# ── 基类 ──
from .base_pipeline import (
    BasePipeline,
    ResourceManagedPipeline,
    FileBasedPipeline,
    DatabasePipeline,
    CacheBasedPipeline,
)

# ── 通用基类 ──
from .generic_sql import GenericSQLPipeline
from .generic_doc import GenericDocumentPipeline

# ── 去重管道 ──
from .dedup import MemoryDedupPipeline, RedisDedupPipeline, BloomDedupPipeline
from .dedup import MySQLDedupPipeline, DatabaseDedupPipeline

# ── SQL 存储管道 ──
from .sql import MySQLPipeline, SQLitePipeline, PostgreSQLPipeline, ClickHousePipeline

# ── 文档型存储管道 ──
from .doc import MongoPipeline, ElasticsearchPipeline

# ── 文件型管道 ──
from .file import CsvPipeline, CsvDictPipeline, JsonLinesPipeline, JsonArrayPipeline

# ── 其他 ──
from .hbase import HBasePipeline
from .console import ConsolePipeline

# 向后兼容别名
JsonPipeline = JsonLinesPipeline

__all__ = [
    # 基类
    'BasePipeline', 'ResourceManagedPipeline', 'FileBasedPipeline',
    'DatabasePipeline', 'CacheBasedPipeline',
    # 通用基类
    'GenericSQLPipeline', 'GenericDocumentPipeline',
    # 去重管道
    'MemoryDedupPipeline', 'RedisDedupPipeline', 'BloomDedupPipeline',
    'MySQLDedupPipeline', 'DatabaseDedupPipeline',
    # SQL 存储管道
    'MySQLPipeline', 'SQLitePipeline', 'PostgreSQLPipeline', 'ClickHousePipeline',
    # 文档型存储管道
    'MongoPipeline', 'ElasticsearchPipeline',
    # 宽列式
    'HBasePipeline',
    # 文件型/控制台
    'CsvPipeline', 'CsvDictPipeline',
    'JsonPipeline', 'JsonLinesPipeline', 'JsonArrayPipeline',
    'ConsolePipeline',
]
