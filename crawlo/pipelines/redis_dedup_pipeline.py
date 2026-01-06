#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 Redis 的数据项去重管道
========================
提供分布式环境下的数据项去重功能，防止保存重复的数据记录。

特点:
- 分布式支持: 多节点共享去重数据
- 高性能: 使用 Redis 集合进行快速查找
- 可配置: 支持自定义 Redis 连接参数
- 容错设计: 网络异常时不会丢失数据
"""
import redis
import hashlib
from typing import Optional

from crawlo import Item
from crawlo.spider import Spider
from crawlo.exceptions import ItemDiscard
from crawlo.logging import get_logger
from crawlo.utils.redis_manager import RedisKeyManager
from crawlo.pipelines.base_pipeline import DedupPipeline


class RedisDedupPipeline(DedupPipeline):
    """基于 Redis 的数据项去重管道"""

    def __init__(
            self,
            crawler,
            redis_host: str = 'localhost',
            redis_port: int = 6379,
            redis_db: int = 0,
            redis_password: Optional[str] = None,
            redis_key: str = 'crawlo:item_fingerprints'
    ):
        """
        初始化 Redis 去重管道
        
        :param crawler: Crawler实例
        :param redis_host: Redis 主机地址
        :param redis_port: Redis 端口
        :param redis_db: Redis 数据库编号
        :param redis_password: Redis 密码
        :param redis_key: 存储指纹的 Redis 键名
        """
        super().__init__(crawler)
        
        self.logger = get_logger(self.__class__.__name__)
        
        # 初始化 Redis 连接
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            raise RuntimeError(f"Redis 连接失败: {e}")

        self.redis_key = redis_key

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        # 使用统一的Redis key命名规范
        key_manager = RedisKeyManager.from_settings(settings)
        # 如果有spider，更新key_manager中的spider_name
        if hasattr(crawler, 'spider') and crawler.spider:
            spider_name = getattr(crawler.spider, 'name', None)
            if spider_name:
                key_manager.set_spider_name(spider_name)
        redis_key = key_manager.get_item_fingerprint_key()
        
        return cls(
            crawler=crawler,
            redis_host=settings.get('REDIS_HOST', 'localhost'),
            redis_port=settings.get_int('REDIS_PORT', 6379),
            redis_db=settings.get_int('REDIS_DB', 0),
            redis_password=settings.get('REDIS_PASSWORD') or None,
            redis_key=redis_key
        )

    async def _initialize_resources(self):
        """初始化资源"""
        # Redis连接已在__init__中创建，这里可以注册到资源管理器
        if self.redis_client:
            self.register_resource(
                resource=self.redis_client,
                cleanup_func=self._close_redis_client,
                name="redis_client"
            )
        # 调用父类的初始化方法
        await super()._initialize_resources()

    async def _close_redis_client(self, client):
        """关闭Redis客户端"""
        try:
            client.close()
            self.logger.info("Redis client closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis client: {e}")

    async def _cleanup_resources(self):
        """清理资源"""
        # 调用父类的清理方法
        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        """
        检查指纹是否已存在
        
        Args:
            fingerprint: 数据项指纹
            
        Returns:
            是否存在
        """
        try:
            # 使用 Redis 的 SISMEMBER 命令检查指纹是否存在
            exists = self.redis_client.sismember(self.redis_key, fingerprint)
            return bool(exists)
        except redis.RedisError as e:
            self.logger.error(f"Redis error checking fingerprint: {e}")
            # 在 Redis 错误时，假设指纹不存在，避免误删数据
            self.crawler.stats.inc_value('dedup/redis_error_count')
            return False

    async def _record_fingerprint(self, fingerprint: str) -> None:
        """
        记录指纹
        
        Args:
            fingerprint: 数据项指纹
        """
        try:
            # 使用 Redis 的 SADD 命令添加指纹
            self.redis_client.sadd(self.redis_key, fingerprint)
        except redis.RedisError as e:
            self.logger.error(f"Redis error recording fingerprint: {e}")
            self.crawler.stats.inc_value('dedup/redis_error_count')
            # 在 Redis 错误时，不抛出异常，避免影响爬虫运行

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        try:
            # 获取去重统计信息
            total_items = self.redis_client.scard(self.redis_key)
            self.logger.info(f"Spider {spider.name} closed:")
            self.logger.info(f"  - Dropped duplicate items: {self.dropped_count}")
            self.logger.info(f"  - Processed items: {self.processed_count}")
            self.logger.info(f"  - Fingerprints stored in Redis: {total_items}")
            
            # 注意：默认情况下不清理 Redis 中的指纹
            # 如果需要清理，可以在设置中配置
            # 安全访问crawler和settings
            crawler = getattr(spider, 'crawler', None)
            if crawler and hasattr(crawler, 'settings'):
                settings = crawler.settings
                if settings.getbool('REDIS_DEDUP_CLEANUP', False):
                    deleted = self.redis_client.delete(self.redis_key)
                    self.logger.info(f"  - Cleaned fingerprints: {deleted}")
        except Exception as e:
            self.logger.error(f"Error closing spider: {e}")