# -*- coding: utf-8 -*-
"""
SQLite Pipeline — 异步 SQLite 数据管道
========================================
继承 GenericSQLPipeline，实现 SQLite 专属逻辑。

特性：
- 单连接复用（无需连接池）
- 默认 INSERT OR IGNORE（避免自增 ID 变化）
- 配置 AUTO_UPDATE=True 时使用 INSERT OR REPLACE
- 事务默认关闭（SQLite 单写锁，并发下事务易超时）

依赖：aiosqlite>=0.19.0

设计文档：docs/internal/db-pipelines-design.md §3.1
"""

import asyncio
from pathlib import Path
from typing import List, Dict

import aiosqlite

from crawlo.db.dialect import SQLiteDialect
from crawlo.pipelines.generic_sql import GenericSQLPipeline


class SQLitePipeline(GenericSQLPipeline):
    """SQLite 管道实现"""

    _PREFIX = 'SQLITE'

    # ── 配置 ──

    def _init_config(self):
        """扩展配置 — SQLite 特有：路径 + 文件"""
        super()._init_config()
        self.db_path = Path(
            self.settings.get('SQLITE_PATH', 'data')
        ) / f"{self.settings.get('SQLITE_DB', 'crawlo')}.db"
        # SQLite 默认关闭事务（单写锁限制）
        self.use_transaction = self.settings.get_bool('SQLITE_USE_TRANSACTION', False)

    # ═══════════════════════════════════════════════
    # 连接管理（单连接，非连接池）
    # ═══════════════════════════════════════════════

    async def _initialize_pool(self):
        """创建 aiosqlite 单连接"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.pool = await aiosqlite.connect(str(self.db_path))
        # 启用 WAL 模式提升并发读取性能
        await self.pool.execute('PRAGMA journal_mode=WAL')
        self.logger.info(f"SQLite connected: {self.db_path}")

    async def _close_pool(self, pool):
        """关闭连接"""
        try:
            if pool:
                await pool.close()
                self.logger.info("SQLite connection closed")
        except Exception as e:
            self.logger.error(f"Close SQLite connection failed: {e}")

    # ═══════════════════════════════════════════════
    # Helper（SQLite 无需 Helper 层）
    # ═══════════════════════════════════════════════

    async def _create_helper(self):
        """SQLite 无需 Helper 层"""
        pass

    # ═══════════════════════════════════════════════
    # 表存在性检查
    # ═══════════════════════════════════════════════

    async def _check_table_exists(self):
        """检查表是否存在（sqlite_master）"""
        if not self.pool:
            return
        try:
            cursor = await self.pool.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (self.table_name,)
            )
            row = await cursor.fetchone()
            if not row:
                self.logger.warning(
                    f"Table not found: {self.table_name}. "
                    f"Will auto-create on first INSERT."
                )
            await cursor.close()
        except Exception as e:
            self.logger.warning(f"Table check failed: {e}")

    # ═══════════════════════════════════════════════
    # 单条 / 批量插入
    # ═══════════════════════════════════════════════

    async def _do_insert(self, data: Dict) -> int:
        """单条插入"""
        cols = list(data.keys())
        if self.auto_update:
            sql, params = SQLiteDialect.build_replace(self.table_name, data)
        elif self.insert_ignore:
            sql, params = SQLiteDialect.build_insert_ignore(self.table_name, data)
        else:
            sql = SQLiteDialect.build_insert(self.table_name, cols)
            params = tuple(data.values())

        cursor = await self.pool.execute(sql, params)
        await self.pool.commit()
        return cursor.rowcount

    async def _do_batch_insert(self, batch: List[Dict]) -> int:
        """批量插入（带事务）"""
        if not batch:
            return 0

        cols = list(batch[0].keys())

        if self.auto_update:
            sql, _ = SQLiteDialect.build_replace(
                self.table_name, batch[0]
            )
        elif self.insert_ignore:
            sql, _ = SQLiteDialect.build_insert_ignore(
                self.table_name, batch[0]
            )
        else:
            sql = SQLiteDialect.build_insert(self.table_name, cols)

        total = 0
        try:
            await self.pool.execute('BEGIN')
            for row in batch:
                params = tuple(row.get(col, '') for col in cols)
                cursor = await self.pool.execute(sql, params)
                total += cursor.rowcount
            await self.pool.commit()
        except Exception:
            await self.pool.rollback()
            raise
        return total

    async def _do_batch_insert_no_tx(self, batch: List[Dict]) -> int:
        """批量插入（无事务）"""
        if not batch:
            return 0

        cols = list(batch[0].keys())

        if self.auto_update:
            sql, _ = SQLiteDialect.build_replace(
                self.table_name, batch[0]
            )
        elif self.insert_ignore:
            sql, _ = SQLiteDialect.build_insert_ignore(
                self.table_name, batch[0]
            )
        else:
            sql = SQLiteDialect.build_insert(self.table_name, cols)

        params_list = [
            tuple(row.get(col, '') for col in cols)
            for row in batch
        ]
        cursor = await self.pool.executemany(sql, params_list)
        await self.pool.commit()
        return cursor.rowcount
