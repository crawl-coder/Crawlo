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

# ── 文件型管道（无外部依赖） ──
from .file import CsvPipeline, CsvDictPipeline, JsonLinesPipeline, JsonArrayPipeline

# ── 控制台管道 ──
from .console import ConsolePipeline


def __getattr__(name):
    """延迟导入有可选依赖的 Pipeline，避免强制安装 asyncmy/pymongo/aiosqlite 等"""
    import importlib

    _lazy_map = {
        # SQL 存储管道（依赖 asyncmy/aiosqlite/asyncpg/clickhouse-connect）
        'MySQLPipeline': ('crawlo.pipelines.sql.mysql', 'MySQLPipeline'),
        'SQLitePipeline': ('crawlo.pipelines.sql.sqlite', 'SQLitePipeline'),
        'PostgreSQLPipeline': ('crawlo.pipelines.sql.postgresql', 'PostgreSQLPipeline'),
        'ClickHousePipeline': ('crawlo.pipelines.sql.clickhouse', 'ClickHousePipeline'),
        # 文档型存储管道（依赖 pymongo/elasticsearch）
        'MongoPipeline': ('crawlo.pipelines.doc.mongo', 'MongoPipeline'),
        'ElasticsearchPipeline': ('crawlo.pipelines.doc.elasticsearch', 'ElasticsearchPipeline'),
        # 其他有外部依赖的管道
        'HBasePipeline': ('crawlo.pipelines.hbase', 'HBasePipeline'),
        'BloomDedupPipeline': ('crawlo.pipelines.dedup.bloom', 'BloomDedupPipeline'),
        'MySQLDedupPipeline': ('crawlo.pipelines.dedup.mysql', 'MySQLDedupPipeline'),
        'DatabaseDedupPipeline': ('crawlo.pipelines.dedup.mysql', 'DatabaseDedupPipeline'),
    }
    if name in _lazy_map:
        module_path, attr = _lazy_map[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'crawlo.pipelines' has no attribute '{name}'")

# 向后兼容别名
JsonPipeline = JsonLinesPipeline

__all__ = [
    # 基类
    'BasePipeline', 'ResourceManagedPipeline', 'FileBasedPipeline',
    'DatabasePipeline', 'CacheBasedPipeline',
    # 通用基类
    'GenericSQLPipeline', 'GenericDocumentPipeline',
    # 去重管道（Memory/Redis 无外部依赖）
    'MemoryDedupPipeline', 'RedisDedupPipeline',
    # 文件型/控制台（无外部依赖）
    'CsvPipeline', 'CsvDictPipeline',
    'JsonPipeline', 'JsonLinesPipeline', 'JsonArrayPipeline',
    'ConsolePipeline',
]
