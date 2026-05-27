# -*- coding: utf-8 -*-
"""
GenericSQLPipeline — 通用 SQL Pipeline 基类
============================================

提取 MySQLPipeline 中所有与数据库无关的通用逻辑：
- 批量缓冲管理
- 重试机制
- 降级策略
- 事务控制
- 错误分类
- 统计记录

子类只需实现：
  1. _get_config_prefix   → 返回配置前缀（'MYSQL' | 'ORACLE' | 'PG'）
  2. _initialize_pool      → 创建数据库连接池
  3. _create_helper        → 创建数据库 Helper 实例
  4. _close_pool           → 关闭连接池
  5. _do_insert            → 单条插入（数据库专属语法）
  6. _do_batch_insert      → 批量事务插入（数据库专属语法）
  7. _do_batch_insert_no_tx → 批量无事务插入（数据库专属语法）
  8. _check_table_exists   → 检查表是否存在（数据库专属语法）

用户编写自定义 Pipeline 示例（约 50 行）：

    class OraclePipeline(GenericSQLPipeline):
        _PREFIX = 'ORACLE'

        async def _initialize_pool(self):
            self.pool = await OraclePoolManager.get_pool(...)

        async def _create_helper(self):
            self._helper = OracleHelper(self.settings)

        async def _close_pool(self, pool):
            await pool.close()

        async def _do_insert(self, data):
            return await self._helper.insert(table=self.table_name, data=data, ...)

        async def _do_batch_insert(self, batch):
            return await self._helper.insert_many(table=self.table_name, datas=batch, ...)

        async def _do_batch_insert_no_tx(self, batch):
            return await self._helper.insert_many(table=self.table_name, datas=batch, ...)

        async def _check_table_exists(self):
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1 FROM user_tables WHERE table_name=:1", (self.table_name.upper(),))
                    if not await cur.fetchone():
                        self.logger.warning(f"Table not found: {self.table_name}")
"""
import asyncio
import re
import time
from abc import abstractmethod
from typing import List, Dict, Optional, Any, Tuple

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.resource_manager import ResourceType
from crawlo.utils.db.pipeline_utils import ErrorClassifier
from . import ResourceManagedPipeline


