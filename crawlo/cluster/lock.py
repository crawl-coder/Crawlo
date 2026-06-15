#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
分布式锁

基于 Redis 的分布式锁（Redlock 简化版）。
使用 SET NX PX 原子操作 + Lua 脚本防误删。

使用示例：
    lock = DistributedLock(redis_client, "crawlo:project:lock:failover")
    holder = await lock.acquire(timeout=30)
    try:
        if holder:
            await do_critical_section()
    finally:
        await lock.release(holder)
"""
import asyncio
import uuid
import time
from typing import Optional

from crawlo.logging import get_logger


# Lua 脚本：原子释放锁（防误删）
_RELEASE_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class DistributedLock:
    """
    基于 Redis 的分布式锁。

    特性：
    - SET NX PX → 原子加锁 + 自动过期
    - Lua 脚本释放 → 防止误删他人持有的锁
    - 自动续期 → 长任务可 extend
    - 重试机制 → 竞争失败时自动重试
    """

    def __init__(
        self,
        redis_client,
        lock_name: str,
        default_timeout: int = 30,
        retry_count: int = 3,
        retry_delay: float = 0.5,
    ):
        """
        初始化分布式锁。

        Args:
            redis_client: Redis 异步客户端
            lock_name: 锁的唯一标识
            default_timeout: 默认锁超时时间（秒），超时后自动释放
            retry_count: 获取锁失败时的重试次数
            retry_delay: 重试间隔（秒）
        """
        self._redis = redis_client
        self._lock_key = f"crawlo:{lock_name}"
        self._default_timeout = default_timeout
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._holder_id: Optional[str] = None
        self._acquired = False

        self.logger = get_logger(self.__class__.__name__)

    # ---- 获取 / 释放 ----

    async def acquire(
        self,
        timeout: Optional[int] = None,
        retry: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ) -> Optional[str]:
        """
        获取锁。

        Returns:
            holder_id: 持有者标识（用于后续 release），获取失败返回 None
        """
        ttl = (timeout or self._default_timeout) * 1000  # ms
        max_retries = retry if retry is not None else self._retry_count
        delay = retry_delay if retry_delay is not None else self._retry_delay

        self._holder_id = str(uuid.uuid4())

        for attempt in range(max_retries + 1):
            try:
                result = await self._redis.set(
                    self._lock_key,
                    self._holder_id,
                    nx=True,
                    px=ttl,
                )
                if result:
                    self._acquired = True
                    self.logger.debug(
                        f"Lock acquired: {self._lock_key} (holder={self._holder_id[:8]})"
                    )
                    return self._holder_id
            except Exception as e:
                self.logger.warning(f"Lock acquire attempt {attempt + 1} failed: {e}")

            if attempt < max_retries:
                await asyncio.sleep(delay)

        self.logger.debug(f"Lock acquire failed after {max_retries} retries: {self._lock_key}")
        self._holder_id = None
        return None

    async def release(self, holder_id: Optional[str] = None):
        """
        释放锁（Lua 原子操作，防误删）。

        Args:
            holder_id: 持有者标识，None 则使用 acquire 时设置的
        """
        hid = holder_id or self._holder_id
        if not hid:
            return

        try:
            result = await self._redis.eval(_RELEASE_LUA, 1, self._lock_key, hid)
            if result:
                self.logger.debug(f"Lock released: {self._lock_key}")
            self._acquired = False
            self._holder_id = None
        except Exception as e:
            self.logger.warning(f"Lock release failed: {e}")

    async def extend(self, additional_time: int = 10):
        """
        续期锁（需要已持有锁）。

        Args:
            additional_time: 延长时间（秒）
        """
        if not self._acquired or not self._holder_id:
            return False

        try:
            # Lua: 只有当值匹配时才续期
            lua = """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("PEXPIRE", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            ttl_ms = additional_time * 1000
            result = await self._redis.eval(lua, 1, self._lock_key, self._holder_id, ttl_ms)
            return bool(result)
        except Exception as e:
            self.logger.warning(f"Lock extend failed: {e}")
            return False

    # ---- 状态查询 ----

    async def is_locked(self) -> bool:
        """查询锁是否被持有（不区分持有者）"""
        try:
            return await self._redis.exists(self._lock_key) > 0
        except Exception:
            return False

    @property
    def acquired(self) -> bool:
        """本实例是否持有锁"""
        return self._acquired

    @property
    def holder_id(self) -> Optional[str]:
        """本实例的持有者 ID"""
        return self._holder_id


__all__ = [
    "DistributedLock",
]
