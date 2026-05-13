#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL Data Existence Checker
============================

Used to check if data already exists in the database during crawler list page scraping.
Reuses the singleton connection pool from crawlo.utils.db.mysql_connection_pool.

Usage Example:
```python
from crawlo.helpers.mysql_exists_checker import MySQLExistsChecker

class MySpider(Spider):
    async def start_requests(self):
        self.db_checker = MySQLExistsChecker.from_settings(self.settings)
    
    async def parse_list(self, response):
        exists = await self.db_checker.exists(
            "SELECT 1 FROM articles WHERE url = %s LIMIT 1",
            (url,)
        )
        if not exists:
            yield Request(url, callback=self.parse_detail)
    
    async def closed(self):
        await self.db_checker.close()
```

Author: Crawlo Team
Version: 0.2.0
"""
from typing import Any, Optional, List, Tuple

from crawlo.logging import get_logger
from crawlo.utils.db.mysql_connection_pool import get_mysql_pool, close_all_mysql_pools


class MySQLExistsChecker:
    """
    MySQL Data Existence Checker
    
    Reuses the singleton connection pool from mysql_connection_pool.
    """
    
    def __init__(self, config: dict):
        self._config = config
        self._closed = False
        self.logger = get_logger('MySQLExistsChecker')
    
    # 默认配置（单一定义，消除三处重复）
    _DEFAULTS = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': '', 'db': 'crawlo', 'minsize': 2, 'maxsize': 5,
    }
    # config key → settings key mapping
    _KEY_MAP = {
        'host': 'MYSQL_HOST', 'port': 'MYSQL_PORT', 'user': 'MYSQL_USER',
        'password': 'MYSQL_PASSWORD', 'db': 'MYSQL_DB',
        'minsize': 'MYSQL_POOL_MIN', 'maxsize': 'MYSQL_POOL_MAX',
    }

    # 数值类型 key（Settings 对象需用 get_int）
    _INT_KEYS = {'port', 'minsize', 'maxsize'}

    @classmethod
    def from_settings(cls, settings: Optional[Any] = None) -> 'MySQLExistsChecker':
        """Create checker from Crawlo settings"""
        if settings is None:
            return cls(dict(cls._DEFAULTS))

        config = {}
        for k, v in cls._DEFAULTS.items():
            settings_key = cls._KEY_MAP[k]
            if k in cls._INT_KEYS and hasattr(settings, 'get_int'):
                config[k] = settings.get_int(settings_key, v)
            else:
                config[k] = settings.get(settings_key, v) if hasattr(settings, 'get') else v
        return cls(config)
    
    async def _get_pool(self):
        """Get connection pool"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker has been closed")
        return await get_mysql_pool(**self._config)
    
    async def exists(self, sql: str, params: Optional[Tuple] = None) -> bool:
        """Check if data exists"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker has been closed")
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result is not None
    
    async def batch_exists(self, sql: str, params_list: List[Tuple]) -> List[bool]:
        """
        Batch check if data exists
        
        Note: Executes queries individually for each parameter set.
        For better performance, consider using a single query with IN clause.
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker has been closed")
        
        pool = await self._get_pool()
        results = []
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for params in params_list:
                    await cursor.execute(sql, params)
                    result = await cursor.fetchone()
                    results.append(result is not None)
        return results
    
    async def count(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Count records"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker has been closed")
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def close(self):
        """Close checker (does not close connection pool, managed by framework)"""
        self._closed = True
    
    @classmethod
    async def close_all(cls):
        """Close all connection pools (class method, called when spider ends)"""
        await close_all_mysql_pools()
    
    def is_closed(self) -> bool:
        """Check if closed"""
        return self._closed


async def check_exists(sql: str, params: Optional[Tuple] = None, settings: Optional[Any] = None) -> bool:
    """Quick check if data exists (one-time use)"""
    checker = MySQLExistsChecker.from_settings(settings)
    try:
        return await checker.exists(sql, params)
    finally:
        await checker.close()


__all__ = ['MySQLExistsChecker', 'check_exists']
