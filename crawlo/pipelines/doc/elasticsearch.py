# -*- coding: utf-8 -*-
"""
Elasticsearch Pipeline — 异步 Elasticsearch 数据管道
======================================================
继承 GenericDocumentPipeline，实现 Elasticsearch 专属逻辑。

特性：
- elasticsearch.AsyncElasticsearch 客户端
- 文档 ID 使用确定性 MD5 指纹（禁止使用 hash(item)）
- index() 自带 upsert 语义（相同 _id 覆盖）
- 批量使用 async_bulk helper

依赖：elasticsearch>=8.0.0,<9.0.0

设计文档：docs/internal/db-pipelines-design.md §3.6
"""

import asyncio
from typing import List, Dict, Optional

from crawlo.logging import get_logger
from crawlo.pipelines.generic_doc import GenericDocumentPipeline

# 尝试导入 elasticsearch
try:
    from elasticsearch import AsyncElasticsearch
    from elasticsearch.helpers import async_bulk
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False


class ElasticsearchPipeline(GenericDocumentPipeline):
    """Elasticsearch 管道实现"""

    _PREFIX = 'ELASTICSEARCH'

    # ── 配置 ──

    def _init_config(self):
        """扩展配置 — Elasticsearch 特有"""

        if not ES_AVAILABLE:
            raise ImportError(
                "elasticsearch is required for ElasticsearchPipeline. "
                "Install: pip install elasticsearch>=8.0.0,<9.0.0"
            )

        super()._init_config()

        # ES 连接配置
        self.es_hosts = self.settings.get(
            'ELASTICSEARCH_HOSTS', ['http://127.0.0.1:9200']
        )
        self.index_name = self.settings.get(
            'ELASTICSEARCH_INDEX',
            getattr(self.crawler.spider, 'name', 'crawlo'),
        )

    # ═══════════════════════════════════════════════
    # 资源初始化
    # ═══════════════════════════════════════════════

    async def _initialize_resources(self):
        """初始化 Elasticsearch 客户端和索引"""
        self.client = AsyncElasticsearch(
            hosts=self.es_hosts,
            # 连接配置
            request_timeout=self.settings.get_int('ELASTICSEARCH_TIMEOUT', 30),
            max_retries=self.settings.get_int('ELASTICSEARCH_MAX_RETRIES', 3),
            retry_on_timeout=True,
        )

        self.logger.info(
            f"Elasticsearch client created: {self.es_hosts}"
        )

        # 注册客户端到资源管理器
        self.register_resource(
            resource=self.client,
            cleanup_func=self._close_client,
            resource_type=None,  # 使用默认类型
            name='elasticsearch_client',
        )

        await self._check_collection_exists()

    async def _check_collection_exists(self):
        """检查索引是否存在"""
        if not self.client:
            return
        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                self.logger.warning(
                    f"Index not found: {self.index_name}. "
                    f"It will be auto-created on first document insert."
                )
            else:
                self.logger.info(f"Index exists: {self.index_name}")
        except Exception as e:
            self.logger.warning(f"Index check failed: {e}")

    async def _close_client(self, client):
        """关闭 Elasticsearch 客户端"""
        try:
            if client:
                await client.close()
                self.logger.info("Elasticsearch client closed")
        except Exception as e:
            self.logger.error(f"Close ES client failed: {e}")

    # ═══════════════════════════════════════════════
    # 单文档 upsert
    # ═══════════════════════════════════════════════

    async def _do_upsert(self, doc: dict) -> int:
        """单文档 upsert（index API 自带 upsert 语义）"""
        doc_id = self._compute_doc_id(doc)
        await self.client.index(
            index=self.index_name,
            id=doc_id,
            document=doc,
        )
        return 1

    # ═══════════════════════════════════════════════
    # 批量 upsert
    # ═══════════════════════════════════════════════

    async def _do_batch_upsert(self, docs: List[dict]) -> int:
        """批量文档 upsert（使用 async_bulk）"""
        if not docs:
            return 0

        actions = [
            {
                '_index': self.index_name,
                '_id': self._compute_doc_id(doc),
                '_source': doc,
            }
            for doc in docs
        ]

        success, errors = await async_bulk(
            self.client,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
        )

        if errors:
            self.logger.warning(
                f"Batch upsert partial errors: {len(errors)} docs failed"
            )

        return success

    # ═══════════════════════════════════════════════
    # 清理
    # ═══════════════════════════════════════════════

    async def _cleanup_resources(self):
        """清理资源 — 先刷新缓冲区，再关闭"""
        if self.use_batch and self.batch_buffer:
            spider = getattr(self.crawler, 'spider', None)
            spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'
            self.logger.info(
                f"[{spider_name}] Flushing remaining {len(self.batch_buffer)} ES docs"
            )
            await self._flush_batch(spider)
        self.batch_buffer.clear()
        self._initialized = False
        # 客户端由 ResourceManager 自动关闭
