# -*- coding: utf-8 -*-
"""
MySQL Pipeline - 异步 MySQL 数据管道

设计原则：
1. 异常分类：可跳过 vs 需抛出
2. 可跳过错误：不中断爬虫，记录日志
3. 需抛出错误：中断当前 item 处理
4. 事务支持：保证批量操作的原子性
5. 性能监控：记录关键性能指标
6. 扩展性：提供钩子方法支持自定义逻辑
"""
import re
import asyncio
import time
from typing import List, Dict, Optional, Any

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.resource_manager import ResourceType
from crawlo.utils.db.mysql_helper import MySQLHelper
from crawlo.utils.db.mysql_connection_pool import (
    MySQLConnectionPoolManager,
    is_pool_active
)
from crawlo.utils.db.pipeline_utils import (
    ErrorClassifier
)
from . import ResourceManagedPipeline


class MySQLPipeline(ResourceManagedPipeline):
    """MySQL 管道实现"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self._init_config()
        
        self._lock = asyncio.Lock()
        self._initialized = False
        self.pool = None
        self.batch_buffer: List[Dict] = []
        self._helper: Optional[MySQLHelper] = None
        self._fallback_failures = 0
        
        self.logger.info(
            f"MySQL Pipeline initialized: table={self.table_name}, "
            f"batch={'enabled' if self.use_batch else 'disabled'}, "
            f"batch_size={self.batch_size}, "
            f"transaction={'enabled' if self.use_transaction else 'disabled'}"
        )
    
    def _init_config(self):
        """初始化配置"""
        spider_table = None
        if hasattr(self.crawler, 'spider') and self.crawler.spider:
            spider_table = getattr(self.crawler.spider, 'custom_settings', {}).get('MYSQL_TABLE')
            if not spider_table:
                spider_table = getattr(self.crawler.spider, 'mysql_table', None)
        
        # 表名配置优先级：Spider 自定义配置 > 全局配置 > Spider 名称
        self.table_name = spider_table or self.settings.get('MYSQL_TABLE') or f"{getattr(self.crawler.spider, 'name', 'default')}_items"
        self.table_name = self._sanitize_table_name(self.table_name)
        
        # 批量插入配置
        self.batch_size = max(1, self.settings.get_int('MYSQL_BATCH_SIZE', 100))
        self.max_buffer_size = max(self.batch_size, self.settings.get_int('MYSQL_MAX_BUFFER_SIZE', 1000))
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        
        # 重试配置
        self.max_retries = self.settings.get_int('MYSQL_EXECUTE_MAX_RETRIES', 3)
        self.retry_delay = self.settings.get_float('MYSQL_EXECUTE_RETRY_DELAY', 0.5)
        
        # SQL 生成行为配置
        self.auto_update = self.settings.get_bool('MYSQL_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool('MYSQL_INSERT_IGNORE', False)
        self.update_columns = self._parse_columns(self.settings.get('MYSQL_UPDATE_COLUMNS', ()))
        self.check_table = self.settings.get_bool('MYSQL_CHECK_TABLE_EXISTS', True)
        
        # 事务和降级配置
        self.use_transaction = self.settings.get_bool('MYSQL_USE_TRANSACTION', True)
        self.fallback_threshold = self.settings.get_int('MYSQL_FALLBACK_THRESHOLD', 10)
        self.enable_performance_log = self.settings.get_bool('MYSQL_PERFORMANCE_LOG', False)
    
    def _sanitize_table_name(self, name: str) -> str:
        """清理表名"""
        if not name:
            raise ValueError("Table name is required")
        name = str(name).strip().replace(' ', '_').replace('-', '_')
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValueError(f"Invalid table name: {name}")
        return name
    
    def _parse_columns(self, cols) -> tuple:
        """解析列配置"""
        if not cols:
            return ()
        if isinstance(cols, (list, tuple)):
            return tuple(cols)
        return (cols,)
    
    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理数据项"""
        await self._ensure_initialized()
        
        if self.use_batch:
            return await self._add_to_batch(item, spider)
        return await self._insert_single(item)
    
    async def _add_to_batch(self, item: Item, spider) -> Item:
        """添加到批量缓冲区"""
        async with self._lock:
            if len(self.batch_buffer) >= self.max_buffer_size:
                await self._flush_batch(spider.name)
            self.batch_buffer.append(dict(item))
            should_flush = len(self.batch_buffer) >= self.batch_size
        
        if should_flush:
            await self._flush_batch(spider.name)
        return item
    
    async def _insert_single(self, item: Item) -> Item:
        """单条插入（带重试）"""
        processed_data = await self.before_insert(item)
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                rowcount = await self._helper.insert(
                    table=self.table_name,
                    data=processed_data,
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                elapsed = time.time() - start_time
                
                self.crawler.stats.inc_value('mysql/success')
                self.crawler.stats.inc_value('mysql/rows', rowcount or 0)
                self.crawler.stats.inc_value('mysql/insert_time', elapsed)
                await self.after_insert(item, rowcount)
                return item
                
            except Exception as e:
                if ErrorClassifier.is_skipable(e):
                    self.logger.warning(f"Skip item: {ErrorClassifier.get_error_description(e)}")
                    self.crawler.stats.inc_value('mysql/skipped')
                    return item
                
                if ErrorClassifier.is_retryable(e) and attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"Retry ({attempt + 1}/{self.max_retries}): "
                        f"{ErrorClassifier.get_error_description(e)}"
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                self.crawler.stats.inc_value('mysql/failed')
                raise ItemDiscard(f"Insert failed: {ErrorClassifier.get_error_description(e)}")
        
        return item
    
    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区"""
        async with self._lock:
            if not self.batch_buffer:
                return
            batch = self.batch_buffer[:]
            self.batch_buffer.clear()
        
        if not batch:
            return
        
        try:
            start_time = time.time()
            
            if self.use_transaction:
                rowcount = await self._flush_batch_with_transaction(batch)
            else:
                rowcount = await self._flush_batch_without_transaction(batch)
            
            elapsed = time.time() - start_time
            
            self.crawler.stats.inc_value('mysql/batch_success')
            self.crawler.stats.inc_value('mysql/batch_items', len(batch))
            self.crawler.stats.inc_value('mysql/rows', rowcount or 0)
            self.crawler.stats.inc_value('mysql/batch_time', elapsed)
            self._fallback_failures = 0
            
            if self.enable_performance_log:
                self.logger.info(
                    f"Batch inserted: {len(batch)} items, {rowcount} rows affected, "
                    f"time={elapsed:.3f}s"
                )
            
        except Exception as e:
            if ErrorClassifier.is_skipable(e):
                self.logger.warning(f"Batch skipped: {ErrorClassifier.get_error_description(e)}")
                return
            
            self._fallback_failures += 1
            self.logger.warning(
                f"Batch failed (fallback failures: {self._fallback_failures}/{self.fallback_threshold}), "
                f"fallback to single insert: {ErrorClassifier.get_error_description(e)}"
            )
            
            if self._fallback_failures >= self.fallback_threshold:
                self.logger.error(
                    f"Fallback threshold exceeded ({self.fallback_threshold}), "
                    f"aborting batch processing"
                )
                raise ItemDiscard(f"Too many fallback failures: {e}")
            
            await self._fallback_insert(batch)
    
    async def _flush_batch_with_transaction(self, batch: List[Dict]) -> int:
        """使用事务刷新批量缓冲区"""
        async with self._helper.transaction() as cursor:
            sql, params = self._helper._sql_builder.make_batch(
                self.table_name,
                batch,
                auto_update=self.auto_update,
                update_columns=self.update_columns,
                insert_ignore=self.insert_ignore
            )
            
            if sql is None:
                return 0
            
            await cursor.execute(sql, params)
            return cursor.rowcount
    
    async def _flush_batch_without_transaction(self, batch: List[Dict]) -> int:
        """不使用事务刷新批量缓冲区"""
        return await self._helper.insert_many(
            table=self.table_name,
            datas=batch,
            auto_update=self.auto_update,
            update_columns=self.update_columns,
            insert_ignore=self.insert_ignore,
            batch_size=len(batch)
        )
    
    async def _fallback_insert(self, datas: List[Dict]):
        """降级单条插入"""
        success = 0
        failed = 0
        
        for data in datas:
            try:
                await self._helper.insert(
                    table=self.table_name,
                    data=data,
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                success += 1
            except Exception as e:
                if not ErrorClassifier.is_skipable(e):
                    failed += 1
                    self.logger.error(f"Fallback insert failed: {ErrorClassifier.get_error_description(e)}")
        
        self.logger.info(
            f"Fallback insert completed: {success}/{len(datas)} success, {failed} failed"
        )
    
    async def _initialize_resources(self):
        """初始化资源（实现 ResourceManagedPipeline 抽象方法）"""
        await self._initialize_pool()
        await self._initialize_helper()
        
        if self.check_table:
            await self._check_table_exists()
        
        self.register_resource(
            resource=self.pool,
            cleanup_func=self._close_pool,
            resource_type=ResourceType.PIPELINE,
            name="mysql_pool"
        )
    
    async def _ensure_initialized(self):
        """确保已初始化"""
        if self._initialized and self.pool and is_pool_active(self.pool):
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            await self._initialize_resources()
            
            self._initialized = True
            self.logger.info("MySQL Pipeline initialized successfully")
    
    async def _initialize_pool(self):
        """初始化连接池"""
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
    
    async def _initialize_helper(self):
        """初始化 Helper"""
        self._helper = await MySQLHelper.get_instance(self.settings)
        self.logger.debug("MySQL helper initialized")
    
    async def _check_table_exists(self):
        """检查表是否存在"""
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
    
    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                pool.close()
                await pool.wait_closed()
                self.logger.info("MySQL pool closed")
        except Exception as e:
            self.logger.error(f"Close pool failed: {e}")
    
    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
        
        self.batch_buffer.clear()
        self._initialized = False
        
        await super()._cleanup_resources()
    
    async def before_insert(self, item: Item) -> Dict[str, Any]:
        """插入前的数据处理钩子（可被子类重写）"""
        return dict(item)
    
    async def after_insert(self, item: Item, rowcount: int):
        """插入后的处理钩子（可被子类重写）"""
        pass
    
    @classmethod
    async def from_crawler(cls, crawler):
        return cls(crawler)
