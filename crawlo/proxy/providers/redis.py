#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:13
# @Author  :   crawl-coder
# @Desc    :   None
"""
import aioredis
from typing import List

from .base import BaseProxyProvider


class RedisProxyProvider(BaseProxyProvider):
    """从 Redis 列表中获取代理"""
    def __init__(self, redis_url: str, key: str = "proxies", decode_responses: bool = True):
        self.redis_url = redis_url
        self.key = key
        self.decode_responses = decode_responses
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=self.decode_responses
            )
        return self._redis

    async def fetch_proxies(self) -> List[str]:
        try:
            r = await self._get_redis()
            return await r.lrange(self.key, 0, -1)
        except Exception as e:
            print(f"[RedisProxyProvider] Redis 错误 {self.redis_url}: {e}")
            return []