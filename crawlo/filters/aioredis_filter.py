#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional

import aioredis

from crawlo import Request
from crawlo.filters import BaseFilter
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint


class AioRedisFilter(BaseFilter):
    """使用Redis集合实现的异步请求去重过滤器（适用于分布式爬虫）"""

    def __init__(
            self,
            redis_key: str,
            client: aioredis.Redis,
            stats: dict,
            debug: bool,
            log_level: str,
            cleanup_fp: bool = False
    ):
        """
        初始化过滤器

        参数说明:
            redis_key: Redis中存储指纹的键名
            client: aioredis客户端实例
            stats: 统计信息字典
            debug: 是否启用调试模式
            log_level: 日志级别
            save_fp: 爬虫关闭时是否保留指纹数据
        """
        # 初始化日志记录器（使用类名作为日志标识）
        self.logger = get_logger(self.__class__.__name__, log_level)
        super().__init__(self.logger, stats, debug)

        self.redis_key = redis_key  # Redis存储键（如："project:request_fingerprints"）
        self.redis = client  # Redis异步客户端
        self.cleanup_fp = cleanup_fp  # 是否持久化指纹数据

    @classmethod
    def create_instance(cls, crawler) -> 'BaseFilter':
        """从爬虫配置创建过滤器实例（工厂方法）"""
        # 从配置获取Redis连接参数（带默认值）
        redis_url = crawler.settings.get('REDIS_URL', 'redis://localhost:6379')
        decode_responses = crawler.settings.get_bool('DECODE_RESPONSES', True)

        try:
            # 创建Redis连接池（限制最大连接数20）
            redis_client = aioredis.from_url(
                redis_url,
                decode_responses=decode_responses,
                max_connections=20
            )
        except Exception as e:
            raise RuntimeError(f"Redis连接失败 {redis_url}: {str(e)}")

        # 使用项目名+配置键组合作为Redis键
        return cls(
            redis_key=f"{crawler.settings.get('PROJECT_NAME')}:{crawler.settings.get('REDIS_KEY', 'request_fingerprints')}",
            client=redis_client,
            stats=crawler.stats,
            cleanup_fp=crawler.settings.get_bool('CLEANUP_FP', False),
            debug=crawler.settings.get_bool('FILTER_DEBUG', False),
            log_level=crawler.settings.get('LOG_LEVEL', 'INFO')
        )

    async def requested(self, request: Request) -> bool:
        """
        检查请求是否重复

        参数:
            request: 要检查的请求对象

        返回:
            bool: True表示重复请求，False表示新请求
        """
        fp = request_fingerprint(request)  # 生成请求指纹
        try:
            # 检查指纹是否已存在集合中
            is_duplicate = await self.redis.sismember(self.redis_key, fp)
            if is_duplicate:
                # self.logger.debug(f"发现重复请求: {fp}")
                return True

            # 新请求则添加指纹
            await self.add_fingerprint(fp)
            return False
        except aioredis.RedisError as e:
            self.logger.error(f"Redis操作失败: {str(e)}")
            raise  # 向上抛出异常

    async def add_fingerprint(self, fp: str) -> None:
        """向Redis集合添加新指纹"""
        try:
            await self.redis.sadd(self.redis_key, fp)
            self.logger.debug(f"新增指纹: {fp}")
        except aioredis.RedisError as e:
            self.logger.error(f"指纹添加失败: {str(e)}")
            raise

    async def closed(self, reason: Optional[str] = None) -> None:
        """
        爬虫关闭时的处理（兼容Scrapy的关闭逻辑）

        参数:
            reason: 爬虫关闭原因（Scrapy标准参数）
        """
        if self.cleanup_fp:  # 仅在配置明确要求时清理
            try:
                deleted = await self.redis.delete(self.redis_key)
                self.logger.info(
                    f"Cleaned {deleted} fingerprints from {self.redis_key} "
                    f"(reason: {reason or 'manual'})"
                )
            except aioredis.RedisError as e:
                self.logger.warning(f"Cleanup failed: {e}")
            finally:
                await self._close_redis()

    async def _close_redis(self) -> None:
        """安全关闭Redis连接"""
        try:
            await self.redis.close()
            await self.redis.connection_pool.disconnect()
        except Exception as e:
            self.logger.warning(f"Redis close error: {e}")