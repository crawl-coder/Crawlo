# -*- coding: utf-8 -*-
"""
MongoDB Pipeline — 异步 MongoDB 数据管道
=========================================
继承 GenericDocumentPipeline，实现 MongoDB 专属逻辑。

特性：
- motor AsyncIOMotorClient（全局共享连接池）
- update_one(upsert=True) 语义
- 批量 bulk_write
- 失败数据保存到文件

Breaking Change (v2.0):
  旧行为：insert_one（重复跳过）
  新行为：update_one(upsert=True）（重复覆盖）
  兼容配置：MONGO_DEDUPLICATE_MODE = 'upsert'(默认) | 'insert'(旧行为)

设计文档：docs/internal/db-pipelines-design.md §3.5
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from pymongo.errors import PyMongoError, BulkWriteError

from crawlo.exceptions import ItemDiscard
from crawlo.utils.db.mongo_connection_pool import MongoConnectionPoolManager
from crawlo.pipelines.generic_doc import GenericDocumentPipeline


class MongoPipeline(GenericDocumentPipeline):
    """MongoDB 管道实现"""

    _PREFIX = 'MONGO'

    # ── 配置 ──

    def __init__(self, crawler):
        super().__init__(crawler)
        # MongoDB 特有字段
        self.db = None
        self.collection = None
        # 为批量刷新添加专用锁（防止并发 flush 竞争）
        self._flush_lock = asyncio.Lock()

    def _init_config(self):
        """扩展配置"""
        super()._init_config()

        # 连接参数
        self.mongo_uri = self.settings.get(
            'MONGO_URI', 'mongodb://localhost:27017'
        )
        self.db_name = self.settings.get(
            'MONGO_DB',
            self.settings.get('MONGO_DATABASE', 'crawlo_db'),
        )
        self.collection_name = self.settings.get(
            'MONGO_COLLECTION',
            getattr(self.crawler.spider, 'name', 'crawlo_data'),
        )

        # 连接池
        self.max_pool_size = self.settings.get_int('MONGO_MAX_POOL_SIZE', 100)
        self.min_pool_size = self.settings.get_int('MONGO_MIN_POOL_SIZE', 10)
        self.connect_timeout_ms = self.settings.get_int('MONGO_CONNECT_TIMEOUT_MS', 5000)
        self.socket_timeout_ms = self.settings.get_int('MONGO_SOCKET_TIMEOUT_MS', 30000)

        # 去重模式：'upsert'(覆盖) | 'insert'(跳过)
        self.deduplicate_mode = self.settings.get(
            'MONGO_DEDUPLICATE_MODE', 'upsert'
        )

    # ═══════════════════════════════════════════════
    # 资源初始化
    # ═══════════════════════════════════════════════

    async def _initialize_resources(self):
        """初始化 MongoDB 连接"""
        self.client = await MongoConnectionPoolManager.get_client(
            mongo_uri=self.mongo_uri,
            db_name=self.db_name,
            max_pool_size=self.max_pool_size,
            min_pool_size=self.min_pool_size,
            connect_timeout_ms=self.connect_timeout_ms,
            socket_timeout_ms=self.socket_timeout_ms,
        )
        if self.client is not None:
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.logger.info(
                f"MongoDB connected: db={self.db_name}, "
                f"collection={self.collection_name}, "
                f"deduplicate_mode={self.deduplicate_mode}"
            )

        # 注册客户端（但 MongoDB 使用全局单例，不在此处关闭）
        # 由 mongo_connection_pool.close_all_mongo_clients() 统一管理

        await self._check_collection_exists()

    async def _check_collection_exists(self):
        """检查集合是否存在"""
        if not self.client or not self.db:
            return
        try:
            collections = await self.db.list_collection_names()
            if self.collection_name not in collections:
                self.logger.info(
                    f"Collection '{self.collection_name}' will be auto-created."
                )
        except Exception as e:
            self.logger.warning(f"Collection check failed: {e}")

    async def _close_client(self, client):
        """MongoDB 使用全局共享连接池，不在此处关闭"""
        pass

    # ═══════════════════════════════════════════════
    # 单文档 upsert
    # ═══════════════════════════════════════════════

    async def _do_upsert(self, doc: dict) -> int:
        """单文档 upsert"""
        if self.deduplicate_mode == 'insert':
            # 旧行为：insert_one（重复跳过）
            try:
                await self.collection.insert_one(doc)
                return 1
            except Exception:
                # DuplicateKeyError 等忽略
                return 0
        else:
            # 新行为：update_one(upsert=True)
            doc_id = self._compute_doc_id(doc)
            result = await self.collection.update_one(
                {'_id': doc_id},
                {'$set': doc},
                upsert=True,
            )
            return 1

    # ═══════════════════════════════════════════════
    # 批量 upsert
    # ═══════════════════════════════════════════════

    async def _do_batch_upsert(self, docs: List[dict]) -> int:
        """批量文档 upsert"""

        from pymongo import UpdateOne

        if self.deduplicate_mode == 'insert':
            # 旧行为：insert_many（重复跳过）
            try:
                result = await self.collection.insert_many(docs, ordered=False)
                return len(result.inserted_ids)
            except BulkWriteError as bwe:
                inserted = bwe.details.get('nInserted', 0)
                self.logger.warning(
                    f"Batch insert partial success: {inserted}/{len(docs)}"
                )
                return inserted
        else:
            # 新行为：bulk_write with UpdateOne(upsert=True)
            operations = [
                UpdateOne(
                    {'_id': self._compute_doc_id(doc)},
                    {'$set': doc},
                    upsert=True,
                )
                for doc in docs
            ]
            result = await self.collection.bulk_write(operations, ordered=False)
            return result.upserted_count + result.modified_count

    # ═══════════════════════════════════════════════
    # 批量刷新（带双重锁保护）
    # ═══════════════════════════════════════════════

    async def _flush_batch(self, spider):
        """刷新批量缓冲区（带双重锁）"""
        if not self.batch_buffer:
            return

        async with self._flush_lock:
            if not self.batch_buffer:
                return

            batch = self.batch_buffer[:]
            self.batch_buffer.clear()

        if not batch:
            return

        await super()._flush_batch(spider)

    # ═══════════════════════════════════════════════
    # 清理
    # ═══════════════════════════════════════════════

    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider = getattr(self.crawler, 'spider', None)
            spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'
            self.logger.info(
                f"[{spider_name}] Flushing remaining {len(self.batch_buffer)} Mongo docs"
            )
            await self._flush_batch(spider)
        self.batch_buffer.clear()
        self._initialized = False
        # MongoDB 使用全局共享连接池，不在此处关闭
