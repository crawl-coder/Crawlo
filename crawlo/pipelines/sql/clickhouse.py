# -*- coding: utf-8 -*-
"""
ClickHouse Pipeline — 异步 ClickHouse 数据管道
===============================================
继承 GenericSQLPipeline，实现 ClickHouse 专属逻辑。

特性：
- clickhouse-connect 异步客户端
- 默认启用批量模式 (USE_BATCH=True, BATCH_SIZE=10000)
- 强制关闭事务（ClickHouse 不支持传统事务）
- UPSERT 依赖 ReplacingMergeTree 引擎后台去重
- 单条插入记录 WARNING（推荐始终使用批量路径）

依赖：clickhouse-connect>=0.7.0

设计文档：docs/internal/db-pipelines-design.md §3.3
"""

import asyncio
from typing import List, Dict, Optional

from crawlo.pipelines.generic_sql import GenericSQLPipeline

# 尝试导入 clickhouse-connect
try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False


class ClickHousePipeline(GenericSQLPipeline):
    """ClickHouse 管道实现"""

    _PREFIX = 'CLICKHOUSE'

    # ── 配置 ──

    def _init_config(self):
        """扩展配置 — ClickHouse 特有：批量优先 + 关闭事务"""

        if not CLICKHOUSE_AVAILABLE:
            raise ImportError(
                "clickhouse-connect is required for ClickHousePipeline. "
                "Install: pip install clickhouse-connect>=0.7.0"
            )

        super()._init_config()

        # ClickHouse 默认启用批量（处理大批量数据）
        if not self.use_batch:
            self.use_batch = self.settings.get_bool('CLICKHOUSE_USE_BATCH', True)
            self.batch_size = max(
                1, self.settings.get_int('CLICKHOUSE_BATCH_SIZE', 10000)
            )

        # 强制关闭事务（ClickHouse 不支持传统事务）
        self.use_transaction = False

        # UPSERT 模式
        self.upsert_mode = self.settings.get(
            'CLICKHOUSE_UPSERT_MODE', 'replacing'
        )

    # ═══════════════════════════════════════════════
    # 连接管理
    # ═══════════════════════════════════════════════

    async def _initialize_pool(self):
        """创建 clickhouse-connect 客户端"""
        host = self.settings.get('CLICKHOUSE_HOST', '127.0.0.1')
        port = self.settings.get_int('CLICKHOUSE_PORT', 8123)
        database = self.settings.get('CLICKHOUSE_DB', 'crawlo')
        username = self.settings.get('CLICKHOUSE_USER', 'default')
        password = self.settings.get('CLICKHOUSE_PASSWORD', '')

        # clickhouse-connect 使用同步客户端，通过 run_in_executor 包装连接
        loop = asyncio.get_event_loop()
        self.pool = await loop.run_in_executor(
            None,
            lambda: clickhouse_connect.get_client(
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
            )
        )
        self.logger.info(f"ClickHouse connected: {host}:{port}/{database}")

    async def _close_pool(self, pool):
        """关闭客户端"""
        try:
            if pool:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, pool.close)
                self.logger.info("ClickHouse client closed")
        except Exception as e:
            self.logger.error(f"Close ClickHouse failed: {e}")

    # ═══════════════════════════════════════════════
    # Helper（ClickHouse 无需 Helper 层）
    # ═══════════════════════════════════════════════

    async def _create_helper(self):
        """ClickHouse 无需 Helper 层"""
        pass

    # ═══════════════════════════════════════════════
    # 表存在性检查
    # ═══════════════════════════════════════════════

    async def _check_table_exists(self):
        """检查表是否存在（system.tables）"""
        if not self.pool:
            return
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.pool.query(
                    "SELECT 1 FROM system.tables "
                    "WHERE database = currentDatabase() AND name = %(name)s",
                    parameters={'name': self.table_name},
                )
            )
            if not result.result_rows:
                self.logger.warning(f"Table not found: {self.table_name}")
        except Exception as e:
            self.logger.warning(f"Table check failed: {e}")

    # ═══════════════════════════════════════════════
    # 单条 / 批量插入
    # ═══════════════════════════════════════════════

    async def _do_insert(self, data: Dict) -> int:
        """单条插入（记录 WARNING，推荐使用批量路径）"""
        self.logger.warning(
            "Single insert is not recommended for ClickHouse. "
            "Please enable USE_BATCH=True in settings."
        )
        return await self._insert_rows([list(data.values())], [list(data.keys())])

    async def _do_batch_insert(self, batch: List[Dict]) -> int:
        """批量事务插入 — 实际上无事务"""
        return await self._do_batch_insert_no_tx(batch)

    async def _do_batch_insert_no_tx(self, batch: List[Dict]) -> int:
        """批量插入（ClickHouse 核心路径）"""
        if not batch:
            return 0

        cols = list(batch[0].keys())
        rows = [[row.get(col, '') for col in cols] for row in batch]

        return await self._insert_rows(rows, cols)

    async def _insert_rows(self, rows: List, columns: List[str]) -> int:
        """通用行插入（通过 run_in_executor）"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.pool.insert(
                table=self.table_name,
                data=rows,
                column_names=columns,
            )
        )
        return len(rows)
