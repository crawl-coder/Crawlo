#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL 数据存在性检查工具
========================

用于在爬虫列表页采集时，提前判断数据是否已存在于数据库中。
复用 crawlo.utils.db.mysql_connection_pool 的单例连接池。

使用示例：
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

import asyncio
from typing import Any

from crawlo.logging import get_logger
from crawlo.utils.db.mysql_connection_pool import get_mysql_pool, close_all_mysql_pools


class MySQLExistsChecker:
    """
    MySQL 数据存在性检查器
    
    复用 mysql_connection_pool 的单例连接池。
    """
    
    def __init__(self, config: dict):
        self._config = config
        self._closed = False
        self.logger = get_logger('MySQLExistsChecker')
    
    @classmethod
    def from_settings(cls, settings: Any) -> 'MySQLExistsChecker':
        """从 Crawlo settings 创建检查器"""
        if settings is None:
            config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'db': 'crawlo',
                'minsize': 2,
                'maxsize': 5,
            }
        elif isinstance(settings, dict):
            config = {
                'host': settings.get('MYSQL_HOST', 'localhost'),
                'port': settings.get('MYSQL_PORT', 3306),
                'user': settings.get('MYSQL_USER', 'root'),
                'password': settings.get('MYSQL_PASSWORD', ''),
                'db': settings.get('MYSQL_DB', 'crawlo'),
                'minsize': settings.get('MYSQL_POOL_MIN', 2),
                'maxsize': settings.get('MYSQL_POOL_MAX', 5),
            }
        else:
            config = {
                'host': settings.get('MYSQL_HOST', 'localhost'),
                'port': settings.get_int('MYSQL_PORT', 3306),
                'user': settings.get('MYSQL_USER', 'root'),
                'password': settings.get('MYSQL_PASSWORD', ''),
                'db': settings.get('MYSQL_DB', 'crawlo'),
                'minsize': settings.get_int('MYSQL_POOL_MIN', 2),
                'maxsize': settings.get_int('MYSQL_POOL_MAX', 5),
            }
        
        return cls(config)
    
    async def _get_pool(self):
        """获取连接池"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        return await get_mysql_pool(**self._config)
    
    async def exists(self, sql: str, params: tuple = None) -> bool:
        """检查数据是否存在"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result is not None
    
    async def batch_exists(self, sql: str, params_list: list) -> list:
        """批量检查数据是否存在"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                all_params = [p for params in params_list for p in params]
                await cursor.execute(sql, all_params)
                results = await cursor.fetchall()
                existing = {r[0] for r in results}
                return [params[0] in existing for params in params_list]
    
    async def count(self, sql: str, params: tuple = None) -> int:
        """统计记录数"""
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def close(self):
        """关闭检查器（不关闭连接池，由框架统一管理）"""
        self._closed = True
    
    @classmethod
    async def close_all(cls):
        """关闭所有连接池（类方法，爬虫结束时调用）"""
        await close_all_mysql_pools()
    
    def is_closed(self) -> bool:
        """检查是否已关闭"""
        return self._closed


async def check_exists(sql: str, params: tuple = None, settings: Any = None) -> bool:
    """快速检查数据是否存在（一次性使用）"""
    checker = MySQLExistsChecker.from_settings(settings)
    try:
        return await checker.exists(sql, params)
    finally:
        await checker.close()


__all__ = ['MySQLExistsChecker', 'check_exists']
