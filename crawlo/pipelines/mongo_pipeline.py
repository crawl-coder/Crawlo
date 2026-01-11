# -*- coding: utf-8 -*-
import asyncio
from typing import Optional, List, Dict

from pymongo.errors import PyMongoError, BulkWriteError

from crawlo.exceptions import ItemDiscard
from crawlo.logging import get_logger
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager


class MongoPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

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

        # 添加锁用于初始化
        self._init_lock = asyncio.Lock()
        # 添加锁用于批量刷新，防止并发flush导致顺序混乱或竞争
        self._flush_lock = asyncio.Lock()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_connection(self):
        """确保连接已建立（线程安全）"""
        if self.client:
            return
            
        async with self._init_lock:
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
                if self.client is not None:
                    self.db = self.client[self.db_name]
                    self.collection = self.db[self.collection_name]
                    self.logger.info(
                        f"MongoDB连接建立 (集合: {self.collection_name}, "
                        f"使用全局共享连接池)"
                    )

    async def process_item(self, item, spider) -> Optional[dict]:
        """处理item的核心方法（带重试机制）"""
        # 1. 批量模式
        if self.use_batch:
            # 注意：append 是原子操作，不需要锁，但 flush 需要
            self.batch_buffer.append(dict(item))
            
            if len(self.batch_buffer) >= self.batch_size:
                # 触发刷新，但不阻塞当前 item 的返回（可选，取决于对数据一致性的要求）
                await self._flush_batch(spider)
            return item
            
        # 2. 单条模式
        else:
            try:
                await self._ensure_connection()
                
                # 检查连接是否有效
                if self.client is None or self.db is None or self.collection is None:
                    raise RuntimeError("MongoDB连接未正确初始化")

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
        """刷新批量缓冲区"""
        # 必须加锁，防止多个并发的 flush 操作
        if not self.batch_buffer:
            return

        async with self._flush_lock:
            if not self.batch_buffer:  # 双重检查
                return
            
            # 【关键修改】立即切出数据，清空缓冲区
            # 这样即使插入失败，缓冲区也被清空了，不会阻塞后续数据
            # 如果需要保留失败数据，应在 except 中处理，而不是默认保留
            current_batch = self.batch_buffer[:]
            self.batch_buffer.clear()

        try:
            await self._ensure_connection()
            if self.collection is None:
                raise RuntimeError("MongoDB未连接")

            # 带重试的批量插入
            for attempt in range(3):
                try:
                    # ordered=False 允许部分成功
                    result = await self.collection.insert_many(current_batch, ordered=False)
                    insert_count = len(result.inserted_ids)
                    self.crawler.stats.inc_value('mongodb/insert_success', insert_count)
                    self.logger.debug(f"批量插入成功: {insert_count} 条")
                    return # 成功退出
                    
                except BulkWriteError as bwe:
                    # 处理部分写入错误 (通常是唯一索引冲突)
                    inserted_count = bwe.details.get('nInserted', 0)
                    if inserted_count > 0:
                        self.crawler.stats.inc_value('mongodb/insert_success', inserted_count)
                    
                    # 记录重复/错误数量
                    failed_count = len(current_batch) - inserted_count
                    self.crawler.stats.inc_value('mongodb/insert_failed', failed_count)
                    self.logger.warning(f"批量插入部分失败 (忽略重试): 已插入 {inserted_count}, 失败 {failed_count}. 错误: {bwe}")
                    return # 部分失败通常不需要重试（特别是索引冲突），直接退出

                except PyMongoError as e:
                    if attempt == 2:
                        raise e # 最后一次重试失败，抛出给外层
                    self.logger.warning(f"批量插入重试中 [{attempt+1}/3]: {e}")
                    await asyncio.sleep(0.5 * (attempt + 1))

        except Exception as e:
            # 这里的异常是 3 次重试后的最终失败
            failed_count = len(current_batch)
            self.crawler.stats.inc_value('mongodb/insert_failed', failed_count)
            self.logger.error(f"MongoDB批量插入最终失败: {e}")
            
            # 【策略选择】是否要丢弃数据？
            # 当前逻辑是丢弃并报错。如果数据极其重要，可以考虑写到错误文件。
            raise ItemDiscard(f"批量插入失败，丢失 {failed_count} 条数据: {e}")

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        # 在关闭前刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            await self._flush_batch(self.crawler.spider)
        
        # 注意：不再关闭客户端，因为客户端是全局共享的
        # 客户端的关闭由 mongo_connection_pool.close_all_mongo_clients() 统一管理
        if self.client:
            self.logger.info(
                f"MongoDB Pipeline 关闭，但保留全局共享连接池以供其他爬虫使用"
            )