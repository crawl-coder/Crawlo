# -*- coding: utf-8 -*-
import asyncio
import aiomysql
from typing import Optional, List, Dict
from asyncmy import create_pool
from crawlo.utils.log import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.db_helper import make_insert_sql, make_batch_sql, logger


class AsyncmyMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        self.table_name = (
                self.settings.get('MYSQL_TABLE') or
                getattr(crawler.spider, 'mysql_table', None) or
                f"{crawler.spider.name}_items"
        )

        # 批量插入配置
        self.batch_size = self.settings.get_int('MYSQL_BATCH_SIZE', 100)
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        self.batch_buffer: List[Dict] = []  # 批量缓冲区

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

    async def process_item(self, item, spider, kwargs=None) -> Optional[dict]:
        """处理item的核心方法"""
        kwargs = kwargs or {}
        spider_name = getattr(spider, 'name', 'unknown')  # 获取爬虫名称
        
        # 如果启用批量插入，将item添加到缓冲区
        if self.use_batch:
            self.batch_buffer.append(dict(item))
            
            # 如果缓冲区达到批量大小，执行批量插入
            if len(self.batch_buffer) >= self.batch_size:
                await self._flush_batch(spider_name)
                
            return item
        else:
            # 单条插入逻辑
            try:
                await self._ensure_pool()
                item_dict = dict(item)
                sql = make_insert_sql(table=self.table_name, data=item_dict, **kwargs)

                rowcount = await self._execute_sql(sql=sql)
                if rowcount > 1:
                    self.logger.info(
                        f"爬虫 {spider_name} 成功插入 {rowcount} 条记录到表 {self.table_name}"
                    )
                elif rowcount == 1:
                    self.logger.debug(
                        f"爬虫 {spider_name} 成功插入单条记录到表 {self.table_name}"
                    )
                else:
                    self.logger.warning(
                        f"爬虫 {spider_name}: SQL执行成功但未插入新记录 - {sql[:100]}..."
                    )

                # 统计计数移到这里，与AiomysqlMySQLPipeline保持一致
                self.crawler.stats.inc_value('mysql/insert_success')
                return item

            except Exception as e:
                self.logger.error(f"处理item时发生错误: {e}")
                self.crawler.stats.inc_value('mysql/insert_failed')
                raise ItemDiscard(f"处理失败: {e}")

    async def _execute_sql(self, sql: str, values: list = None) -> int:
        """执行SQL语句并处理结果"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # 根据是否有参数值选择不同的执行方法
                    if values is not None:
                        rowcount = await cursor.execute(sql, values)
                    else:
                        rowcount = await cursor.execute(sql)

                    await conn.commit()
                    # 移除这里的统计计数
                    return rowcount
                except Exception as e:
                    await conn.rollback()
                    # 移除这里的统计计数
                    raise ItemDiscard(f"MySQL插入失败: {e}")

    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区并执行批量插入"""
        if not self.batch_buffer:
            return

        try:
            await self._ensure_pool()
            
            # 使用批量SQL生成函数
            batch_result = make_batch_sql(table=self.table_name, datas=self.batch_buffer)
            if batch_result is None:
                self.logger.warning("批量插入数据为空")
                self.batch_buffer.clear()
                return

            sql, values_list = batch_result

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        # 执行批量插入
                        rowcount = await cursor.executemany(sql, values_list)
                        await conn.commit()
                        
                        self.logger.info(
                            f"爬虫 {spider_name} 批量插入 {rowcount} 条记录到表 {self.table_name}"
                        )
                        # 更新统计计数
                        self.crawler.stats.inc_value('mysql/insert_success', rowcount)
                        self.batch_buffer.clear()
                    except Exception as e:
                        await conn.rollback()
                        self.crawler.stats.inc_value('mysql/insert_failed', len(self.batch_buffer))
                        self.logger.error(f"批量插入失败: {e}")
                        raise ItemDiscard(f"批量插入失败: {e}")
        except Exception as e:
            self.logger.error(f"批量插入过程中发生错误: {e}")
            raise ItemDiscard(f"批量插入处理失败: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        # 在关闭前刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
            
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("MySQL连接池已关闭")


class AiomysqlMySQLPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 使用异步锁和初始化标志
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        self.table_name = (
                self.settings.get('MYSQL_TABLE') or
                getattr(crawler.spider, 'mysql_table', None) or
                f"{crawler.spider.name}_items"
        )

        # 批量插入配置
        self.batch_size = self.settings.get_int('MYSQL_BATCH_SIZE', 100)
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        self.batch_buffer: List[Dict] = []  # 批量缓冲区

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

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法"""
        # 如果启用批量插入，将item添加到缓冲区
        if self.use_batch:
            self.batch_buffer.append(dict(item))
            
            # 如果缓冲区达到批量大小，执行批量插入
            if len(self.batch_buffer) >= self.batch_size:
                spider_name = getattr(spider, 'name', 'unknown')
                await self._flush_batch(spider_name)
                
            return item
        else:
            # 单条插入逻辑
            try:
                await self._init_pool()

                item_dict = dict(item)
                # 使用make_insert_sql工具函数生成SQL
                sql = make_insert_sql(table=self.table_name, data=item_dict)

                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        try:
                            await cursor.execute(sql)
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

    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区并执行批量插入"""
        if not self.batch_buffer:
            return

        try:
            await self._init_pool()
            
            # 使用批量SQL生成函数
            batch_result = make_batch_sql(table=self.table_name, datas=self.batch_buffer)
            if batch_result is None:
                self.logger.warning("批量插入数据为空")
                self.batch_buffer.clear()
                return

            sql, values_list = batch_result

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    try:
                        # 执行批量插入
                        rowcount = await cursor.executemany(sql, values_list)
                        await conn.commit()
                        
                        self.logger.info(
                            f"爬虫 {spider_name} 批量插入 {rowcount} 条记录到表 {self.table_name}"
                        )
                        # 更新统计计数
                        self.crawler.stats.inc_value('mysql/insert_success', rowcount)
                        self.batch_buffer.clear()
                    except Exception as e:
                        await conn.rollback()
                        self.crawler.stats.inc_value('mysql/insert_failed', len(self.batch_buffer))
                        self.logger.error(f"批量插入失败: {e}")
                        raise ItemDiscard(f"批量插入失败: {e}")
        except Exception as e:
            self.logger.error(f"批量插入过程中发生错误: {e}")
            raise ItemDiscard(f"批量插入处理失败: {e}")

    async def spider_closed(self):
        """资源清理"""
        # 在关闭前刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
            
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.logger.info("aiomysql连接池已释放")