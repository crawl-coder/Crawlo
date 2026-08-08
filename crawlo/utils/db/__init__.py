# Database utilities package

from .mysql_helper import MySQLHelper, get_mysql_helper, check_exists
from .sql_builder import SQLBuilder
from .mysql_connection_pool import (
    MySQLConnectionPoolManager,
    get_mysql_pool,
    close_all_mysql_pools,
    is_pool_active,
    get_mysql_pool_stats
)
from .dialect import (
    SQLDialect,
    MySQLDialect,
    PostgreSQLDialect,
    SQLiteDialect,
    ClickHouseDialect,
)
from .pool_manager import BasePoolManager
from .mysql_exists_checker import MySQLExistsChecker

__all__ = [
    "MySQLHelper",
    "get_mysql_helper",
    "check_exists",
    "SQLBuilder",
    "MySQLConnectionPoolManager",
    "get_mysql_pool",
    "close_all_mysql_pools",
    "is_pool_active",
    "get_mysql_pool_stats",
    # SQL 方言
    'SQLDialect',
    'MySQLDialect',
    'PostgreSQLDialect',
    'SQLiteDialect',
    'ClickHouseDialect',
    # 连接池管理
    'BasePoolManager',
    # MySQL 存在性检查
    'MySQLExistsChecker',
]
