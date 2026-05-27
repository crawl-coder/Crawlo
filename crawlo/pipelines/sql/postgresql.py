# -*- coding: utf-8 -*-
"""
PostgreSQL Pipeline — 异步 PostgreSQL 数据管道
================================================
继承 GenericSQLPipeline，实现 PostgreSQL 专属逻辑。

特性：
- asyncpg 连接池
- ON CONFLICT (conflict_cols) DO UPDATE
- 必须配置 PG_CONFLICT_COLUMNS（与 MySQL 的自动唯一键检测不同）
- 占位符风格 $1, $2（使用 PostgreSQLDialect 管理）

依赖：asyncpg>=0.29.0

设计文档：docs/internal/db-pipelines-design.md §3.2
"""

import asyncio
from typing import List, Dict

from crawlo.db.dialect import PostgreSQLDialect
from crawlo.exceptions import PipelineInitError
from crawlo.pipelines.generic_sql import GenericSQLPipeline

# 尝试导入 asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False


class PostgreSQLPipeline(GenericSQLPipeline):
    """PostgreSQL 管道实现"""

    _PREFIX = 'PG'

    # ── 配置 ──

    def _init_config(self):
        """扩展配置 — PostgreSQL 特有：conflict_columns 必须配置"""

        if not ASYNCPG_AVAILABLE:
            raise ImportError(
                "asyncpg is required for PostgreSQLPipeline. "
                "Install: pip install asyncpg>=0.29.0"
            )

        super()._init_config()

        # PostgreSQL 必须配置冲突列（与 MySQL 自动检测唯一键不同）
        self.conflict_cols = self._parse_columns(
            self.settings.get('PG_CONFLICT_COLUMNS')
        )

        if not self.conflict_cols and not self.insert_ignore:
            raise PipelineInitError(
                "PG_CONFLICT_COLUMNS is required for PostgreSQLPipeline "
                "(PostgreSQL ON CONFLICT requires explicit column specification). "
                "Example: PG_CONFLICT_COLUMNS = ('id',)\n"
                "Or set PG_INSERT_IGNORE=True to use ON CONFLICT DO NOTHING."
            )

    # ═══════════════════════════════════════════════
    # 连接池
    # ═══════════════════════════════════════════════

    async def _initialize_pool(self):
        """创建 asyncpg 连接池"""
        self.pool = await asyncpg.create_pool(
            host=self.settings.get('PG_HOST', '127.0.0.1'),
            port=self.settings.get_int('PG_PORT', 5432),
            user=self.settings.get('PG_USER', 'postgres'),
            password=self.settings.get('PG_PASSWORD', ''),
            database=self.settings.get('PG_DB', 'crawlo'),
            min_size=self.settings.get_int('PG_POOL_MIN', 2),
            max_size=self.settings.get_int('PG_POOL_MAX', 10),
        )
        self.logger.debug("PostgreSQL connection pool initialized")

    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                await pool.close()
                self.logger.info("PostgreSQL pool closed")
        except Exception as e:
            self.logger.error(f"Close pool failed: {e}")

    # ═══════════════════════════════════════════════
    # Helper（PG 直接使用连接池，无需 Helper 层）
    # ═══════════════════════════════════════════════

    async def _create_helper(self):
        """PostgreSQL 直接使用连接池，无需 Helper 层"""
        pass

    # ═══════════════════════════════════════════════
    # 表存在性检查
    # ═══════════════════════════════════════════════

    async def _check_table_exists(self):
        """检查表是否存在（PostgreSQL information_schema）"""
        if not self.pool:
            return
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = $1",
                    self.table_name,
                )
                if not row:
                    self.logger.warning(f"Table not found: {self.table_name}")
        except Exception as e:
            self.logger.warning(f"Table check failed: {e}")

    # ═══════════════════════════════════════════════
    # 单条 / 批量插入（使用 PostgreSQLDialect 构建 SQL）
    # ═══════════════════════════════════════════════

    async def _do_insert(self, data: Dict) -> int:
        """单条插入"""
        if self.insert_ignore:
            sql, params = PostgreSQLDialect.build_insert_ignore(
                self.table_name, data
            )
        else:
            sql, params = PostgreSQLDialect.build_upsert(
                table=self.table_name,
                data=data,
                conflict_cols=self.conflict_cols,
                update_cols=self.update_columns,
            )

        async with self.pool.acquire() as conn:
            result = await conn.execute(sql, *params)
            # asyncpg 的 execute 返回 "INSERT 0 1" 格式字符串
            return 1

    async def _do_batch_insert(self, batch: List[Dict]) -> int:
        """批量事务插入"""
        if not batch:
            return 0

        cols = list(batch[0].keys())
        total = 0

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for data in batch:
                    if self.insert_ignore:
                        sql, params = PostgreSQLDialect.build_insert_ignore(
                            self.table_name, data
                        )
                    else:
                        sql, params = PostgreSQLDialect.build_upsert(
                            table=self.table_name,
                            data=data,
                            conflict_cols=self.conflict_cols,
                            update_cols=self.update_columns,
                        )
                    await conn.execute(sql, *params)
                    total += 1

        return total

    async def _do_batch_insert_no_tx(self, batch: List[Dict]) -> int:
        """批量无事务插入"""
        if not batch:
            return 0

        cols = list(batch[0].keys())
        total = 0

        async with self.pool.acquire() as conn:
            for data in batch:
                if self.insert_ignore:
                    sql, params = PostgreSQLDialect.build_insert_ignore(
                        self.table_name, data
                    )
                else:
                    sql, params = PostgreSQLDialect.build_upsert(
                        table=self.table_name,
                        data=data,
                        conflict_cols=self.conflict_cols,
                        update_cols=self.update_columns,
                    )
                await conn.execute(sql, *params)
                total += 1

        return total
