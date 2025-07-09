#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
import aiomysql
from typing import Optional, List, Dict
from asyncmy import create_pool
from crawlo.utils.log import get_logger
from crawlo.exceptions import ItemDiscard


class AsyncmyMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        self.table_name = self.settings.get('MYSQL_TABLE', self.crawler.spider.name)

        # 批量处理相关
        self.batch_size = self.settings.get_int("MYSQL_BATCH_SIZE", 100)
        self.insert_queue: List[dict] = []

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        # crawler.subscriber.subscribe(self.flush_items, event='engine_stopped')  # 可选：引擎停止时也刷新

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized:
            return

        async with self._pool_lock:
            if not self._pool_initialized:  # 双重检查避免竞争条件
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

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的方法（加入队列）"""
        # 动态设置表名（可选）
        if not self.table_name:
            self.table_name = getattr(spider, 'mysql_table', self.settings.get('MYSQL_TABLE'))

        item_dict = dict(item)

        self.insert_queue.append(item_dict)

        if len(self.insert_queue) >= self.batch_size:
            await self.flush_items()

        return item

    async def flush_items(self):
        """执行批量插入"""
        if not self.insert_queue:
            return

        try:
            await self._ensure_pool()

            keys = self.insert_queue[0].keys()
            columns = ', '.join([f'`{k}`' for k in keys])
            placeholders = ', '.join(['%s'] * len(keys))
            values = [list(item.values()) for item in self.insert_queue]

            sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        await cursor.executemany(sql, values)
                        await conn.commit()
                        self.crawler.stats.inc_value(f'mysql/insert_success', count=len(self.insert_queue))
                        self.insert_queue.clear()
                    except Exception as e:
                        await conn.rollback()
                        self.crawler.stats.inc_value(f'mysql/insert_failed', count=len(self.insert_queue))
                        self.logger.error(f"批量插入失败: {e}")
                        raise ItemDiscard(f"批量插入失败: {e}")

        except Exception as e:
            self.logger.error(f"批量插入异常: {e}")
            raise ItemDiscard(f"批量写入失败: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源并刷新剩余数据"""
        await self.flush_items()
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("MySQL连接池已关闭")


class AiomysqlMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None

        # 批量处理相关
        self.batch_size = self.settings.getint("MYSQL_BATCH_SIZE", 100)
        self.insert_queue: List[Dict] = []

        # 表名配置
        self.table_name = self.settings.get(
            'MYSQL_TABLE',
            f"{self.crawler.spider.name}_items"
        )

        # 注册事件监听器
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        # crawler.subscriber.subscribe(self.flush_items, event='engine_stopped')  # 可选：引擎停止时也刷新数据

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
                        minsize=self.settings.getint('MYSQL_POOL_MIN', 2),
                        maxsize=self.settings.getint('MYSQL_POOL_MAX', 5),
                        cursorclass=aiomysql.DictCursor,
                        autocommit=False
                    )
                    self._pool_initialized = True
                    self.logger.debug(f"aiomysql连接池已初始化（表: {self.table_name}）")
                except Exception as e:
                    self.logger.error(f"aiomysql连接池初始化失败: {e}")
                    raise

    async def process_item(self, item, spider) -> Optional[Dict]:
        """将item加入队列，达到批量数量后执行插入"""
        # 动态设置表名（可选）
        if not self.table_name:
            self.table_name = getattr(spider, 'mysql_table', self.settings.get('MYSQL_TABLE'))

        item_dict = dict(item)
        self.insert_queue.append(item_dict)

        if len(self.insert_queue) >= self.batch_size:
            await self.flush_items()

        return item

    async def flush_items(self):
        """批量插入数据库"""
        if not self.insert_queue:
            return

        try:
            await self._init_pool()

            keys = self.insert_queue[0].keys()
            columns = ', '.join([f'`{k}`' for k in keys])
            placeholders = ', '.join(['%s'] * len(keys))
            values = [list(item.values()) for item in self.insert_queue]

            sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        await cursor.executemany(sql, values)
                        await conn.commit()
                        self.crawler.stats.inc_value('mysql/insert_success', count=len(self.insert_queue))
                        self.insert_queue.clear()
                    except aiomysql.Error as e:
                        await conn.rollback()
                        self.crawler.stats.inc_value('mysql/insert_failed', count=len(self.insert_queue))
                        self.logger.error(f"MySQL批量插入失败: {e}")
                        raise ItemDiscard(f"MySQL错误: {e.args[1]}")

        except Exception as e:
            self.logger.error(f"处理批量插入时发生异常: {e}")
            raise ItemDiscard(f"批量写入失败: {e}")

    async def spider_closed(self):
        """爬虫关闭时清空队列并释放资源"""
        await self.flush_items()
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("aiomysql连接池已释放")
