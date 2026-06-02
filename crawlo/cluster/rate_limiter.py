#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
分布式限流器

基于 Redis Lua 脚本的令牌桶算法，跨节点控制域名级请求速率。
所有 Worker 共享同一域名配额，解决多节点速率叠加问题。

Key 设计：
    crawlo:{project}:{spider}:rate:{domain}     String  令牌计数
    crawlo:{project}:{spider}:rate:{domain}:ts  String  上次补充时间戳
"""
import asyncio
import time
from typing import Dict, Optional

from crawlo.logging import get_logger


# Lua 脚本：原子令牌桶操作
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]          -- 令牌计数 Key
local ts_key = KEYS[2]       -- 时间戳 Key
local rate = tonumber(ARGV[1])     -- 每秒补充令牌数
local capacity = tonumber(ARGV[2]) -- 桶容量
local now = tonumber(ARGV[3])      -- 当前时间
local requested = tonumber(ARGV[4]) -- 请求的令牌数（默认 1）

local tokens = tonumber(redis.call('GET', key)) or capacity
local last_ts = tonumber(redis.call('GET', ts_key)) or now

-- 按时间差补充令牌
local elapsed = now - last_ts
tokens = math.min(capacity, tokens + elapsed * rate)

if tokens >= requested then
    redis.call('SET', key, tokens - requested)
    redis.call('SET', ts_key, now)
    return {1, math.floor(tokens - requested)}  -- 允许, 剩余令牌
else
    redis.call('SET', key, tokens)
    redis.call('SET', ts_key, now)
    -- 计算需要等待的时间
    local wait_time = (requested - tokens) / rate
    return {0, math.floor(tokens), math.ceil(wait_time * 1000)}  -- 拒绝, 当前令牌, wait_ms
end
"""


class DistributedRateLimiter:
    """
    跨节点的分布式限流（Redis 令牌桶）。

    使用示例：
        limiter = DistributedRateLimiter(redis_client, "crawlo:project")
        # 限速 2 req/s，允许突发 5 个
        allowed = await limiter.acquire("example.com", rate=2.0, capacity=5)
        if not allowed:
            await limiter.wait_and_acquire("example.com", rate=2.0, timeout=10)
    """

    def __init__(
        self,
        redis_client,
        namespace: str,
        enabled: bool = True,
        default_rate: float = 0,
        default_capacity: int = 10,
    ):
        """
        初始化分布式限流器。

        Args:
            redis_client: Redis 异步客户端
            namespace: 命名空间（如 "crawlo:project:spider"）
            enabled: 是否启用（False 时所有请求放行）
            default_rate: 默认速率（req/s），0 = 不限
            default_capacity: 默认桶容量（允许突发）
        """
        self._redis = redis_client
        self._ns = namespace
        self._enabled = enabled
        self._default_rate = default_rate
        self._default_capacity = default_capacity

        # 域名级速率覆盖
        self._domain_rates: Dict[str, float] = {}
        self._domain_capacities: Dict[str, int] = {}

        self.logger = get_logger(self.__class__.__name__)

    # ---- 令牌申请 ----

    async def acquire(
        self,
        domain: str,
        rate: Optional[float] = None,
        capacity: Optional[int] = None,
        count: int = 1,
    ) -> bool:
        """
        申请令牌（非阻塞）。

        Args:
            domain: 域名
            rate: 速率（req/s），None 则使用默认值
            capacity: 桶容量，None 则使用默认值
            count: 请求的令牌数

        Returns:
            True = 允许，False = 拒绝（需等待）
        """
        if not self._enabled:
            return True

        effective_rate = rate or self._domain_rates.get(domain, self._default_rate)
        if effective_rate <= 0:
            return True  # 不限速

        effective_capacity = capacity or self._domain_capacities.get(domain, self._default_capacity)

        key = f"{self._ns}:rate:{domain}"
        ts_key = f"{key}:ts"

        try:
            result = await self._redis.eval(
                _TOKEN_BUCKET_LUA, 2,
                key, ts_key,
                effective_rate, effective_capacity, time.time(), count,
            )
            return result[0] == 1
        except Exception as e:
            self.logger.debug(f"Rate limiter check failed for {domain}: {e}")
            return True  # 降级：Redis 不可用时放行

    async def wait_and_acquire(
        self,
        domain: str,
        rate: Optional[float] = None,
        capacity: Optional[int] = None,
        timeout: float = 30.0,
        count: int = 1,
    ) -> bool:
        """
        阻塞等待直到获取令牌（带超时）。

        Args:
            domain: 域名
            rate: 速率
            capacity: 桶容量
            timeout: 最大等待时间（秒）
            count: 请求的令牌数

        Returns:
            True = 成功获取，False = 超时
        """
        if not self._enabled:
            return True

        effective_rate = rate or self._domain_rates.get(domain, self._default_rate)
        if effective_rate <= 0:
            return True

        effective_capacity = capacity or self._domain_capacities.get(domain, self._default_capacity)
        key = f"{self._ns}:rate:{domain}"
        ts_key = f"{key}:ts"

        start = time.time()

        while True:
            try:
                result = await self._redis.eval(
                    _TOKEN_BUCKET_LUA, 2,
                    key, ts_key,
                    effective_rate, effective_capacity, time.time(), count,
                )
                if result[0] == 1:
                    return True

                # 计算等待时间
                wait_ms = result[2] if len(result) > 2 else 100
                wait_s = max(0.05, min(wait_ms / 1000, 2.0))  # 最多等 2s

                if time.time() - start >= timeout:
                    return False

                await asyncio.sleep(wait_s)

            except Exception as e:
                self.logger.debug(f"Rate limiter wait failed: {e}")
                return True  # 降级放行

    # ---- 配置 ----

    async def set_rate(self, domain: str, rate: float, capacity: Optional[int] = None):
        """
        动态调整域名级速率。

        Args:
            domain: 域名
            rate: 新速率（req/s），0 = 不限
            capacity: 桶容量
        """
        self._domain_rates[domain] = rate
        if capacity is not None:
            self._domain_capacities[domain] = capacity
        self.logger.info(f"Rate limit updated: {domain} -> {rate} req/s")

    async def remove_rate(self, domain: str):
        """移除域名级速率限制"""
        self._domain_rates.pop(domain, None)
        self._domain_capacities.pop(domain, None)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def default_rate(self) -> float:
        return self._default_rate

    @default_rate.setter
    def default_rate(self, value: float):
        self._default_rate = value


__all__ = ["DistributedRateLimiter"]
