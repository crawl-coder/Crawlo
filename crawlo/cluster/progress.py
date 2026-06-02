#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
进度聚合器

汇总集群中各 Worker 的运行统计，提供全局可观测性。
基于 Redis HASH 存储全局统计和各 Worker 分项统计。

Key 设计：
    crawlo:{project}:{spider}:progress:stats   HASH  全局统计
    crawlo:{project}:{spider}:progress:items   HASH  各 Worker 产出统计
"""
import time
from typing import Dict, Any, Optional

from crawlo.logging import get_logger


class ProgressAggregator:
    """
    进度聚合器。

    使用示例：
        agg = ProgressAggregator(redis_client, key_manager)
        await agg.report("worker-001", {"completed": 10, "failed": 1})
        stats = await agg.get_global_stats()
        print(stats["total_completed"], stats["items_per_sec"])
    """

    def __init__(
        self,
        redis_client,
        key_manager,
        report_interval: int = 10,
    ):
        self._redis = redis_client
        self._km = key_manager
        self._report_interval = report_interval

        ns = key_manager.namespace
        self._stats_key = f"crawlo:{ns}:progress:stats"
        self._items_key = f"crawlo:{ns}:progress:items"
        # 记录首次上报时间，用于速率计算
        self._first_report_key = f"crawlo:{ns}:progress:first_report"

        self.logger = get_logger(self.__class__.__name__)

    # ---- Worker 上报 ----

    async def report(self, worker_id: str, stats: Dict[str, Any]):
        """
        Worker 上报进度。

        Args:
            worker_id: Worker 标识
            stats: 统计字段（completed/failed/processing 等）
        """
        # 全局累计统计（HINCRBY 原子增量）
        for field in ("completed", "failed", "items"):
            if field in stats:
                await self._redis.hincrby(
                    self._stats_key, f"total_{field}", int(stats[field])
                )

        # Worker 分项统计
        worker_data = {
            "last_report": time.time(),
            **{k: int(v) for k, v in stats.items() if isinstance(v, (int, float))},
        }
        import json
        await self._redis.hset(
            self._items_key,
            f"worker:{worker_id}",
            json.dumps(worker_data, ensure_ascii=False),
        )

        # 记录首次上报时间
        if not await self._redis.exists(self._first_report_key):
            await self._redis.set(self._first_report_key, time.time())

    # ---- 全局统计 ----

    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        stats = {
            "total_completed": 0,
            "total_failed": 0,
            "total_items": 0,
            "items_per_sec": 0,
            "elapsed": 0,
        }

        try:
            raw = await self._redis.hgetall(self._stats_key)
            for k, v in raw.items():
                k_str = k.decode("utf-8") if isinstance(k, bytes) else k
                v_int = int(v.decode("utf-8") if isinstance(v, bytes) else v)
                stats[k_str] = v_int

            # 计算速率
            first_ts = await self._redis.get(self._first_report_key)
            if first_ts:
                elapsed = time.time() - float(first_ts)
                stats["elapsed"] = round(elapsed, 1)
                if elapsed > 0 and stats["total_completed"] > 0:
                    stats["items_per_sec"] = round(stats["total_completed"] / elapsed, 2)
        except Exception:
            pass

        return stats

    async def get_worker_stats(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """获取指定 Worker 的统计"""
        import json
        raw = await self._redis.hget(self._items_key, f"worker:{worker_id}")
        if raw:
            raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            return json.loads(raw_str)
        return None

    async def get_all_workers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Worker 的统计"""
        import json
        raw = await self._redis.hgetall(self._items_key)
        result = {}
        for k, v in raw.items():
            k_str = k.decode("utf-8") if isinstance(k, bytes) else k
            v_str = v.decode("utf-8") if isinstance(v, bytes) else v
            result[k_str] = json.loads(v_str)
        return result

    async def estimate_completion(self, total_expected: int) -> Dict[str, Any]:
        """
        预估完成时间。

        Args:
            total_expected: 预期的总任务数

        Returns:
            {"eta": seconds, "eta_str": "Xh Ym", "percent": 45.2}
        """
        stats = await self.get_global_stats()
        completed = stats["total_completed"]
        rate = stats["items_per_sec"]

        if rate <= 0 or completed >= total_expected:
            return {"eta": 0, "eta_str": "N/A", "percent": 100.0 if completed > 0 else 0}

        remaining = total_expected - completed
        eta_seconds = remaining / rate

        hours = int(eta_seconds // 3600)
        minutes = int((eta_seconds % 3600) // 60)
        eta_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        return {
            "eta": round(eta_seconds),
            "eta_str": eta_str,
            "percent": round(completed / total_expected * 100, 1),
        }

    # ---- 重置 ----

    async def reset(self):
        """重置所有统计数据"""
        await self._redis.delete(self._stats_key, self._items_key, self._first_report_key)


__all__ = ["ProgressAggregator"]
