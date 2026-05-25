# -*- coding: utf-8 -*-
"""
GenericDocumentPipeline — 文档型数据库通用基类
===============================================

提供与 GenericSQLPipeline 对称的完整能力：
- 批量缓冲管理 + 刷新
- 文档级别 upsert（单条/批量）
- 连接生命周期管理
- 重试 + 降级 + 统计（复用 ErrorClassifier）
- 失败数据保存到文件
- 钩子：_before_insert / _after_insert

子类只需实现 4 个抽象方法：
  1. _do_upsert(doc)         — 单文档 upsert
  2. _do_batch_upsert(docs)  — 批量文档 upsert
  3. _check_collection_exists()  — 集合/索引存在性检查
  4. _close_client(client)   — 关闭客户端连接

设计文档：docs/internal/db-pipelines-design.md §3.4
"""

import asyncio
import json
import hashlib
import time
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.db.pipeline_utils import ErrorClassifier
from . import ResourceManagedPipeline


class GenericDocumentPipeline(ResourceManagedPipeline):
    """文档型数据库通用基类 — 与 GenericSQLPipeline 对称设计"""

    # ── 子类必须覆盖 ──
    _PREFIX: str = 'DOC'  # 配置前缀，子类覆盖为 'MONGO' | 'ELASTICSEARCH'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

        self._init_config()

        self._lock = asyncio.Lock()
        self._initialized = False
        self.client: Optional[Any] = None
        self._fallback_failures = 0

    # ═══════════════════════════════════════════════
    # 配置解析
    # ═══════════════════════════════════════════════

    def _init_config(self):
        """初始化配置（子类可重写以扩展）"""
        prefix = self._PREFIX

        # 批量插入配置
        self.batch_size = max(1, self.settings.get_int(f'{prefix}_BATCH_SIZE', 100))
        self.max_buffer_size = max(
            self.batch_size, self.settings.get_int(f'{prefix}_MAX_BUFFER_SIZE', 1000)
        )
        self.use_batch = self.settings.get_bool(f'{prefix}_USE_BATCH', False)

        # 重试配置
        self.max_retries = self.settings.get_int(f'{prefix}_EXECUTE_MAX_RETRIES', 3)
        self.retry_delay = self.settings.get_float(f'{prefix}_EXECUTE_RETRY_DELAY', 0.5)

        # 降级阈值
        self.fallback_threshold = self.settings.get_int(f'{prefix}_FALLBACK_THRESHOLD', 10)

    # ═══════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════

    async def open_spider(self, spider) -> None:
        """爬虫启动时初始化资源"""
        try:
            await self._ensure_initialized()
            self.logger.info(
                f"{self.__class__.__name__} ready: "
                f"batch={'enabled' if self.use_batch else 'disabled'}, "
                f"batch_size={self.batch_size}, "
                f"spider={spider.name}"
            )
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} init failed on spider open: {e}")
            raise

    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理数据项"""
        await self._ensure_initialized()
        if self.use_batch:
            return await self._add_to_batch(item, spider)
        return await self._insert_single(item)

    async def _ensure_initialized(self):
        """确保已初始化（DCL 模式）"""
        if self._initialized and self.client is not None:
            return
        async with self._lock:
            if self._initialized:
                return
            await self._initialize_resources()
            self._initialized = True
            self.logger.debug(f"{self.__class__.__name__} resources initialized")

    # ═══════════════════════════════════════════════
    # 资源初始化（子类实现）
    # ═══════════════════════════════════════════════

    async def _initialize_resources(self):
        """初始化资源 — 子类可重写"""
        await self._check_collection_exists()

    @abstractmethod
    async def _check_collection_exists(self):
        """检查集合/索引是否存在（子类实现）"""
        pass

    @abstractmethod
    async def _close_client(self, client):
        """关闭客户端连接（子类实现）"""
        raise NotImplementedError

    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider = getattr(self.crawler, 'spider', None)
            spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'
            self.logger.info(
                f"[{spider_name}] Flushing remaining {len(self.batch_buffer)} docs"
            )
            await self._flush_batch(spider)
        self.batch_buffer.clear()
        self._initialized = False

    # ═══════════════════════════════════════════════
    # 文档 ID 生成
    # ═══════════════════════════════════════════════

    def _compute_doc_id(self, doc: dict) -> str:
        """计算文档确定性 ID（MD5 指纹），子类可重写"""
        return hashlib.md5(
            json.dumps(doc, sort_keys=True, ensure_ascii=False).encode('utf-8')
        ).hexdigest()

    # ═══════════════════════════════════════════════
    # 单文档 upsert + 重试
    # ═══════════════════════════════════════════════

    async def _insert_single(self, item: Item) -> Item:
        """单文档 upsert（带重试和错误分类）"""
        processed_data = await self._before_insert(item)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                rowcount = await self._do_upsert(processed_data)
                elapsed = time.time() - start_time
                self._record_success(item, rowcount, elapsed)
                await self._after_insert(item, rowcount)
                return item
            except Exception as e:
                if ErrorClassifier.is_skipable(e):
                    self.logger.warning(
                        f"Skip doc: {ErrorClassifier.get_error_description(e)}"
                    )
                    self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/skipped')
                    return item
                if ErrorClassifier.is_retryable(e) and attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"Retry ({attempt + 1}/{self.max_retries}): "
                        f"{ErrorClassifier.get_error_description(e)}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/failed')
                raise ItemDiscard(
                    f"Upsert failed: {ErrorClassifier.get_error_description(e)}"
                )
        return item

    @abstractmethod
    async def _do_upsert(self, doc: dict) -> int:
        """单文档 upsert，返回受影响的文档数（子类实现）"""
        raise NotImplementedError

    # ═══════════════════════════════════════════════
    # 批量 upsert
    # ═══════════════════════════════════════════════

    async def _add_to_batch(self, item: Item, spider) -> Item:
        """添加到批量缓冲区"""
        async with self._lock:
            if len(self.batch_buffer) >= self.max_buffer_size:
                self.logger.debug("Buffer full, triggering flush")
                await self._flush_batch(spider)
            self.batch_buffer.append(dict(item))
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
        batch_size = len(batch)

        try:
            start_time = time.time()
            rowcount = await self._do_batch_upsert(batch)
            elapsed = time.time() - start_time

            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_success')
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_docs', batch_size)
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/rows', rowcount or 0)
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_time', elapsed)
            self._fallback_failures = 0

            self.logger.info(
                f"[{spider_name}] Batch upsert success: {batch_size} docs, "
                f"{rowcount} affected, {elapsed:.3f}s"
            )
        except Exception as e:
            if ErrorClassifier.is_skipable(e):
                self.logger.warning(
                    f"[{spider_name}] Batch skipped: {ErrorClassifier.get_error_description(e)}"
                )
                return
            self._fallback_failures += 1
            self.logger.warning(
                f"[{spider_name}] Batch failed (fallback {self._fallback_failures}"
                f"/{self.fallback_threshold}): {ErrorClassifier.get_error_description(e)}"
            )
            if self._fallback_failures >= self.fallback_threshold:
                self.logger.error(
                    f"[{spider_name}] Fallback threshold exceeded, aborting batch"
                )
                raise ItemDiscard(f"Too many fallback failures: {e}")
            await self._fallback_upsert(batch, spider_name)

    @abstractmethod
    async def _do_batch_upsert(self, docs: List[dict]) -> int:
        """批量文档 upsert，返回受影响的文档数（子类实现）"""
        raise NotImplementedError

    # ═══════════════════════════════════════════════
    # 降级插入
    # ═══════════════════════════════════════════════

    async def _fallback_upsert(self, docs: List[dict], spider_name: str = 'unknown'):
        """降级单文档 upsert"""
        self.logger.info(
            f"[{spider_name}] Fallback to single upsert for {len(docs)} docs"
        )
        success = 0
        failed = 0
        for doc in docs:
            try:
                await self._do_upsert(doc)
                success += 1
            except Exception as e:
                if not ErrorClassifier.is_skipable(e):
                    failed += 1
                    self.logger.error(
                        f"[{spider_name}] Fallback upsert failed: "
                        f"{ErrorClassifier.get_error_description(e)}"
                    )
        self.logger.info(
            f"[{spider_name}] Fallback upsert: {success}/{len(docs)} success, {failed} failed"
        )

        if failed > 0:
            await self._save_failed_batch(docs, RuntimeError(f"{failed} docs failed in fallback"))

    async def _save_failed_batch(self, docs: list, error: Exception):
        """保存失败的批量数据到文件"""
        try:
            error_dir = Path("output/errors")
            error_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            error_file = error_dir / f"{self._PREFIX.lower()}_failed_batch_{timestamp}.json"

            error_data = {
                'error': str(error),
                'timestamp': timestamp,
                'count': len(docs),
                'data': docs,
            }

            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: json.dump(
                    error_data, open(error_file, 'w', encoding='utf-8'),
                    ensure_ascii=False, indent=2
                )
            )

            self.logger.info(f"Failed docs saved to: {error_file}")
        except Exception as save_error:
            self.logger.error(f"Save failed docs error: {save_error}")

    # ═══════════════════════════════════════════════
    # 钩子方法
    # ═══════════════════════════════════════════════

    async def _before_insert(self, item: Item) -> Dict[str, Any]:
        """插入前的数据处理钩子（子类可重写）"""
        return dict(item)

    async def _after_insert(self, item: Item, rowcount: int):
        """插入后的处理钩子（子类可重写）"""
        pass

    def _record_success(self, item: Item, rowcount: int, elapsed: float):
        """记录单文档插入成功统计"""
        prefix = self._PREFIX.lower()
        self.crawler.stats.inc_value(f'{prefix}/success')
        self.crawler.stats.inc_value(f'{prefix}/rows', rowcount or 0)
        self.crawler.stats.inc_value(f'{prefix}/insert_time', elapsed)

    # ═══════════════════════════════════════════════
    # 工厂方法
    # ═══════════════════════════════════════════════

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
