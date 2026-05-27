# -*- coding: utf-8 -*-
"""
数据库基础设施模块
=================
提供 Pipeline 体系所需的通用数据库工具：

- SQLDialect: SQL 方言描述器（MySQL / PostgreSQL / SQLite / ClickHouse）
- BasePoolManager: 连接池管理器基类（单例 + 引用计数 + 自动清理）

设计文档：docs/internal/db-pipelines-design.md
"""

from .dialect import (
    SQLDialect,
    MySQLDialect,
    PostgreSQLDialect,
    SQLiteDialect,
    ClickHouseDialect,
)
from .pool_manager import BasePoolManager

__all__ = [
    # SQL 方言
    'SQLDialect',
    'MySQLDialect',
    'PostgreSQLDialect',
    'SQLiteDialect',
    'ClickHouseDialect',
    # 连接池管理
    'BasePoolManager',
]
