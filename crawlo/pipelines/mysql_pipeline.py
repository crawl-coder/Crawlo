# -*- coding: utf-8 -*-
"""
MySQL Pipeline - 异步 MySQL 数据管道

设计原则：
1. 异常分类：可跳过 vs 需抛出
2. 可跳过错误：不中断爬虫，记录日志
3. 需抛出错误：中断当前 item 处理
"""
import re
import asyncio
from typing import List, Dict, Optional

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.resource_manager import ResourceType
from crawlo.utils.db.mysql_helper import MySQLHelper
from crawlo.utils.db.mysql_connection_pool import (
    MySQLConnectionPoolManager,
    is_pool_active
)
from . import ResourceManagedPipeline


# 可跳过的 MySQL 错误码（不中断爬虫）
SKIPABLE_ERROR_CODES = {
    1062: '重复数据',
    1205: '锁等待超时',
    1213: '死锁',
    2006: 'MySQL服务器断开',
    2013: '连接丢失',
    2014: '脏连接',
}

# 可重试的 MySQL 错误码（连接类问题）
RETRYABLE_ERROR_CODES = {
    2006: 'MySQL服务器断开',
    2013: '连接丢失',
    2014: '脏连接',
}


def extract_error_code(error: Exception) -> Optional[int]:
    """从异常中提取 MySQL 错误码"""
    err_str = str(error)
    # 匹配 (1062, "...") 格式
    match = re.search(r'\((\d+),', err_str)
    if match:
        return int(match.group(1))
    return None


def is_skipable_error(error: Exception) -> bool:
    """判断是否为可跳过的错误"""
    code = extract_error_code(error)
    return code in SKIPABLE_ERROR_CODES


def is_retryable_error(error: Exception) -> bool:
    """判断是否为可重试的错误"""
    code = extract_error_code(error)
    return code in RETRYABLE_ERROR_CODES


class MySQLPipeline(ResourceManagedPipeline):
    """MySQL 管道实现"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 初始化配置
        self._init_config()
        
        # 异步锁和状态
        self._lock = asyncio.Lock()
        self._initialized = False
        self.pool = None
        self.batch_buffer: List[Dict] = []
        self._helper: Optional[MySQLHelper] = None
        
        self.logger.info(
            f"MySQL Pipeline: table={self.table_name}, "
            f"batch={'enabled' if self.use_batch else 'disabled'}"
        )
    
    def _init_config(self):
        """初始化配置"""
        # 表名
        spider_table = None
        if hasattr(self.crawler, 'spider') and self.crawler.spider:
            spider_table = getattr(self.crawler.spider, 'custom_settings', {}).get('MYSQL_TABLE')
            if not spider_table:
                spider_table = getattr(self.crawler.spider, 'mysql_table', None)
        
        self.table_name = spider_table or self.settings.get('MYSQL_TABLE') or f"{getattr(self.crawler.spider, 'name', 'default')}_items"
        self.table_name = self._sanitize_table_name(self.table_name)
        
        # 批量配置
        self.batch_size = max(1, self.settings.get_int('MYSQL_BATCH_SIZE', 100))
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        
        # 重试配置
        self.max_retries = self.settings.get_int('MYSQL_EXECUTE_MAX_RETRIES', 3)
        self.retry_delay = self.settings.get_float('MYSQL_EXECUTE_RETRY_DELAY', 0.5)
        
        # SQL 配置
        self.auto_update = self.settings.get_bool('MYSQL_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool('MYSQL_INSERT_IGNORE', False)
        self.update_columns = self._parse_columns(self.settings.get('MYSQL_UPDATE_COLUMNS', ()))
        self.check_table = self.settings.get_bool('MYSQL_CHECK_TABLE_EXISTS', True)
    
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
            self.batch_buffer.append(dict(item))
            should_flush = len(self.batch_buffer) >= self.batch_size
        
        if should_flush:
            await self._flush_batch(spider.name)
        return item
    
    async def _insert_single(self, item: Item) -> Item:
        """单条插入（带重试）"""
        for attempt in range(self.max_retries):
            try:
                rowcount = await self._helper.insert(
                    table=self.table_name,
                    data=dict(item),
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                self._update_stats(rowcount, 1)
                return item
                
            except Exception as e:
                # 可跳过的错误：记录日志，继续下一个
                if is_skipable_error(e):
                    self.logger.warning(f"Skip item: {e}")
                    self.crawler.stats.inc_value('mysql/skipped')
                    return item
                
                # 可重试的错误：等待后重试
                if is_retryable_error(e) and attempt < self.max_retries - 1:
                    self.logger.warning(f"Retry ({attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                # 其他错误：抛出异常
                self.crawler.stats.inc_value('mysql/failed')
                raise ItemDiscard(f"Insert failed: {e}")
        
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
            rowcount = await self._helper.insert_many(
                table=self.table_name,
                datas=batch,
                auto_update=self.auto_update,
                update_columns=self.update_columns,
                insert_ignore=self.insert_ignore,
                batch_size=len(batch)
            )
            self._update_stats(rowcount, len(batch))
            self.logger.info(f"Batch: {len(batch)} items, {rowcount} rows")
            
        except Exception as e:
            if is_skipable_error(e):
                self.logger.warning(f"Batch skipped: {e}")
                return
            
            # 降级为单条插入
            self.logger.warning(f"Batch failed, fallback to single: {e}")
            await self._fallback_insert(batch)
    
    async def _fallback_insert(self, datas: List[Dict]):
        """降级单条插入"""
        success = 0
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
                if not is_skipable_error(e):
                    self.logger.error(f"Fallback failed: {e}")
        
        self.logger.info(f"Fallback: {success}/{len(datas)} success")
    
    def _update_stats(self, rowcount: int, total: int):
        """更新统计"""
        self.crawler.stats.inc_value('mysql/success')
        self.crawler.stats.inc_value('mysql/rows', rowcount or 0)
    
    async def _ensure_initialized(self):
        """确保已初始化"""
        if self._initialized and self.pool and is_pool_active(self.pool):
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            # 初始化连接池
            self.pool = await MySQLConnectionPoolManager.get_pool(
                host=self.settings.get('MYSQL_HOST', 'localhost'),
                port=self.settings.get_int('MYSQL_PORT', 3306),
                user=self.settings.get('MYSQL_USER', 'root'),
                password=self.settings.get('MYSQL_PASSWORD', ''),
                db=self.settings.get('MYSQL_DB', 'crawlo_db'),
                minsize=self.settings.get_int('MYSQL_POOL_MIN', 3),
                maxsize=self.settings.get_int('MYSQL_POOL_MAX', 10),
            )
            
            # 初始化 Helper
            self._helper = await MySQLHelper.get_instance(self.settings)
            
            # 检查表
            if self.check_table:
                await self._check_table()
            
            # 注册资源
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.PIPELINE,
                name="mysql_pool"
            )
            
            self._initialized = True
    
    async def _check_table(self):
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
        # 刷新剩余批量
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
        
        self.batch_buffer.clear()
        self._initialized = False
        await super()._cleanup_resources()
    
    @classmethod
    async def from_crawler(cls, crawler):
        return cls(crawler)
