# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from crawlo.utils.log import get_logger
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager
from crawlo.exceptions import ItemDiscard


class MongoPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 初始化连接参数
        self.client = None
        self.db = None
        self.collection = None

        # 配置默认值
        self.mongo_uri = self.settings.get('MONGO_URI', 'mongodb://localhost:27017')
        self.db_name = self.settings.get('MONGO_DATABASE', 'scrapy_db')
        self.collection_name = self.settings.get('MONGO_COLLECTION', crawler.spider.name)
        
        # 连接池配置
        self.max_pool_size = self.settings.getint('MONGO_MAX_POOL_SIZE', 100)
        self.min_pool_size = self.settings.getint('MONGO_MIN_POOL_SIZE', 10)
        self.connect_timeout_ms = self.settings.getint('MONGO_CONNECT_TIMEOUT_MS', 5000)
        self.socket_timeout_ms = self.settings.getint('MONGO_SOCKET_TIMEOUT_MS', 30000)

        # 批量插入配置
        self.batch_size = self.settings.getint('MONGO_BATCH_SIZE', 100)
        self.use_batch = self.settings.getbool('MONGO_USE_BATCH', False)
        self.batch_buffer: List[Dict] = []  # 批量缓冲区

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_connection(self):
        """确保连接已建立"""
        if self.client is None:
            # 使用单例连接池管理器
            self.client = await MongoConnectionPoolManager.get_client(
                mongo_uri=self.mongo_uri,
                db_name=self.db_name,
                max_pool_size=self.max_pool_size,
                min_pool_size=self.min_pool_size,
                connect_timeout_ms=self.connect_timeout_ms,
                socket_timeout_ms=self.socket_timeout_ms
            )
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.logger.info(
                f"MongoDB连接建立 (集合: {self.collection_name}, "
                f"使用全局共享连接池)"
            )

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法（带重试机制）"""
        # 如果启用批量插入，将item添加到缓冲区
        if self.use_batch:
            self.batch_buffer.append(dict(item))
            
            # 如果缓冲区达到批量大小，执行批量插入
            if len(self.batch_buffer) >= self.batch_size:
                await self._flush_batch(spider)
                
            return item
        else:
            # 单条插入逻辑
            try:
                await self._ensure_connection()

                item_dict = dict(item)

                # 带重试的插入操作
                for attempt in range(3):
                    try:
                        result = await self.collection.insert_one(item_dict)
                        # 统一使用insert_success统计键名
                        self.crawler.stats.inc_value('mongodb/insert_success')
                        self.logger.debug(f"插入成功 [attempt {attempt + 1}]: {result.inserted_id}")
                        return item
                    except PyMongoError as e:
                        if attempt == 2:  # 最后一次尝试仍失败
                            raise
                        self.logger.warning(f"插入重试中 [attempt {attempt + 1}]: {e}")

            except Exception as e:
                # 统一使用insert_failed统计键名
                self.crawler.stats.inc_value('mongodb/insert_failed')
                self.logger.error(f"MongoDB操作最终失败: {e}")
                raise ItemDiscard(f"MongoDB操作失败: {e}")

    async def _flush_batch(self, spider):
        """刷新批量缓冲区并执行批量插入"""
        if not self.batch_buffer:
            return

        try:
            await self._ensure_connection()

            # 带重试的批量插入操作
            for attempt in range(3):
                try:
                    result = await self.collection.insert_many(self.batch_buffer, ordered=False)
                    # 统一使用insert_success统计键名
                    inserted_count = len(result.inserted_ids)
                    self.crawler.stats.inc_value('mongodb/insert_success', inserted_count)
                    self.logger.debug(f"批量插入成功 [attempt {attempt + 1}]: {inserted_count} 条记录")
                    self.batch_buffer.clear()
                    return
                except PyMongoError as e:
                    if attempt == 2:  # 最后一次尝试仍失败
                        raise
                    self.logger.warning(f"批量插入重试中 [attempt {attempt + 1}]: {e}")
        except Exception as e:
            # 统一使用insert_failed统计键名
            failed_count = len(self.batch_buffer)
            self.crawler.stats.inc_value('mongodb/insert_failed', failed_count)
            self.logger.error(f"MongoDB批量插入最终失败: {e}")
            raise ItemDiscard(f"MongoDB批量插入失败: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        # 在关闭前刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            await self._flush_batch(self.crawler.spider)
        
        # 注意：不再关闭客户端，因为客户端是全局共享的
        # 客户端的关闭由 MongoConnectionPoolManager.close_all_clients() 统一管理
        if self.client:
            self.logger.info(
                f"MongoDB Pipeline 关闭，但保留全局共享连接池以供其他爬虫使用"
            )