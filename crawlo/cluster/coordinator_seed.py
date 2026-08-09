#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""ClusterMixin 种子锁子 Mixin（P2-6 从 coordinator.py 拆分）"""
from __future__ import annotations

import asyncio


class ClusterSeedMixin:
    """种子 URL 生成互斥（种子锁获取/续期/原子守卫）。"""

    async def _renew_seed_lock(self):
        """种子锁续期任务：每 60 秒延长锁 TTL，防止长时种子生成期间锁过期"""
        try:
            while self.running and self._seed_lock_key:
                await asyncio.sleep(60)
                if self._cluster_state.redis and self._seed_lock_key:
                    await self._cluster_state.redis.expire(self._seed_lock_key, 120)
        except asyncio.CancelledError:
            pass

    async def _try_acquire_seed_lock_atomic(
        self, seed_lock_key: str, project: str, spider_name: str
    ) -> bool:
        """
        原子地获取种子锁（含死锁清理 + 启动期协调）。

        修复分布式种子锁的关键竞态：
        - 抢锁前确认自己已写入 registry（避免 registry 读取空列表导致误判死锁）
        - 抢锁前短 sleep，让其他 worker 完成注册写入
        - Lua 已保证 active_count=0 时不清死锁；此处对 "暂无法判定" 的结果做重试
        """
        my_id = self._cluster_state.worker_id
        registry = self._cluster_state.registry
        redis = self._cluster_state.redis
        if redis is None:
            return False

        # 1. 等待自身注册可见（保证 list_workers 至少能看到自己，避免 active=[]）
        if registry is not None:
            for _ in range(20):  # 最多 2.0s
                try:
                    workers = await registry.list_workers() or []
                except Exception:
                    workers = []
                ids = [
                    w.get('worker_id') if isinstance(w, dict) else str(w)
                    for w in workers
                ]
                if my_id in ids:
                    break
                await asyncio.sleep(0.1)
            # 额外等待 0.3s，给其他刚启动的 worker 一个写入窗口（run_10_workers 间隔 1s）
            await asyncio.sleep(0.3)

        # 2. 带重试的抢锁：最多 5 次，每次间隔递增，覆盖活跃列表还没同步的情况
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                active_workers = []
                if registry is not None:
                    try:
                        workers = await registry.list_workers()
                        active_workers = [
                            w.get('worker_id') if isinstance(w, dict) else str(w)
                            for w in (workers or [])
                        ]
                        active_workers = [w for w in active_workers if w]
                    except Exception as e:
                        self.logger.debug(
                            f"Failed to list active workers for seed lock: {e}"
                        )

                args = [my_id, 120, len(active_workers)] + active_workers
                result = await redis.eval(self._SEED_LOCK_LUA, 1, seed_lock_key, *args)
                result_int = int(result) if result is not None else 0

                if result_int == 1:
                    self.logger.debug(
                        f"Acquired seed lock (fresh, attempt={attempt}): {seed_lock_key}"
                    )
                    return True
                if result_int == 2:
                    self.logger.info(
                        f"Cleared stale seed lock and acquired (attempt={attempt}): {seed_lock_key}"
                    )
                    return True
                # result_int == 0
                # 要么锁被活跃 worker 持有（正常情况，seed 由另一个 worker 生成）
                # 要么 active_count=0 时 Lua 拒绝清死锁（注册信息还没完整同步）
                # 做区分：如果锁 holder 就在活跃列表里 -> 直接放弃；否则重试
                if registry is not None and active_workers:
                    try:
                        holder = await redis.get(seed_lock_key)
                        if holder and holder in active_workers and holder != my_id:
                            self.logger.debug(
                                f"Seed lock held by active worker {holder}, skipping"
                            )
                            return False
                    except Exception:
                        pass
                if attempt < max_attempts:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                return False
            except Exception as e:
                self.logger.warning(
                    f"Atomic seed lock acquisition (attempt={attempt}/{max_attempts}) "
                    f"failed: {e}"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                # 最后一轮失败时使用 SETNX 保底
                try:
                    acquired = await redis.set(
                        seed_lock_key, my_id, nx=True, ex=120
                    )
                    return bool(acquired)
                except Exception as fallback_err:
                    self.logger.error(
                        f"Seed lock fallback SETNX failed: {fallback_err}"
                    )
                    return False
        return False

    # ========================================================================
    # 组件初始化
    # ========================================================================

