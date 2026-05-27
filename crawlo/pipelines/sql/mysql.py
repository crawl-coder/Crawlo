# -*- coding: utf-8 -*-
"""
MySQL Pipeline - 异步 MySQL 数据管道
====================================

继承 GenericSQLPipeline，只需实现 MySQL 专属逻辑：
- 连接池初始化 (aiomysql)
- 表存在性检查 (information_schema)
- 单条/批量插入 (委托 MySQLHelper)

GenericSQLPipeline 提供：批量缓冲、重试、降级、事务控制、错误分类、统计记录。
"""
import asyncio
from typing import List, Dict

from crawlo.utils.db.mysql_helper import MySQLHelper
from crawlo.utils.db.mysql_connection_pool import (
    MySQLConnectionPoolManager,
    is_pool_active
)
from crawlo.pipelines.generic_sql import GenericSQLPipeline


class MySQLPipeline(GenericSQLPipeline):
    """MySQL 管道实现"""

    _PREFIX = 'MYSQL'

    # ═══════════════════════════════════════════════
    # 连接池
    # ═══════════════════════════════════════════════

    async def _initialize_pool(self):
        """创建 aiomysql 连接池"""
        self.pool = await MySQLConnectionPoolManager.get_pool(
            host=self.settings.get('MYSQL_HOST', 'localhost'),
            port=self.settings.get_int('MYSQL_PORT', 3306),
            user=self.settings.get('MYSQL_USER', 'root'),
            password=self.settings.get('MYSQL_PASSWORD', ''),
            db=self.settings.get('MYSQL_DB', 'crawlo_db'),
            minsize=self.settings.get_int('MYSQL_POOL_MIN', 3),
            maxsize=self.settings.get_int('MYSQL_POOL_MAX', 10),
        )
        self.logger.debug("MySQL connection pool initialized")

    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                pool.close()
                await pool.wait_closed()
                self.logger.debug("MySQL pool closed")
        except Exception as e:
            self.logger.error(f"Close pool failed: {e}")

    async def _ensure_initialized(self):
        """确保已初始化（含连接池活性检查）"""
        if self._initialized and self.pool and is_pool_active(self.pool):
            return
        async with self._lock:
            if self._initialized and self.pool and is_pool_active(self.pool):
                return
            await self._initialize_resources()
            self._initialized = True
            self.logger.debug("MySQL Pipeline resources initialized")

    # ═══════════════════════════════════════════════
    # Helper
    # ═══════════════════════════════════════════════

    async def _create_helper(self):
        """创建 MySQLHelper 实例"""
        self._helper = await MySQLHelper.get_instance(self.settings)
        self.logger.debug("MySQL helper initialized")

    # ═══════════════════════════════════════════════
    # 表存在性检查
    # ═══════════════════════════════════════════════

    async def _check_table_exists(self):
        """检查表是否存在（MySQL information_schema）"""
        if not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = DATABASE() AND table_name = %s",
                        (self.table_name,)
                    )
                    if not await cur.fetchone():
                        self.logger.warning(f"Table not found: {self.table_name}")
        except Exception as e:
            self.logger.warning(f"Table check failed: {e}")

    # ═══════════════════════════════════════════════
    # 单条 / 批量插入（委托 MySQLHelper）
    # ═══════════════════════════════════════════════

    async def _do_insert(self, data: Dict) -> int:
        """单条插入"""
        return await self._helper.insert(
            table=self.table_name,
            data=data,
            auto_update=self.auto_update,
            update_columns=self.update_columns,
            insert_ignore=self.insert_ignore
        )

    async def _do_batch_insert(self, batch: List[Dict]) -> int:
        """批量事务插入"""
        async with self._helper.transaction() as cursor:
            sql, params = self._helper._sql_builder.make_batch(
                self.table_name, batch,
                auto_update=self.auto_update,
                update_columns=self.update_columns,
                insert_ignore=self.insert_ignore
            )
            if sql is None:
                return 0
            await cursor.execute(sql, params)
            return cursor.rowcount

    async def _do_batch_insert_no_tx(self, batch: List[Dict]) -> int:
        """批量无事务插入"""
        return await self._helper.insert_many(
            table=self.table_name,
            datas=batch,
            auto_update=self.auto_update,
            update_columns=self.update_columns,
            insert_ignore=self.insert_ignore,
            batch_size=len(batch)
        )