class GenericSQLPipeline(ResourceManagedPipeline):
    """通用 SQL Pipeline 基类 — 提取所有数据库无关逻辑"""

    # ── 子类必须覆盖的配置前缀 ──
    _PREFIX: str = 'SQL'  # 子类覆盖为 'MYSQL' | 'ORACLE' | 'PG'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

        self._init_config()

        self._lock = asyncio.Lock()
        self._initialized = False
        self.pool = None
        self._helper: Any = None
        self._fallback_failures = 0

    # ═══════════════════════════════════════════════
    # 配置解析
    # ═══════════════════════════════════════════════

    def _init_config(self):
        """初始化配置（子类可重写以扩展）"""
        prefix = self._PREFIX
        spider_table = None
        if hasattr(self.crawler, 'spider') and self.crawler.spider:
            spider_table = getattr(self.crawler.spider, 'custom_settings', {}).get(f'{prefix}_TABLE')
            if not spider_table:
                spider_table = getattr(self.crawler.spider, f'{prefix.lower()}_table', None)

        self.table_name = spider_table or self.settings.get(f'{prefix}_TABLE') or \
                          f"{getattr(self.crawler.spider, 'name', 'default')}_items"
        self.table_name = self._sanitize_table_name(self.table_name)

        # 批量插入配置
        self.batch_size = max(1, self.settings.get_int(f'{prefix}_BATCH_SIZE', 100))
        self.max_buffer_size = max(self.batch_size, self.settings.get_int(f'{prefix}_MAX_BUFFER_SIZE', 1000))
        self.use_batch = self.settings.get_bool(f'{prefix}_USE_BATCH', False)

        # 重试配置
        self.max_retries = self.settings.get_int(f'{prefix}_EXECUTE_MAX_RETRIES', 3)
        self.retry_delay = self.settings.get_float(f'{prefix}_EXECUTE_RETRY_DELAY', 0.5)

        # SQL 生成行为配置
        self.auto_update = self.settings.get_bool(f'{prefix}_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool(f'{prefix}_INSERT_IGNORE', False)
        self.update_columns = self._parse_columns(self.settings.get(f'{prefix}_UPDATE_COLUMNS', ()))

        # 事务和降级配置
        self.use_transaction = self.settings.get_bool(f'{prefix}_USE_TRANSACTION', True)
        self.fallback_threshold = self.settings.get_int(f'{prefix}_FALLBACK_THRESHOLD', 10)

    @staticmethod
    def _sanitize_table_name(name: str) -> str:
        """清理表名"""
        if not name:
            raise ValueError("Table name is required")
        name = str(name).strip().replace(' ', '_').replace('-', '_')
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValueError(f"Invalid table name: {name}")
        return name

    @staticmethod
    def _parse_columns(cols) -> tuple:
        """解析列配置"""
        if not cols:
            return ()
        if isinstance(cols, (list, tuple)):
            return tuple(cols)
        return (cols,)

    # ═══════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════

    async def open_spider(self, spider) -> None:
        """爬虫启动时初始化资源"""
        try:
            await self._ensure_initialized()
            self.logger.info(
                f"{self.__class__.__name__} ready: table={self.table_name}, "
                f"batch={'enabled' if self.use_batch else 'disabled'}, "
                f"batch_size={self.batch_size}, "
                f"transaction={'enabled' if self.use_transaction else 'disabled'}, "
                f"spider={spider.name}"
            )
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} initialization failed on spider open: {e}")
            raise

    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理数据项"""
        await self._ensure_initialized()
        if self.use_batch:
            return await self._add_to_batch(item, spider)
        return await self._insert_single(item)

    async def _ensure_initialized(self):
        """确保已初始化（DCL 模式）"""
        if self._initialized and self.pool:
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
        """初始化资源"""
        await self._initialize_pool()
        await self._create_helper()
        await self._check_table_exists()
        self.register_resource(
            resource=self.pool,
            cleanup_func=self._close_pool_wrapper,
            resource_type=ResourceType.PIPELINE,
            name=f"{self._PREFIX.lower()}_pool"
        )

    @abstractmethod
    async def _initialize_pool(self):
        """创建数据库连接池（子类实现）"""
        raise NotImplementedError

    @abstractmethod
    async def _create_helper(self):
        """创建数据库 Helper 实例（子类实现）"""
        raise NotImplementedError

    @abstractmethod
    async def _check_table_exists(self):
        """检查表是否存在（子类实现）"""
        pass

    @abstractmethod
    async def _close_pool(self, pool):
        """关闭连接池（子类实现）"""
        raise NotImplementedError

    async def _close_pool_wrapper(self, pool):
        """ResourceManager 回调包装"""
        await self._close_pool(pool)

    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider = getattr(self.crawler, 'spider', None)
            spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'
            self.logger.info(
                f"[{spider_name}] Spider closing, flushing remaining {len(self.batch_buffer)} items"
            )
            await self._flush_batch(spider)
        self.batch_buffer.clear()
        self._initialized = False

    # ═══════════════════════════════════════════════
    # 单条插入 + 重试
    # ═══════════════════════════════════════════════

    async def _insert_single(self, item: Item) -> Item:
        """单条插入（带重试和错误分类）"""
        processed_data = await self._before_insert(item)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                rowcount = await self._do_insert(processed_data)
                elapsed = time.time() - start_time
                self._record_success(item, rowcount, elapsed)
                await self._after_insert(item, rowcount)
                return item
            except Exception as e:
                if ErrorClassifier.is_skipable(e):
                    self.logger.debug(
                        f"[{self.table_name}] 重复数据已跳过: "
                        f"{ErrorClassifier.get_error_description(e)}"
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
                raise ItemDiscard(f"Insert failed: {ErrorClassifier.get_error_description(e)}")
        return item

    @abstractmethod
    async def _do_insert(self, data: Dict[str, Any]) -> int:
        """执行单条插入（子类实现，返回行数）"""
        raise NotImplementedError

    # ═══════════════════════════════════════════════
    # 批量插入
    # ═══════════════════════════════════════════════

    async def _add_to_batch(self, item: Item, spider) -> Item:
        """添加到批量缓冲区"""
        async with self._lock:
            if len(self.batch_buffer) >= self.max_buffer_size:
                self.logger.debug(f"Buffer full, triggering flush")
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
            if self.use_transaction:
                rowcount = await self._do_batch_insert(batch)
            else:
                rowcount = await self._do_batch_insert_no_tx(batch)
            elapsed = time.time() - start_time

            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_success')
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_items', batch_size)
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/rows', rowcount or 0)
            self.crawler.stats.inc_value(f'{self._PREFIX.lower()}/batch_time', elapsed)
            self._fallback_failures = 0

            self.logger.info(
                f"[{spider_name}] Batch insert success: {batch_size} items -> table={self.table_name}, "
                f"{rowcount} rows, {elapsed:.3f}s"
            )
        except Exception as e:
            if ErrorClassifier.is_skipable(e):
                self.logger.debug(
                    f"[{spider_name}] 批量数据已跳过: "
                    f"{ErrorClassifier.get_error_description(e)}"
                )
                return
            self._fallback_failures += 1
            self.logger.warning(
                f"[{spider_name}] Batch failed (fallback {self._fallback_failures}/{self.fallback_threshold}): "
                f"{ErrorClassifier.get_error_description(e)}"
            )
            if self._fallback_failures >= self.fallback_threshold:
                self.logger.error(f"[{spider_name}] Fallback threshold exceeded, aborting batch")
                raise ItemDiscard(f"Too many fallback failures: {e}")
            await self._fallback_insert(batch, spider_name)

    @abstractmethod
    async def _do_batch_insert(self, batch: List[Dict]) -> int:
        """批量事务插入（子类实现，返回行数）"""
        raise NotImplementedError

    @abstractmethod
    async def _do_batch_insert_no_tx(self, batch: List[Dict]) -> int:
        """批量无事务插入（子类实现，返回行数）"""
        raise NotImplementedError

    # ═══════════════════════════════════════════════
    # 降级插入
    # ═══════════════════════════════════════════════

    async def _fallback_insert(self, datas: List[Dict], spider_name: str = 'unknown'):
        """降级单条插入"""
        self.logger.info(f"[{spider_name}] Fallback to single insert for {len(datas)} items")
        success = 0
        failed = 0
        for data in datas:
            try:
                await self._do_insert(data)
                success += 1
            except Exception as e:
                if not ErrorClassifier.is_skipable(e):
                    failed += 1
                    self.logger.error(
                        f"[{spider_name}] Fallback insert failed: {ErrorClassifier.get_error_description(e)}"
                    )
        self.logger.info(
            f"[{spider_name}] Fallback insert completed: {success}/{len(datas)} success, {failed} failed"
        )

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
        """记录单条插入成功统计"""
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
