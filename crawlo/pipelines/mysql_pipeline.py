# -*- coding: utf-8 -*-
import aiomysql
from typing import Optional
from asyncmy import create_pool
from crawlo.utils.log import get_logger
from crawlo.exceptions import ItemDiscard


class AsyncmyMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 初始化时暂不创建连接池（在process_item首次调用时创建）
        self.pool = None
        self.table_name = self.settings.get('MYSQL_TABLE', self.crawler.spider.name)

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    async def _ensure_pool(self):
        """确保连接池已初始化"""
        if self.pool is None:
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
            self.logger.info(f"MySQL连接池初始化完成（表: {self.table_name}）")

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法"""
        try:
            await self._ensure_pool()

            item_dict = dict(item)
            columns = ', '.join([f'`{k}`' for k in item_dict.keys()])
            placeholders = ', '.join(['%s'] * len(item_dict))

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        await cursor.execute(
                            f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})",
                            list(item_dict.values())
                        )
                        await conn.commit()
                    except Exception as e:
                        await conn.rollback()
                        self.logger.error(f"MySQL插入失败: {e}")
                        raise ItemDiscard(f"MySQL插入失败: {e}")

            return item

        except Exception as e:
            self.logger.error(f"处理item时发生错误: {e}")
            raise ItemDiscard(f"处理失败: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("MySQL连接池已关闭")


class AiomysqlMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        self.pool = None
        self.table_name = self.settings.get(
            'MYSQL_TABLE',
            f"{self.crawler.spider.name}_items"
        )

        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    async def _init_pool(self):
        """延迟初始化连接池"""
        if self.pool is None:
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
            self.logger.debug(f"aiomysql连接池已初始化（表: {self.table_name}）")

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        try:
            await self._init_pool()

            item_dict = dict(item)
            sql = f"""
            INSERT INTO `{self.table_name}` 
            ({', '.join([f'`{k}`' for k in item_dict.keys()])})
            VALUES ({', '.join(['%s'] * len(item_dict))})
            """

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        await cursor.execute(sql, list(item_dict.values()))
                        await conn.commit()
                        self.crawler.stats.inc_value('mysql/insert_success')
                    except aiomysql.Error as e:
                        await conn.rollback()
                        self.crawler.stats.inc_value('mysql/insert_failed')
                        raise ItemDiscard(f"MySQL错误: {e.args[1]}")

            return item

        except Exception as e:
            self.logger.error(f"Pipeline处理异常: {e}")
            raise ItemDiscard(f"处理失败: {e}")

    async def spider_closed(self):
        """资源清理"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("aiomysql连接池已释放")