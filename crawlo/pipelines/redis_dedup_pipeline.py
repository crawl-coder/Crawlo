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
from typing import Optional

import redis.asyncio as aioredis

from crawlo.logging import get_logger
from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.spider import Spider
from crawlo.utils.redis_manager import RedisKeyManager


class RedisDedupPipeline(DedupPipeline):
    """基于 Redis 的数据项去重管道"""

    def __init__(
            self,
            crawler,
            redis_host: str = 'localhost',
            redis_port: int = 6379,
            redis_db: int = 0,
            redis_password: Optional[str] = None,
            redis_user: Optional[str] = None,  # 新增：Redis用户名
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
        
        # 初始化 Redis 连接参数（异步初始化在第一次使用时进行）
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.redis_user = redis_user
        self.redis_client = None  # 异步初始化

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
            redis_user=settings.get('REDIS_USER') or None,  # 新增：获取Redis用户名
            redis_key=redis_key
        )

    async def _ensure_redis_connection(self):
        """确保Redis连接已建立"""
        if self.redis_client is None:
            try:
                # 根据是否有用户名构建连接参数
                if self.redis_user and self.redis_password:
                    # 构建Redis URL以支持用户名认证
                    redis_url = f"redis://{self.redis_user}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
                    self.redis_client = aioredis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                else:
                    # 使用传统的密码认证方式
                    self.redis_client = aioredis.Redis(
                        host=self.redis_host,
                        port=self.redis_port,
                        db=self.redis_db,
                        password=self.redis_password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                
                # 测试连接
                await self.redis_client.ping()
                self.logger.info(f"Redis连接成功: {self.redis_host}:{self.redis_port}/{self.redis_db}")
            except Exception as e:
                self.logger.error(f"Redis connection failed: {e}")
                raise RuntimeError(f"Redis 连接失败: {e}")

    async def _initialize_resources(self):
        """初始化资源"""
        # 延迟初始化Redis连接，当第一次需要时再建立
        await self._ensure_redis_connection()
        
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
            # 确保连接可用
            await self._ensure_redis_connection()
            # 使用 Redis 的 SISMEMBER 命令检查指纹是否存在
            exists = await self.redis_client.sismember(self.redis_key, fingerprint)
            return bool(exists)
        except Exception as e:
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
            # 确保连接可用
            await self._ensure_redis_connection()
            # 使用 Redis 的 SADD 命令添加指纹
            await self.redis_client.sadd(self.redis_key, fingerprint)
        except Exception as e:
            self.logger.error(f"Redis error recording fingerprint: {e}")
            self.crawler.stats.inc_value('dedup/redis_error_count')
            # 在 Redis 错误时，不抛出异常，避免影响爬虫运行

    async def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        try:
            # 确保连接可用
            await self._ensure_redis_connection()
            # 获取去重统计信息
            total_items = await self.redis_client.scard(self.redis_key)
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
                    deleted = await self.redis_client.delete(self.redis_key)
                    self.logger.info(f"  - Cleaned fingerprints: {deleted}")
        except Exception as e:
            self.logger.error(f"Error closing spider: {e}")