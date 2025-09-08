# -*- coding: utf-8 -*-
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from crawlo.utils.log import get_logger
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

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_connection(self):
        """确保连接已建立"""
        if self.client is None:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.logger.info(f"MongoDB连接建立 (集合: {self.collection_name})")

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法"""
        try:
            await self._ensure_connection()

            item_dict = dict(item)
            result = await self.collection.insert_one(item_dict)

            # 统计计数
            self.crawler.stats.inc_value('mongodb/inserted')
            self.logger.debug(f"插入文档ID: {result.inserted_id}")

            return item

        except Exception as e:
            self.crawler.stats.inc_value('mongodb/failed')
            self.logger.error(f"MongoDB插入失败: {e}")
            raise ItemDiscard(f"MongoDB操作失败: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB连接已关闭")


class MongoPoolPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get('LOG_LEVEL'))

        # 连接池配置
        self.client = AsyncIOMotorClient(
            self.settings.get('MONGO_URI', 'mongodb://localhost:27017'),
            maxPoolSize=self.settings.getint('MONGO_MAX_POOL_SIZE', 100),
            minPoolSize=self.settings.getint('MONGO_MIN_POOL_SIZE', 10),
            connectTimeoutMS=5000,
            socketTimeoutMS=30000
        )

        self.db = self.client[self.settings.get('MONGO_DATABASE', 'scrapy_db')]
        self.collection = self.db[self.settings.get('MONGO_COLLECTION', crawler.spider.name)]

        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')
        self.logger.info(f"MongoDB连接池已初始化 (集合: {self.collection.name})")

    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item方法（带重试机制）"""
        try:
            item_dict = dict(item)

            # 带重试的插入操作
            for attempt in range(3):
                try:
                    result = await self.collection.insert_one(item_dict)
                    self.crawler.stats.inc_value('mongodb/insert_success')
                    self.logger.debug(f"插入成功 [attempt {attempt + 1}]: {result.inserted_id}")
                    return item
                except PyMongoError as e:
                    if attempt == 2:  # 最后一次尝试仍失败
                        raise
                    self.logger.warning(f"插入重试中 [attempt {attempt + 1}]: {e}")

        except Exception as e:
            self.crawler.stats.inc_value('mongodb/insert_failed')
            self.logger.error(f"MongoDB操作最终失败: {e}")
            raise ItemDiscard(f"MongoDB操作失败: {e}")

    async def spider_closed(self):
        """资源清理"""
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("MongoDB连接池已释放")