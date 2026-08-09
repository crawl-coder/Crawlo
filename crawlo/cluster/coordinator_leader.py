#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""ClusterMixin Leader 子 Mixin（P2-6 从 coordinator.py 拆分）"""
from __future__ import annotations

import asyncio
from crawlo.utils.misc import safe_get_config


class ClusterLeaderMixin:
    """Leader 锁获取/释放、协调退出循环与退出条件检查。"""

    async def _leader_shutdown_loop(self):
        """Leader Worker 协调退出后台循环"""
        if not self._cluster_state.dynamic_config or not self._cluster_state.leader_lock:
            return

        leader_lock_ttl = safe_get_config(
            self.settings, 'CLUSTER_HEARTBEAT_INTERVAL', 15, int
        ) * 2
        check_interval = 10

        while self.running:
            try:
                if not await self._try_acquire_leader_lock(leader_lock_ttl):
                    await asyncio.sleep(check_interval)
                    continue

                # 已由其他 Leader 触发退出，直接停止
                control_state = await self._cluster_state.dynamic_config.get_control_state()
                if control_state == "shutdown":
                    self.running = False
                    break

                if not await self._check_leader_shutdown_conditions():
                    await asyncio.sleep(check_interval)
                    continue

                self.logger.warning(
                    "Coordinated shutdown: all tasks complete, all workers idle, "
                    "broadcasting shutdown signal"
                )
                await self._cluster_state.dynamic_config.shutdown_cluster(cleanup=False)
                self.running = False
                break

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.debug(f"Leader shutdown loop error: {e}")
                await asyncio.sleep(5)

    # ========================================================================
    # Leader 锁操作
    # ========================================================================

    async def _try_acquire_leader_lock(self, ttl: int) -> bool:
        """
        尝试获取或续期 Leader 锁。

        使用 DistributedLock 提供的原子操作：
        - acquire() → SET NX PX（原子获取 + 自动过期）
        - extend()  → Lua 脚本检查持有者身份后 PEXPIRE（原子续期，防误续他人锁）
        """
        if not self._cluster_state.leader_lock:
            return False
        try:
            if self._cluster_state.leader_lock.acquired and self._cluster_state.leader_lock.holder_id:
                if await self._cluster_state.leader_lock.extend(ttl):
                    return True
            result = await self._cluster_state.leader_lock.acquire(timeout=ttl, retry=1)
            return result is not None
        except Exception:
            return False

    async def _release_leader_lock(self):
        """释放 Leader 锁（Lua 脚本原子释放，防误删他人持有的锁）"""
        if not self._cluster_state.leader_lock:
            return
        try:
            await self._cluster_state.leader_lock.release()
        except Exception:
            pass

    # ========================================================================
    # 退出条件
    # ========================================================================

    async def _check_leader_shutdown_conditions(self) -> bool:
        """
        检查协调退出的前置条件：

        1. 所有种子 URL 已生成完毕（_start_requests_source 已耗尽）
        2. 队列为空（无待处理请求）
        3. 当前 Worker 无在途后台任务
        4. 短暂等待后重检队列（防止瞬态误判）
        5. 所有已注册 Worker 均空闲（tasks_processing == 0）
        """
        if self._start_requests_source is not None:
            return False

        if self.scheduler and self.scheduler.queue_manager:
            is_empty = await self.scheduler.async_idle()
            if not is_empty:
                return False

        if len(self._background_tasks) > 0:
            return False

        await asyncio.sleep(2)

        if self.scheduler and self.scheduler.queue_manager:
            is_empty = await self.scheduler.async_idle()
            if not is_empty:
                self.logger.debug("Coordinated shutdown re-check: queue not empty, postponing")
                return False

        if self._cluster_state.registry:
            try:
                active_workers = await self._cluster_state.registry.get_active_workers()
                for worker in active_workers:
                    wid = worker.get("id", "")
                    if wid == self._cluster_state.worker_id:
                        continue
                    processing = worker.get("tasks_processing", 1)
                    if processing > 0:
                        self.logger.debug(
                            f"Coordinated shutdown: worker {wid} still processing "
                            f"{processing} tasks"
                        )
                        return False
            except Exception as e:
                self.logger.debug(f"Coordinated shutdown worker check error: {e}")
                return False

        return True

    # ========================================================================
    # 关闭与 Drain
    # ========================================================================
