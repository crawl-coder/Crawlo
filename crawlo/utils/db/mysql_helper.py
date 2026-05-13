#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo MySQL 通用工具
====================
提供高性能的 MySQL 查询和操作接口，支持单例模式避免重复实例化。

使用场景：
- 爬虫中检查数据是否已采集
- 批量数据插入和更新
- 事务操作

特性：
- 单例模式避免重复实例化
- 自动复用框架连接池
- 支持查询和写入操作
- 批量操作优化
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import asynccontextmanager
from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager
from crawlo.utils.db.sql_builder import SQLBuilder
from crawlo.logging import get_logger
from crawlo.settings.setting_manager import SettingManager
import asyncio
import warnings


class MySQLHelper:
    """
    MySQL 通用操作助手（非单例模式）
    
    与 Crawlo 框架深度集成，连接池由 MySQLConnectionPoolManager 统一管理复用。
    """
    
    def __init__(self, settings: Optional[Dict] = None):
        """
        初始化
        
        Args:
            settings: Crawlo 配置对象
        """
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)
        self._pool = None
        self._sql_builder = SQLBuilder()
        self._lock = None  # 实例级别的锁
    
    @classmethod
    async def get_instance(cls, settings=None) -> 'MySQLHelper':
        """获取实例（非单例，每次创建新实例，但连接池会被复用）"""
        return cls(settings)
    
    async def _get_pool(self):
        """懒加载连接池"""
        if self._pool is None:
            # 初始化实例级别的锁
            if self._lock is None:
                self._lock = asyncio.Lock()
            
            # 使用 MySQLConnectionPoolManager.get_pool() 获取连接池
            self._pool = await MySQLConnectionPoolManager.get_pool(
                host=self.settings.get('MYSQL_HOST', 'localhost') if self.settings else 'localhost',
                port=self.settings.get('MYSQL_PORT', 3306) if self.settings else 3306,
                user=self.settings.get('MYSQL_USER', 'root') if self.settings else 'root',
                password=self.settings.get('MYSQL_PASSWORD', '') if self.settings else '',
                db=self.settings.get('MYSQL_DB', 'crawlo') if self.settings else 'crawlo',
                minsize=self.settings.get('MYSQL_POOL_MIN', 2) if self.settings else 2,
                maxsize=self.settings.get('MYSQL_POOL_MAX', 5) if self.settings else 5,
                shared=True
            )
        return self._pool
    
    # ==================== 查询操作 ====================
    
    async def exists(
        self,
        table: str,
        conditions: Dict[str, Any],
        db: Optional[str] = None
    ) -> bool:
        """
        检查数据是否存在（最常用）
        
        Args:
            table: 表名
            conditions: 条件字典，如 {"url": "http://...", "status": 1}
            db: 数据库名
            
        Returns:
            bool: 是否存在
            
        Example:
            helper = await MySQLHelper.get_instance()
            exists = await helper.exists("articles", {"url": item["url"]})
        """
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        where_clauses = []
        params = []
        
        for column, value in conditions.items():
            # 支持操作符
            if "__" in column:
                col, op = column.split("__", 1)
                operator = self._get_operator(op)
                where_clauses.append(f"`{col}` {operator} %s")
            else:
                where_clauses.append(f"`{column}` = %s")
            params.append(value)
        
        where_sql = " AND ".join(where_clauses)
        sql = f"SELECT 1 FROM {table_name} WHERE {where_sql} LIMIT 1"
        
        return await self._execute_exists(sql, params)
    
    async def fetch_one(
        self,
        sql: str,
        params: Optional[Union[List, Tuple]] = None
    ) -> Optional[Dict]:
        """
        查询单条数据
        
        Args:
            sql: SQL 查询语句
            params: SQL 参数
            
        Returns:
            dict: 数据字典，不存在返回 None
        """
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params or [])
                result = await cursor.fetchone()
                
                if result is None:
                    return None
                
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
    
    async def fetch_all(
        self,
        sql: str,
        params: Optional[Union[List, Tuple]] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        查询多条数据
        
        Args:
            sql: SQL 查询语句
            params: SQL 参数
            limit: 最大返回条数
            
        Returns:
            list: 数据字典列表
        """
        if limit and "LIMIT" not in sql.upper():
            sql = sql.strip().rstrip(";") + f" LIMIT {limit}"
        
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params or [])
                results = await cursor.fetchall()
                
                if not results:
                    return []
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
    
    async def count(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None,
        db: Optional[str] = None
    ) -> int:
        """
        统计记录数
        
        Args:
            table: 表名
            conditions: 条件字典
            db: 数据库名
            
        Returns:
            int: 记录数
        """
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        if conditions:
            where_clauses = []
            params = []
            for column, value in conditions.items():
                where_clauses.append(f"`{column}` = %s")
                params.append(value)
            where_sql = " WHERE " + " AND ".join(where_clauses)
        else:
            where_sql = ""
            params = []
        
        sql = f"SELECT COUNT(*) as count FROM {table_name}{where_sql}"
        
        result = await self.fetch_one(sql, params)
        return result["count"] if result else 0
    
    # ==================== 写入操作 ====================
    
    async def insert(
        self,
        table: str,
        data: Dict[str, Any],
        auto_update: bool = False,
        update_columns: Tuple = (),
        insert_ignore: bool = False,
        db: Optional[str] = None
    ) -> int:
        """
        插入数据
        
        Args:
            table: 表名
            data: 数据字典
            auto_update: 是否使用 REPLACE INTO
            update_columns: 冲突时更新的列
            insert_ignore: 是否忽略重复
            db: 数据库名
            
        Returns:
            int: 影响的行数
        """
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        # 复用 db_helper 的 SQLBuilder
        sql, params = self._sql_builder.make_insert(
            table_name.strip("`"),
            data,
            auto_update=auto_update,
            update_columns=update_columns,
            insert_ignore=insert_ignore
        )
        
        return await self._execute_write(sql, params)
    
    async def insert_many(
        self,
        table: str,
        datas: List[Dict[str, Any]],
        auto_update: bool = False,
        update_columns: Tuple = (),
        insert_ignore: bool = False,
        batch_size: int = 100,
        db: Optional[str] = None
    ) -> int:
        """
        批量插入数据
        
        Args:
            table: 表名
            datas: 数据字典列表
            auto_update: 是否使用 REPLACE INTO
            update_columns: 冲突时更新的列
            insert_ignore: 是否忽略重复
            batch_size: 每批插入数量
            db: 数据库名
            
        Returns:
            int: 影响的行数
        """
        if not datas:
            return 0
        
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        table_key = table_name.strip("`")  # SQLBuilder 不需要反引号
        total_affected = 0
        
        # 分批处理
        for i in range(0, len(datas), batch_size):
            batch = datas[i:i + batch_size]
            
            # 使用 SQLBuilder 构建批量插入 SQL
            result = self._sql_builder.make_batch(
                table_key,
                batch,
                auto_update=auto_update,
                update_columns=update_columns,
                insert_ignore=insert_ignore
            )
            
            if result is None:
                continue
                
            sql, params = result
            affected = await self._execute_write(sql, params)
            total_affected += affected
        
        return total_affected
    
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        conditions: Dict[str, Any],
        db: Optional[str] = None
    ) -> int:
        """
        更新数据
        
        Args:
            table: 表名
            data: 要更新的数据
            conditions: 更新条件
            db: 数据库名
            
        Returns:
            int: 影响的行数
        """
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        # 构建 SET 子句
        set_clauses = []
        params = []
        for column, value in data.items():
            set_clauses.append(f"`{column}` = %s")
            params.append(value)
        
        # 构建 WHERE 子句
        where_clauses = []
        for column, value in conditions.items():
            where_clauses.append(f"`{column}` = %s")
            params.append(value)
        
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        
        return await self._execute_write(sql, params)
    
    async def delete(
        self,
        table: str,
        conditions: Dict[str, Any],
        db: Optional[str] = None
    ) -> int:
        """
        删除数据
        
        Args:
            table: 表名
            conditions: 删除条件
            db: 数据库名
            
        Returns:
            int: 影响的行数
        """
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        where_clauses = []
        params = []
        for column, value in conditions.items():
            where_clauses.append(f"`{column}` = %s")
            params.append(value)
        
        sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_clauses)}"
        
        return await self._execute_write(sql, params)
    
    # ==================== 事务支持 ====================
    
    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器
        
        Example:
            async with mysql_helper.transaction() as cursor:
                await cursor.execute("INSERT INTO ...")
                await cursor.execute("UPDATE ...")
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await conn.begin()
                    yield cursor
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise e
    
    # ==================== 批量操作优化 ====================
    
    async def bulk_check_exists(
        self,
        table: str,
        keys: List[Dict[str, Any]],
        db: Optional[str] = None
    ) -> List[bool]:
        """
        批量检查数据是否存在（性能优化）
        
        Args:
            table: 表名
            keys: 条件列表，如 [{"url": "http://1.com"}, {"url": "http://2.com"}]
            db: 数据库名
            
        Returns:
            List[bool]: 每条记录是否存在
        """
        if not keys:
            return []
        
        # 使用 IN 查询优化
        table_name = f"`{db}`.`{table}`" if db else f"`{table}`"
        
        # 假设所有 key 的结构相同
        first_key = keys[0]
        columns = list(first_key.keys())
        
        if len(columns) == 1:
            # 单列 IN 查询
            col = columns[0]
            values = [k[col] for k in keys]
            placeholders = ", ".join(["%s"] * len(values))
            sql = f"SELECT `{col}` FROM {table_name} WHERE `{col}` IN ({placeholders})"
            
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(sql, values)
                    results = await cursor.fetchall()
                    existing = {r[0] for r in results}
                    return [k[col] in existing for k in keys]
        else:
            # 多列情况，逐个查询
            results = []
            for key in keys:
                exists = await self.exists(table, key, db)
                results.append(exists)
            return results
    
    # ==================== 私有方法 ====================
    
    async def _execute_exists(self, sql: str, params: List) -> bool:
        """执行存在性检查"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                result = await cursor.fetchone()
                return result is not None
    
    async def _execute_write(self, sql: str, params: List) -> int:
        """执行写入操作"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params)
                await conn.commit()
                return cursor.rowcount
    
    def _get_operator(self, op: str) -> str:
        """获取操作符"""
        operators = {
            "eq": "=",
            "ne": "!=",
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
            "like": "LIKE",
            "in": "IN",
        }
        return operators.get(op, "=")


# ==================== 便捷函数（已废弃，请直接使用 MySQLHelper） ====================

def get_mysql_helper(settings=None, spider=None) -> MySQLHelper:
    """
    获取 MySQLHelper 实例（已废弃）
    
    ⚠️ 此函数已废弃，请直接使用 MySQLHelper.get_instance()
    
    Args:
        settings: 配置对象 (SettingManager)
        spider: spider 对象，可选。如果传入 spider，会自动从中获取配置：
            - spider.custom_settings 获取配置（优先）
            - spider.crawler.settings 获取数据库配置（作为后备）
    
    Returns:
        MySQLHelper 实例
    
    Example:
        # 推荐方式：直接使用 MySQLHelper
        helper = await MySQLHelper.get_instance(settings)
        
        # 或使用 get_mysql_helper（已废弃）
        helper = await get_mysql_helper(settings)
    """
    warnings.warn(
        "get_mysql_helper() is deprecated, use MySQLHelper.get_instance() instead",
        DeprecationWarning,
        stacklevel=2
    )
    
    async def _get_instance():
        # 如果传入 spider，尝试从中获取配置
        if spider is not None:
            # 检查是否有 custom_settings
            custom_settings = getattr(spider, 'custom_settings', None)
            
            # 从 spider.crawler.settings 获取数据库配置
            crawler_settings = getattr(spider, 'crawler', None)
            
            # 如果 spider 有 crawler.settings 或 custom_settings，合并配置
            if crawler_settings and hasattr(crawler_settings, 'settings'):
                if settings is None:
                    # SettingManager 已在顶部导入
                    settings = SettingManager()
                
                # 复制 crawler settings 作为基础配置
                for key in ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 
                           'MYSQL_DB', 'MYSQL_POOL_MIN', 'MYSQL_POOL_MAX', 'MYSQL_ECHO']:
                    if crawler_settings.settings.get(key):
                        settings.set(key, crawler_settings.settings.get(key))
            
            # 如果有 custom_settings，覆盖配置
            if custom_settings:
                if settings is None:
                    # SettingManager 已在顶部导入
                    settings = SettingManager()
                for key, value in custom_settings.items():
                    settings.set(key, value)
        
        return await MySQLHelper.get_instance(settings)
    
    return _get_instance()


async def check_exists(
    table: str,
    conditions: Dict[str, Any],
    settings=None
) -> bool:
    """
    快速检查数据是否存在（已废弃）
    
    ⚠️ 此函数已废弃，请直接使用 MySQLHelper 实例的 exists() 方法
    
    Example:
        # 推荐方式：使用 MySQLHelper 实例
        helper = await MySQLHelper.get_instance(settings)
        exists = await helper.exists("articles", {"url": item["url"]})
    """
    warnings.warn(
        "check_exists() is deprecated, use MySQLHelper.exists() instead",
        DeprecationWarning,
        stacklevel=2
    )
    helper = await MySQLHelper.get_instance(settings)
    return await helper.exists(table, conditions)
