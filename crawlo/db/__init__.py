# -*- coding: utf-8 -*-
"""
数据库基础设施模块（已迁移至 crawlo.utils.db）

此模块为向后兼容层，所有代码已迁移至 crawlo.utils.db：
- dialect → crawlo.utils.db.dialect
- pool_manager → crawlo.utils.db.pool_manager
"""

import sys
import warnings
import importlib

# 注册旧子模块路径，使 from crawlo.db.dialect import X 仍可用
_MODULE_MAP = {
    'crawlo.db.dialect': 'crawlo.utils.db.dialect',
    'crawlo.db.pool_manager': 'crawlo.utils.db.pool_manager',
}
for _old, _new in _MODULE_MAP.items():
    if _old not in sys.modules:
        sys.modules[_old] = importlib.import_module(_new)

from crawlo.utils.db.dialect import (
    SQLDialect,
    MySQLDialect,
    PostgreSQLDialect,
    SQLiteDialect,
    ClickHouseDialect,
)
from crawlo.utils.db.pool_manager import BasePoolManager

warnings.warn(
    "crawlo.db is deprecated, use crawlo.utils.db instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    'SQLDialect',
    'MySQLDialect',
    'PostgreSQLDialect',
    'SQLiteDialect',
    'ClickHouseDialect',
    'BasePoolManager',
]
