#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
心跳守护协程

周期性向 Redis 发送心跳，维持 Worker 的存活状态。
附带上报本节点的运行统计（处理中任务数、已完成任务数等）。
"""
import asyncio
import random
import traceback
from typing import Optional

from crawlo.logging import get_logger


class HeartbeatDaemon:
    """
    心跳守护协程。

    使用示例：
        daemon = HeartbeatDaemon(registry, worker_id, interval=15)
        task = asyncio.create_task(daemon.start())
        # ... 爬取运行中 ...
        await daemon.stop()
        task.cancel()
    """

    def __init__(
        self,
        registry,
        worker_id: str,
        interval: float = 15.0,
        jitter: float = 0.2,
    ):
        """
        初始化心跳守护。

        Args:
            registry: WorkerRegistry 实例
            worker_id: Worker ID
            interval: 心跳间隔（秒），默认 15s
            jitter: 随机偏移比例（±20%），防止心跳风暴
        """
        self._registry = registry
        self._worker_id = worker_id
        self._interval = interval
        self._jitter = jitter
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stats_provider = None  # 可注入的统计提供者

        self.logger = get_logger(self.__class__.__name__)

    # ---- 统计回调 ----

    def set_stats_provider(self, provider):
        """
        设置统计提供者（用于上报处理进度）。

        provider 应为具有以下属性的对象或函数：
            - tasks_processing: 当前处理中的任务数
            - tasks_completed: 已完成任务数
            - tasks_failed: 失败任务数
        或可调用对象，返回包含以上字段的 dict。
        """
        self._stats_provider = provider

    # ---- 启停 ----

    async def start(self):
        """
        启动心跳循环（作为后台协程运行）。

        Returns:
            asyncio.Task: 心跳协程
        """
        self._running = True
        self._task = asyncio.create_task(self._loop())
        self.logger.debug(
            f"Heartbeat daemon started for {self._worker_id} "
            f"(interval={self._interval}s, jitter={self._jitter * 100:.0f}%)"
        )
        return self._task

    async def stop(self):
        """停止心跳循环"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.debug(f"Heartbeat daemon stopped for {self._worker_id}")

    # ---- 内部循环 ----

    async def _loop(self):
        """心跳主循环"""
        while self._running:
            try:
                # 收集额外统计信息
                extra = self._collect_stats()

                # 发送心跳
                await self._registry.heartbeat(self._worker_id, extra=extra)

                # 计算下次心跳间隔（含 jitter）
                sleep_time = self._interval * (1.0 + random.uniform(-self._jitter, self._jitter))

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.warning(
                    f"Heartbeat failed for {self._worker_id}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                # 失败时不使用 jitter，缩短重试间隔
                sleep_time = min(self._interval, 5.0)

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                raise

    def _collect_stats(self) -> dict:
        """收集本节点的运行统计"""
        extra = {}
        if self._stats_provider:
            try:
                if callable(self._stats_provider):
                    extra = self._stats_provider()
                else:
                    for attr in ("tasks_completed", "tasks_failed", "tasks_processing"):
                        if hasattr(self._stats_provider, attr):
                            extra[attr] = getattr(self._stats_provider, attr)
            except Exception:
                pass
        return extra


__all__ = [
    "HeartbeatDaemon",
]
