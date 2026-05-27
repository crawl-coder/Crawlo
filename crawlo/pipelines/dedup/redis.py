#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 Redis 的数据项去重管道
========================
提供分布式环境下的数据项去重功能，防止保存重复的数据记录。

"""

from typing import Optional

from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.utils.redis import RedisConfig, RedisKeyManager, get_redis_pool


class RedisDedupPipeline(DedupPipeline):
    """基于 Redis 的数据项去重管道"""

    def __init__(
            self,
            crawler,
            redis_host: str = 'localhost',
            redis_port: int = 6379,
            redis_db: int = 0,
            redis_password: Optional[str] = None,
            redis_user: Optional[str] = None,
            redis_key: str = 'crawlo:item_fingerprints'
    ):
        super().__init__(crawler)
        
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.redis_user = redis_user
        self.redis_client = None
        self.redis_key = redis_key

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        key_manager = RedisKeyManager.from_settings(settings)
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
            redis_user=settings.get('REDIS_USER') or None,
            redis_key=redis_key
        )

    async def _ensure_redis_connection(self):
        """确保 Redis 连接已建立"""
        if self.redis_client is None:
            try:
                redis_config = RedisConfig(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    username=self.redis_user,
                    db=self.redis_db
                )
                redis_url = redis_config.to_url()
                redis_pool = get_redis_pool(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    shared=True  # 复用框架已有的连接池，避免重复创建
                )
                self.redis_client = await redis_pool.get_connection()
                await self.redis_client.ping()
            except Exception as e:
                self.logger.error(f"Redis connection failed: {e}")
                raise RuntimeError(f"Redis 连接失败: {e}")

    async def _initialize_resources(self):
        """初始化资源（保留：有实际连接建立逻辑）"""
        await self._ensure_redis_connection()
        if self.redis_client:
            self.register_resource(
                resource=self.redis_client,
                cleanup_func=self._close_redis_client,
                name="redis_client"
            )
        await super()._initialize_resources()

    async def _close_redis_client(self, client):
        """关闭 Redis 客户端"""
        try:
            client.close()
            self.logger.info("Redis client closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis client: {e}")

    async def _cleanup_resources(self):
        """清理资源 + 输出统计"""
        spider = getattr(self.crawler, 'spider', None)
        spider_name = getattr(spider, 'name', 'unknown') if spider else 'unknown'

        # 从未处理过 item，无需连接 Redis 仅为了统计
        if self.processed_count == 0:
            self.logger.debug(
                f"RedisDedupPipeline [{spider_name}] closed (no items processed)"
            )
            await super()._cleanup_resources()
            return

        try:
            await self._ensure_redis_connection()
            total_items = await self.redis_client.scard(self.redis_key)
            self.logger.debug(
                f"RedisDedupPipeline [{spider_name}] closed: "
                f"processed={self.processed_count}, dropped={self.dropped_count}, "
                f"redis_keys={total_items}"
            )

            # 可选清理
            if self.settings.get_bool('REDIS_DEDUP_CLEANUP', False):
                deleted = await self.redis_client.delete(self.redis_key)
                self.logger.info(f"  Cleaned fingerprints: {deleted}")
        except Exception as e:
            self.logger.error(f"RedisDedupPipeline cleanup error: {e}")

        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        try:
            await self._ensure_redis_connection()
            exists = await self.redis_client.sismember(self.redis_key, fingerprint)
            return bool(exists)
        except Exception as e:
            self.logger.error(f"Redis error checking fingerprint: {e}")
            self.crawler.stats.inc_value('dedup/redis_error_count')
            return False

    async def _record_fingerprint(self, fingerprint: str) -> None:
        try:
            await self._ensure_redis_connection()
            await self.redis_client.sadd(self.redis_key, fingerprint)
        except Exception as e:
            self.logger.error(f"Redis error recording fingerprint: {e}")
            self.crawler.stats.inc_value('dedup/redis_error_count')
