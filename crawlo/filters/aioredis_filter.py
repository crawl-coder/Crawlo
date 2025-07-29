#!/usr/bin/python
# -*- coding:UTF-8 -*-
import aioredis
from typing import Optional
from crawlo import Request
from crawlo.filters import BaseFilter
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint


class AioRedisFilter(BaseFilter):
    """基于Redis集合实现的异步请求去重过滤器（支持分布式爬虫），提供TTL和清理控制"""

    def __init__(
            self,
            redis_key: str,
            client: aioredis.Redis,
            stats: dict,
            debug: bool,
            log_level: str,
            cleanup_fp: bool = False,
            ttl: Optional[int] = None
    ):
        """初始化过滤器"""
        self.logger = get_logger(self.__class__.__name__, log_level)
        super().__init__(self.logger, stats, debug)

        self.redis_key = redis_key
        self.redis = client
        self.cleanup_fp = cleanup_fp
        self.ttl = ttl

    @classmethod
    def create_instance(cls, crawler) -> 'BaseFilter':
        """从爬虫配置创建过滤器实例"""
        redis_url = crawler.settings.get('REDIS_URL', 'redis://localhost:6379')
        decode_responses = crawler.settings.get_bool('DECODE_RESPONSES', False)
        ttl_setting = crawler.settings.get_int('REDIS_TTL')

        # 处理TTL设置
        ttl = None
        if ttl_setting is not None:
            ttl = max(0, int(ttl_setting)) if ttl_setting > 0 else None

        try:
            redis_client = aioredis.from_url(
                redis_url,
                decode_responses=decode_responses,
                max_connections=20,
                encoding='utf-8'
            )
        except Exception as e:
            raise RuntimeError(f"Redis连接失败: {redis_url} - {str(e)}")

        return cls(
            redis_key=f"{crawler.settings.get('PROJECT_NAME', 'default')}:{crawler.settings.get('REDIS_KEY', 'request_fingerprints')}",
            client=redis_client,
            stats=crawler.stats,
            cleanup_fp=crawler.settings.get_bool('CLEANUP_FP', False),
            ttl=ttl,
            debug=crawler.settings.get_bool('FILTER_DEBUG', False),
            log_level=crawler.settings.get('LOG_LEVEL', 'INFO')
        )

    async def requested(self, request: Request) -> bool:
        """检查请求是否已存在"""
        try:
            fp = str(request_fingerprint(request))

            # 1. 检查指纹是否存在
            pipe = self.redis.pipeline()
            pipe.sismember(self.redis_key, fp)  # 不单独 await
            exists = (await pipe.execute())[0]  # 执行并获取结果

            if exists:  # 如果已存在，返回 True
                return True

            # 2. 如果不存在，添加指纹并设置 TTL
            pipe = self.redis.pipeline()
            pipe.sadd(self.redis_key, fp)  # 不单独 await
            if self.ttl and self.ttl > 0:
                pipe.expire(self.redis_key, self.ttl)  # 不单独 await
            await pipe.execute()  # 一次性执行所有命令

            return False  # 表示是新请求

        except Exception as e:
            self.logger.error(f"请求检查失败: {getattr(request, 'url', '未知URL')}")
            raise

    async def add_fingerprint(self, fp: str) -> bool:
        """添加新指纹到Redis集合"""
        try:
            fp = str(fp)
            added = await self.redis.sadd(self.redis_key, fp)

            if self.ttl and self.ttl > 0:
                await self.redis.expire(self.redis_key, self.ttl)

            return added == 1
        except Exception as e:
            self.logger.error("添加指纹失败")
            raise

    async def get_stats(self) -> dict:
        """获取过滤器统计信息"""
        try:
            count = await self.redis.scard(self.redis_key)
            stats = {
                '指纹总数': count,
                'Redis键名': self.redis_key,
                'TTL配置': f"{self.ttl}秒" if self.ttl else "持久化"
            }
            stats.update(self.stats)
            return stats
        except Exception as e:
            self.logger.error("获取统计信息失败")
            return self.stats

    async def clear_all(self) -> int:
        """清空所有指纹数据"""
        try:
            deleted = await self.redis.delete(self.redis_key)
            self.logger.info(f"已清除指纹数: {deleted}")
            return deleted
        except Exception as e:
            self.logger.error("清空指纹失败")
            raise

    async def closed(self, reason: Optional[str] = None) -> None:
        """爬虫关闭时的清理操作"""
        try:
            if self.cleanup_fp:
                deleted = await self.redis.delete(self.redis_key)
                self.logger.info(f"爬虫关闭清理: 已删除{deleted}个指纹")
            else:
                count = await self.redis.scard(self.redis_key)
                ttl_info = f"{self.ttl}秒" if self.ttl else "持久化"
                self.logger.info(f"保留指纹数: {count} (TTL: {ttl_info})")
        finally:
            await self._close_redis()

    async def _close_redis(self) -> None:
        """安全关闭Redis连接"""
        try:
            if hasattr(self.redis, 'close'):
                await self.redis.close()
                self.logger.debug("Redis连接已关闭")
        except Exception as e:
            self.logger.warning(f"Redis关闭时出错：{e}")
