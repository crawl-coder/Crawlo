# -*- coding: utf-8 -*-
"""
MySQL Pipeline - 异步 MySQL 数据管道

支持批量插入、错误自动处理、连接池管理等功能。
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


# MySQL 错误码常量
class MySQLErrorCode:
    """MySQL 错误码定义"""
    DUPLICATE_ENTRY = 1062
    LOCK_WAIT_TIMEOUT = 1205
    COMMAND_OUT_OF_SYNC = 2014
    MYSQL_SERVER_GONE = 2006
    MYSQL_SERVER_LOST = 2013


class MySQLErrorHandler:
    """MySQL 错误处理器 - 统一处理各种 MySQL 错误"""
    
    # 错误码到处理策略的映射
    ERROR_HANDLERS = {
        MySQLErrorCode.DUPLICATE_ENTRY: {
            'action': 'skip',
            'log_level': 'debug',
            'message': '数据已存在，跳过',
            'stat_key': 'mysql/rows_ignored_by_duplicate',
            'retry': False
        },
        MySQLErrorCode.LOCK_WAIT_TIMEOUT: {
            'action': 'skip',
            'log_level': 'warning',
            'message': '锁等待超时，跳过',
            'stat_key': 'mysql/lock_timeout_count',
            'retry': False
        },
        MySQLErrorCode.COMMAND_OUT_OF_SYNC: {
            'action': 'skip',
            'log_level': 'warning',
            'message': '脏连接(2014)，跳过',
            'stat_key': 'mysql/dirty_connection_count',
            'retry': False
        },
        MySQLErrorCode.MYSQL_SERVER_GONE: {
            'action': 'skip',
            'log_level': 'warning',
            'message': 'MySQL服务器断开，跳过',
            'stat_key': 'mysql/server_gone_count',
            'retry': False
        },
        MySQLErrorCode.MYSQL_SERVER_LOST: {
            'action': 'skip',
            'log_level': 'warning',
            'message': 'MySQL连接丢失，跳过',
            'stat_key': 'mysql/connection_lost_count',
            'retry': False
        }
    }
    
    @classmethod
    def handle(cls, error: Exception, crawler=None, item_id: str = None) -> dict:
        """
        处理 MySQL 错误
        
        Returns:
            dict: 处理结果 {'action': 'skip'|'retry'|'raise', 'should_retry': bool}
        """
        err_str = str(error).lower()
        err_code = cls._extract_error_code(err_str)
        
        # 根据错误码获取处理策略
        handler = cls.ERROR_HANDLERS.get(err_code)
        
        if handler:
            # 记录统计
            if crawler and handler.get('stat_key'):
                crawler.stats.inc_value(handler['stat_key'])
            
            # 记录日志
            msg = handler['message']
            if item_id:
                msg = f"{msg}: {item_id}"
            
            if crawler:
                logger = get_logger('MySQLPipeline')
                log_func = getattr(logger, handler['log_level'])
                log_func(msg)
            
            return {
                'action': handler['action'],
                'should_retry': handler.get('retry', False),
                'close_conn': handler.get('close_conn', False)
            }
        
        # 未知错误，需要抛出
        return {'action': 'raise', 'should_retry': False, 'close_conn': False}
    
    @classmethod
    def _extract_error_code(cls, err_str: str) -> Optional[int]:
        """从错误字符串中提取错误码"""
        # 尝试匹配 (1062, ...) 格式
        import re
        match = re.search(r'\((\d+),', err_str)
        if match:
            return int(match.group(1))
        
        # 关键字匹配
        if 'duplicate entry' in err_str:
            return MySQLErrorCode.DUPLICATE_ENTRY
        if 'lock wait timeout' in err_str:
            return MySQLErrorCode.LOCK_WAIT_TIMEOUT
        if 'command out of sync' in err_str:
            return MySQLErrorCode.COMMAND_OUT_OF_SYNC
        if 'mysql server has gone away' in err_str:
            return MySQLErrorCode.MYSQL_SERVER_GONE
        if 'lost connection' in err_str:
            return MySQLErrorCode.MYSQL_SERVER_LOST
        
        return None


class BaseMySQLPipeline(ResourceManagedPipeline):
    """MySQL 管道基类"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        self._init_config()
        self._log_initialization()
        
        # 异步锁和状态
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        self.batch_buffer: List[Dict] = []
        self._mysql_helper: Optional[MySQLHelper] = None
    
    def _init_config(self):
        """初始化配置"""
        # 表名配置（优先级：spider.custom_settings > settings > spider.mysql_table > spider.name）
        spider_table_name = None
        if hasattr(self.crawler, 'spider') and self.crawler.spider:
            spider_table_name = getattr(self.crawler.spider, 'custom_settings', {}).get('MYSQL_TABLE')
            if not spider_table_name:
                spider_table_name = getattr(self.crawler.spider, 'mysql_table', None)
        
        self.table_name = (
            spider_table_name or
            self.settings.get('MYSQL_TABLE') or
            f"{getattr(self.crawler.spider, 'name', 'default')}_items"
        )
        
        # 验证和清理表名
        self.table_name = self._sanitize_table_name(self.table_name)
        
        # 批量插入配置
        self.batch_size = max(1, self.settings.get_int('MYSQL_BATCH_SIZE', 100))
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        self.batch_timeout = self.settings.get_int('MYSQL_BATCH_TIMEOUT', 120)
        
        # 执行配置
        self.execute_max_retries = self.settings.get_int('MYSQL_EXECUTE_MAX_RETRIES', 3)
        self.execute_timeout = self.settings.get_int('MYSQL_EXECUTE_TIMEOUT', 60)
        self.execute_retry_delay = self.settings.get_float('MYSQL_EXECUTE_RETRY_DELAY', 0.2)
        
        # SQL 生成配置
        self.auto_update = self.settings.get_bool('MYSQL_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool('MYSQL_INSERT_IGNORE', False)
        self.update_columns = self._parse_update_columns(
            self.settings.get('MYSQL_UPDATE_COLUMNS', ())
        )
        
        # 其他配置
        self.check_table_exists = self.settings.get_bool('MYSQL_CHECK_TABLE_EXISTS', True)
    
    def _sanitize_table_name(self, name: str) -> str:
        """清理表名，移除非法字符"""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid table name: {name}")
        
        name = name.strip().replace(' ', '_').replace('-', '_')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValueError(f"Table name contains illegal characters: {name}")
        
        return name
    
    def _parse_update_columns(self, columns) -> tuple:
        """解析更新列配置"""
        if not columns:
            return ()
        if isinstance(columns, (list, tuple)):
            return tuple(columns)
        return (columns,)
    
    def _log_initialization(self):
        """记录初始化日志"""
        self.logger.info(
            f"MySQL Pipeline initialized - "
            f"host={self.settings.get('MYSQL_HOST', 'localhost')}:{self.settings.get('MYSQL_PORT', 3306)}, "
            f"database={self.settings.get('MYSQL_DB', 'crawlo_db')}, "
            f"table={self.table_name}, "
            f"batch_size={self.batch_size}, "
            f"batch_mode={'enabled' if self.use_batch else 'disabled'}"
        )
    
    def _validate_config(self) -> bool:
        """验证必要配置"""
        required = [
            ('MYSQL_HOST', self.settings.get('MYSQL_HOST', 'localhost')),
            ('MYSQL_DB', self.settings.get('MYSQL_DB', 'crawlo_db')),
            ('MYSQL_USER', self.settings.get('MYSQL_USER', 'root')),
        ]
        
        for name, value in required:
            if not value:
                self.logger.error(f"Missing required config: {name}")
                return False
        return True
    
    @staticmethod
    def _is_pool_active(pool) -> bool:
        return is_pool_active(pool)
    
    @staticmethod
    def _is_conn_active(conn) -> bool:
        if not conn:
            return False
        return not getattr(conn, '_closed', False)
    
    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理数据项"""
        await self._ensure_initialized()
        
        if self.use_batch:
            return await self._process_batch_item(item, spider)
        return await self._process_single_item(item, **kwargs)
    
    async def _process_batch_item(self, item: Item, spider) -> Item:
        """批量模式：添加到缓冲区"""
        async with self._pool_lock:
            self.batch_buffer.append(dict(item))
            should_flush = len(self.batch_buffer) >= self.batch_size
        
        if should_flush:
            try:
                await self._flush_batch(spider.name)
            except Exception as e:
                self.logger.warning(f"Batch flush failed: {e}")
        
        return item
    
    async def _process_single_item(self, item: Item, **kwargs) -> Item:
        """单条模式：直接插入（带重试）"""
        last_error = None
        
        for attempt in range(self.execute_max_retries):
            try:
                rowcount = await self._mysql_helper.insert(
                    table=self.table_name,
                    data=dict(item),
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                
                self._update_stats(rowcount, 1)
                return item
                
            except Exception as e:
                last_error = e
                result = MySQLErrorHandler.handle(e, self.crawler, item.get('pmid'))
                
                if result['action'] == 'skip':
                    return item
                
                if result['action'] == 'retry' and attempt < self.execute_max_retries - 1:
                    self.logger.warning(f"Insert failed, retrying ({attempt + 1}/{self.execute_max_retries}): {e}")
                    await asyncio.sleep(self.execute_retry_delay * (attempt + 1))
                    continue
                
                # 不重试，跳出循环
                break
        
        # 所有重试都失败了
        self.crawler.stats.inc_value('mysql/insert_failed')
        raise ItemDiscard(f"Insert failed after {self.execute_max_retries} retries: {last_error}")
    
    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区"""
        await self._ensure_initialized()
        
        # 获取并清空缓冲区
        async with self._pool_lock:
            if not self.batch_buffer:
                return
            batch = self.batch_buffer[:]
            self.batch_buffer.clear()
        
        if not batch:
            return
        
        try:
            rowcount = await self._mysql_helper.insert_many(
                table=self.table_name,
                datas=batch,
                auto_update=self.auto_update,
                update_columns=self.update_columns,
                insert_ignore=self.insert_ignore,
                batch_size=len(batch)
            )
            
            self._update_stats(rowcount, len(batch))
            
            if rowcount > 0:
                self.logger.info(f"Batch insert: {len(batch)} items, {rowcount} rows affected")
            
        except Exception as e:
            result = MySQLErrorHandler.handle(e, self.crawler)
            
            if result['action'] == 'retry':
                # 降级为单条插入
                await self._fallback_to_individual(batch)
            else:
                # 放回缓冲区重试
                async with self._pool_lock:
                    self.batch_buffer.extend(batch)
                raise ItemDiscard(f"Batch insert failed: {e}")
    
    async def _fallback_to_individual(self, datas: List[Dict]) -> int:
        """降级为单条插入"""
        total = 0
        failed = 0
        
        for data in datas:
            try:
                rowcount = await self._mysql_helper.insert(
                    table=self.table_name,
                    data=data,
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                total += rowcount or 0
            except Exception as e:
                result = MySQLErrorHandler.handle(e, self.crawler, data.get('pmid'))
                if result['action'] == 'raise':
                    failed += 1
        
        self.logger.info(f"Fallback insert: {len(datas)-failed} success, {failed} failed")
        return total
    
    def _update_stats(self, rowcount: int, requested: int):
        """更新统计信息"""
        self.crawler.stats.inc_value('mysql/insert_success')
        self.crawler.stats.inc_value('mysql/rows_requested', requested)
        self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
        
        if self.insert_ignore and rowcount < requested:
            ignored = requested - rowcount
            self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', ignored)
    
    async def _initialize_resources(self):
        """初始化资源"""
        await self._ensure_pool()
        self._mysql_helper = await MySQLHelper.get_instance(self.settings)
        
        if self.check_table_exists:
            await self._check_table_exists()
        
        if self.pool:
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.PIPELINE,
                name="mysql_pool"
            )
        
        await super()._initialize_resources()
    
    async def _cleanup_resources(self):
        """清理资源"""
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
        
        self.batch_buffer.clear()
        self._pool_initialized = False
        await super()._cleanup_resources()
    
    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                pool.close()
                await pool.wait_closed()
                self.logger.info("MySQL connection pool closed")
        except Exception as e:
            self.logger.error(f"Error closing pool: {e}")
    
    async def _check_table_exists(self):
        """检查表是否存在"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = DATABASE() AND table_name = %s",
                        (self.table_name,)
                    )
                    result = await cursor.fetchone()
                    exists = result[0] > 0 if result else False
                    
                    if not exists:
                        self.logger.warning(f"Table {self.table_name} does not exist")
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
    
    async def _ensure_pool(self):
        """确保连接池已初始化"""
        raise NotImplementedError("Subclasses must implement _ensure_pool")


class MySQLPipeline(BaseMySQLPipeline):
    """MySQL 管道实现（使用 asyncmy）"""
    
    @classmethod
    async def from_crawler(cls, crawler):
        return cls(crawler)
    
    async def _ensure_pool(self):
        """确保连接池已初始化"""
        if self._pool_initialized and self.pool and self._is_pool_active(self.pool):
            return
        
        if not self._validate_config():
            raise ValueError("MySQL config validation failed")
        
        async with self._pool_lock:
            if self._pool_initialized:
                return
            
            try:
                self.pool = await MySQLConnectionPoolManager.get_pool(
                    host=self.settings.get('MYSQL_HOST', 'localhost'),
                    port=self.settings.get_int('MYSQL_PORT', 3306),
                    user=self.settings.get('MYSQL_USER', 'root'),
                    password=self.settings.get('MYSQL_PASSWORD', ''),
                    db=self.settings.get('MYSQL_DB', 'scrapy_db'),
                    minsize=self.settings.get_int('MYSQL_POOL_MIN', 3),
                    maxsize=self.settings.get_int('MYSQL_POOL_MAX', 10),
                    echo=self.settings.get_bool('MYSQL_ECHO', False)
                )
                self._pool_initialized = True
                self.logger.debug("MySQL connection pool initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize pool: {e}")
                self._pool_initialized = False
                self.pool = None
                raise
