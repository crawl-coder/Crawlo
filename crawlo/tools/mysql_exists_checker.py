#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL 数据存在性检查工具
========================

用于在爬虫列表页采集时，提前判断数据是否已存在于数据库中。

使用示例：
```python
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker

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
from typing import Any, Dict, Optional

# asyncmy 驱动导入
try:
    from asyncmy import create_pool
    ASYNCMY_AVAILABLE = True
except ImportError:
    create_pool = None
    ASYNCMY_AVAILABLE = False

from crawlo.logging import get_logger


# ============================================================
# 模块级连接池（单例）
# ============================================================

_pool: Optional[Any] = None
_pool_config: Optional[Dict] = None
_pool_lock = asyncio.Lock()


async def _get_pool(config: Dict[str, Any]) -> Any:
    """获取或创建连接池（单例）"""
    global _pool, _pool_config
    
    # 配置相同，直接返回现有连接池
    if _pool is not None and _pool_config == config:
        return _pool
    
    async with _pool_lock:
        # 双重检查
        if _pool is not None and _pool_config == config:
            return _pool
        
        if not ASYNCMY_AVAILABLE:
            raise RuntimeError(
                "asyncmy 不可用，请安装: pip install asyncmy"
            )
        
        _pool = await create_pool(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            db=config['db'],
            minsize=config.get('minsize', 2),
            maxsize=config.get('maxsize', 5),
        )
        _pool_config = config.copy()
        
        logger = get_logger('MySQLExistsChecker')
        logger.debug(f"连接池已创建: {config['host']}:{config['port']}")
        
        return _pool


async def _close_pool():
    """关闭连接池"""
    global _pool, _pool_config
    
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        _pool_config = None
        get_logger('MySQLExistsChecker').debug("连接池已关闭")


# ============================================================
# MySQLExistsChecker
# ============================================================

class MySQLExistsChecker:
    """
    MySQL 数据存在性检查器
    
    用于快速检查数据库中是否存在满足条件的记录。
    连接池在整个爬虫生命周期内复用。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化检查器
        
        Args:
            config: 数据库配置
                   {
                       'host': 'localhost',
                       'port': 3306,
                       'user': 'root',
                       'password': '',
                       'db': 'crawlo',
                       'minsize': 2,
                       'maxsize': 5,
                   }
        """
        self._config = config
        self._closed = False
        self.logger = get_logger('MySQLExistsChecker')
    
    @classmethod
    def from_settings(cls, settings: Any) -> 'MySQLExistsChecker':
        """
        从 Crawlo settings 创建检查器
        
        Args:
            settings: Crawlo 配置对象（支持 Settings 类或 dict）
        """
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
            # Settings 对象
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
    
    async def exists(self, sql: str, params: tuple = None) -> bool:
        """
        检查数据是否存在
        
        Args:
            sql: SQL 查询语句（使用 LIMIT 1）
            params: SQL 参数元组（可选）
        
        Returns:
            bool: 是否存在
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await _get_pool(self._config)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result is not None
    
    async def batch_exists(self, sql: str, params_list: list) -> list:
        """
        批量检查数据是否存在
        
        Args:
            sql: SQL 查询语句（使用 IN 占位符）
            params_list: 参数列表，如 [("url1",), ("url2",)]
        
        Returns:
            list: 每个参数的存在性结果
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await _get_pool(self._config)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                all_params = [p for params in params_list for p in params]
                await cursor.execute(sql, all_params)
                results = await cursor.fetchall()
                existing = {r[0] for r in results}
                return [params[0] in existing for params in params_list]
    
    async def count(self, sql: str, params: tuple = None) -> int:
        """
        统计记录数
        
        Args:
            sql: SQL 查询语句
            params: SQL 参数元组（可选）
        
        Returns:
            int: 记录数量
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭")
        
        pool = await _get_pool(self._config)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def close(self):
        """关闭检查器，统一关闭连接池"""
        if self._closed:
            return
        
        self._closed = True
        await _close_pool()
        self.logger.debug("MySQLExistsChecker 已关闭")
    
    def is_closed(self) -> bool:
        """检查是否已关闭"""
        return self._closed


# 便捷函数
async def check_exists(
    sql: str,
    params: tuple = None,
    settings: Any = None
) -> bool:
    """
    快速检查数据是否存在（一次性使用）
    
    Args:
        sql: SQL 查询语句
        params: SQL 参数元组（可选）
        settings: Crawlo 配置对象（可选）
    
    Returns:
        bool: 是否存在
    """
    checker = MySQLExistsChecker.from_settings(settings)
    try:
        return await checker.exists(sql, params)
    finally:
        await checker.close()


__all__ = ['MySQLExistsChecker', 'check_exists']
