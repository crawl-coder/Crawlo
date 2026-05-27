# -*- coding: utf-8 -*-
"""
HBase Pipeline — HBase 数据管道
================================
直接继承 ResourceManagedPipeline（不继承 GenericSQLPipeline）。

原因：HBase 不是 SQL/文档模型，API 完全不同。
- 列族 + rowkey 模型
- 同步 happybase 客户端（通过 run_in_executor 异步化）
- 无传统 UPSERT 语义（直接 put 覆盖）
- 批量使用 table.batch() 上下文管理器

依赖：happybase>=1.2.0

设计文档：docs/internal/db-pipelines-design.md §3.7
"""

import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path

from crawlo.logging import get_logger
from crawlo.items import Item
from crawlo.exceptions import ItemDiscard
from . import ResourceManagedPipeline

# 尝试导入 happybase
try:
    import happybase
    HBASE_AVAILABLE = True
except ImportError:
    HBASE_AVAILABLE = False


class HBasePipeline(ResourceManagedPipeline):
    """HBase 管道实现 — 直接继承 ResourceManagedPipeline"""

    _PREFIX = 'HBASE'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

        self._init_config()

        self._lock = asyncio.Lock()
        self._initialized = False
        self.connection: Optional[Any] = None
        self.table: Optional[Any] = None

    # ── 配置 ──

    def _init_config(self):
        """初始化配置"""
        if not HBASE_AVAILABLE:
            raise ImportError(
                "happybase is required for HBasePipeline. "
                "Install: pip install happybase>=1.2.0"
            )

        self.hbase_host = self.settings.get('HBASE_HOST', '127.0.0.1')
        self.hbase_port = self.settings.get_int('HBASE_PORT', 9090)
        self.table_name = self.settings.get(
            'HBASE_TABLE',
            getattr(self.crawler.spider, 'name', 'crawlo') + '_data',
        )
        self.column_family = self.settings.get('HBASE_COLUMN_FAMILY', 'cf')

        # 批量配置
        self.use_batch = self.settings.get_bool('HBASE_USE_BATCH', True)
        self.batch_size = max(1, self.settings.get_int('HBASE_BATCH_SIZE', 100))

    # ═══════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════

    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理数据项"""
        await self._ensure_initialized()

        if self.use_batch:
            return await self._add_to_batch(item, spider)
        return await self._put_single(item)

    async def _ensure_initialized(self):
        """确保已初始化"""
        if self._initialized and self.table is not None:
            return
        async with self._lock:
            if self._initialized:
                return
            await self._initialize_resources()
            self._initialized = True

    # ═══════════════════════════════════════════════
    # 资源初始化
    # ═══════════════════════════════════════════════

    async def _initialize_resources(self):
        """初始化 HBase 连接"""
        loop = asyncio.get_event_loop()

        # happybase 是同步库，通过 run_in_executor 包装
        def _connect():
            conn = happybase.Connection(
                host=self.hbase_host,
                port=self.hbase_port,
                timeout=self.settings.get_int('HBASE_TIMEOUT', 30000),
            )
            return conn

        self.connection = await loop.run_in_executor(None, _connect)

        # 获取表对象
        try:
            self.table = await loop.run_in_executor(
                None, lambda: self.connection.table(self.table_name)
            )
        except Exception:
            self.logger.warning(
                f"Table not found: {self.table_name}. "
                f"Ensure it exists with column family '{self.column_family}'."
            )

        self.logger.info(
            f"HBase connected: {self.hbase_host}:{self.hbase_port}, "
            f"table={self.table_name}, cf={self.column_family}"
        )

        # 注册资源
        self.register_resource(
            resource=self.connection,
            cleanup_func=self._close_connection,
            name='hbase_connection',
        )

    async def _close_connection(self, conn):
        """关闭 HBase 连接"""
        try:
            if conn:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, conn.close)
                self.logger.info("HBase connection closed")
        except Exception as e:
            self.logger.error(f"Close HBase failed: {e}")

    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider = getattr(self.crawler, 'spider', None)
            spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'
            self.logger.info(
                f"[{spider_name}] Flushing remaining {len(self.batch_buffer)} HBase rows"
            )
            await self._flush_batch(spider)
        self.batch_buffer.clear()
        self._initialized = False

    # ═══════════════════════════════════════════════
    # Rowkey 构建
    # ═══════════════════════════════════════════════

    def _build_rowkey(self, item: Item) -> bytes:
        """构建 HBase rowkey（子类可重写）"""
        import hashlib
        import json

        data = dict(item)
        return hashlib.md5(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
        ).hexdigest().encode()

    def _build_columns(self, item_dict: dict) -> dict:
        """构建列族:列名 -> 值映射"""
        cf = self.column_family
        return {
            f'{cf}:{col}': str(val) if val is not None else ''
            for col, val in item_dict.items()
        }

    # ═══════════════════════════════════════════════
    # 单行写入
    # ═══════════════════════════════════════════════

    async def _put_single(self, item: Item) -> Item:
        """单行写入"""
        try:
            item_dict = dict(item)
            rowkey = self._build_rowkey(item)
            columns = self._build_columns(item_dict)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.table.put(rowkey, columns)
            )

            self.crawler.stats.inc_value('hbase/success')
            return item
        except Exception as e:
            self.crawler.stats.inc_value('hbase/failed')
            self.logger.error(f"HBase put failed: {e}")
            raise ItemDiscard(f"HBase put failed: {e}")

    # ═══════════════════════════════════════════════
    # 批量写入
    # ═══════════════════════════════════════════════

    async def _add_to_batch(self, item: Item, spider) -> Item:
        """添加到批量缓冲区"""
        async with self._lock:
            self.batch_buffer.append(item)
            should_flush = len(self.batch_buffer) >= self.batch_size
        if should_flush:
            await self._flush_batch(spider)
        return item

    async def _flush_batch(self, spider):
        """刷新批量缓冲区"""
        spider_name = getattr(spider, 'name', str(spider)) if spider else 'unknown'

        async with self._lock:
            if not self.batch_buffer:
                return
            batch = self.batch_buffer[:]
            self.batch_buffer.clear()

        if not batch:
            return

        try:
            loop = asyncio.get_event_loop()

            def _batch_put():
                with self.table.batch(
                    batch_size=len(batch),
                    transaction=True,
                ) as b:
                    for item in batch:
                        item_dict = dict(item)
                        rowkey = self._build_rowkey(item)
                        columns = self._build_columns(item_dict)
                        b.put(rowkey, columns)

            await loop.run_in_executor(None, _batch_put)

            success_count = len(batch)
            self.crawler.stats.inc_value('hbase/batch_success')
            self.crawler.stats.inc_value('hbase/batch_rows', success_count)
            self.logger.info(
                f"[{spider_name}] HBase batch put: {success_count} rows"
            )
        except Exception as e:
            self.crawler.stats.inc_value('hbase/batch_failed')
            self.logger.error(
                f"[{spider_name}] HBase batch put failed: {e}"
            )
            raise ItemDiscard(f"HBase batch put failed: {e}")
