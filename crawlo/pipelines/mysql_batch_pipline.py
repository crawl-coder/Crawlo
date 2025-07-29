# -*- coding: utf-8 -*-
import asyncio
import aiomysql
from typing import Optional, List, Dict
from asyncmy import create_pool
from crawlo.utils.log import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.tools import make_insert_sql, logger


class AsyncmyMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 配置参数
        self.table_name = (
            self.settings.get('MYSQL_TABLE') or
            getattr(crawler.spider, 'mysql_table', None) or
            f"{crawler.spider.name}_items"
        )
        self.batch_size = self.settings.getint('MYSQL_BATCH_SIZE', 100)
        self.flush_interval = self.settings.getfloat('MYSQL_FLUSH_INTERVAL', 3.0)  # 秒

        # 连接池相关
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None

        # 缓冲区与锁
        self.items_buffer: List[Dict] = []
        self.buffer_lock = asyncio.Lock()

        # 后台任务
        self.flush_task: Optional[asyncio.Task] = None

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            return

        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    self.pool = await create_pool(
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
                    self.logger.debug(f"MySQL连接池初始化完成（表: {self.table_name}）")
                except Exception as e:
                    self.logger.error(f"MySQL连接池初始化失败: {e}")
                    raise

    async def open_spider(self, spider):
        """爬虫启动时初始化后台刷新任务"""
        await self._ensure_pool()
        self.flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self):
        """后台循环：定期检查是否需要刷新缓冲区"""
        while True:
            await asyncio.sleep(self.flush_interval)
            if len(self.items_buffer) > 0:
                await self._flush_buffer()

    async def _flush_buffer(self):
        """将缓冲区中的数据批量写入数据库"""
        async with self.buffer_lock:
            if not self.items_buffer:
                return

            items_to_insert = self.items_buffer.copy()
            self.items_buffer.clear()

        try:
            await self._ensure_pool()
            first_item = items_to_insert[0]
            sql = make_insert_sql(table=self.table_name, data=first_item, many=True)

            values = [list(item.values()) for item in items_to_insert]

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    affected_rows = await cursor.executemany(sql, values)
                    await conn.commit()

            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            self.logger.info(f"批量插入 {affected_rows} 条记录到 {self.table_name}")
            self.crawler.stats.inc_value('mysql/insert_success_batch', len(items_to_insert))

        except Exception as e:
            self.logger.error(f"批量插入失败: {e}")
            self.crawler.stats.inc_value('mysql/insert_failed_batch', len(items_to_insert))
            # 可选：重试或丢弃
            raise ItemDiscard(f"批量插入失败: {e}")

    async def process_item(self, item, spider, kwargs=None) -> dict:
        """将 item 添加到缓冲区，触发批量插入"""
        item_dict = dict(item)

        async with self.buffer_lock:
            self.items_buffer.append(item_dict)
            if len(self.items_buffer) >= self.batch_size:
                # 达到批量阈值，立即刷新
                await self._flush_buffer()

        return item

    async def spider_closed(self):
        """关闭爬虫时，确保所有剩余数据被写入"""
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        # 刷最后一批数据
        if self.items_buffer:
            await self._flush_buffer()

        # 关闭连接池
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("MySQL连接池已关闭")


class AiomysqlMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 配置
        self.table_name = (
            self.settings.get('MYSQL_TABLE') or
            getattr(crawler.spider, 'mysql_table', None) or
            f"{crawler.spider.name}_items"
        )
        self.batch_size = self.settings.getint('MYSQL_BATCH_SIZE', 100)
        self.flush_interval = self.settings.getfloat('MYSQL_FLUSH_INTERVAL', 3.0)

        # 连接池
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None

        # 缓冲
        self.items_buffer: List[Dict] = []
        self.buffer_lock = asyncio.Lock()

        # 后台任务
        self.flush_task: Optional[asyncio.Task] = None

        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    async def _init_pool(self):
        """延迟初始化连接池（线程安全）"""
        if self._pool_initialized:
            return

        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    self.pool = await aiomysql.create_pool(
                        host=self.settings.get('MYSQL_HOST', 'localhost'),
                        port=self.settings.getint('MYSQL_PORT', 3306),
                        user=self.settings.get('MYSQL_USER', 'root'),
                        password=self.settings.get('MYSQL_PASSWORD', ''),
                        db=self.settings.get('MYSQL_DB', 'scrapy_db'),
                        minsize=self.settings.getint('MYSQL_POOL_MIN', 3),
                        maxsize=self.settings.getint('MYSQL_POOL_MAX', 10),
                        cursorclass=aiomysql.DictCursor,
                        autocommit=False
                    )
                    self._pool_initialized = True
                    self.logger.debug(f"aiomysql连接池已初始化（表: {self.table_name}）")
                except Exception as e:
                    self.logger.error(f"aiomysql连接池初始化失败: {e}")
                    raise

    async def open_spider(self, spider):
        """爬虫启动时创建后台刷新任务"""
        await self._init_pool()
        self.flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self):
        """定期刷新缓冲区"""
        while True:
            await asyncio.sleep(self.flush_interval)
            if len(self.items_buffer) > 0:
                await self._flush_buffer()

    async def _flush_buffer(self):
        """执行批量插入"""
        async with self.buffer_lock:
            if not self.items_buffer:
                return
            items_to_insert = self.items_buffer.copy()
            self.items_buffer.clear()

        try:
            await self._init_pool()
            keys = items_to_insert[0].keys()
            placeholders = ', '.join(['%s'] * len(keys))
            columns = ', '.join([f'`{k}`' for k in keys])
            sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"

            values = [list(item.values()) for item in items_to_insert]

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    result = await cursor.executemany(sql, values)
                    await conn.commit()

            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            self.logger.info(f"【{spider_name}】批量插入 {result} 条记录到 {self.table_name}")
            self.crawler.stats.inc_value('mysql/insert_success_batch', len(items_to_insert))

        except aiomysql.Error as e:
            self.logger.error(f"aiomysql批量插入失败: {e}")
            self.crawler.stats.inc_value('mysql/insert_failed_batch', len(items_to_insert))
            raise ItemDiscard(f"MySQL错误: {e.args[1]}")
        except Exception as e:
            self.logger.error(f"未知错误: {e}")
            raise ItemDiscard(f"处理失败: {e}")

    async def process_item(self, item, spider) -> dict:
        item_dict = dict(item)

        async with self.buffer_lock:
            self.items_buffer.append(item_dict)
            if len(self.items_buffer) >= self.batch_size:
                await self._flush_buffer()

        return item

    async def spider_closed(self):
        """清理资源并提交剩余数据"""
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        if self.items_buffer:
            await self._flush_buffer()

        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("aiomysql连接池已释放")