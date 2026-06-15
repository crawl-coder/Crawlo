#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
集群监控

提供集群状态总览、队列详情、Worker 列表、Pending 任务查询等功能。
聚合 WorkerRegistry + ProgressAggregator + Stream Queue 的数据。
"""
from typing import Dict, Any, List

from crawlo.logging import get_logger


class ClusterMonitor:
    """
    集群监控。

    使用示例：
        monitor = ClusterMonitor(registry, progress, stream_queue, failover)
        status = await monitor.status()
        print(status["workers"]["active"], status["queue"]["pending"])
    """

    def __init__(
        self,
        registry,
        progress_aggregator,
        stream_queue=None,
        failover_manager=None,
    ):
        self._registry = registry
        self._progress = progress_aggregator
        self._stream_queue = stream_queue
        self._failover = failover_manager

        self.logger = get_logger(self.__class__.__name__)

    # ---- 状态总览 ----

    async def status(self) -> Dict[str, Any]:
        """
        集群状态总览。

        Returns:
            {
                "workers": {"active": N, "idle": M, "total": K},
                "queue": {"pending": X, "processing": Y, "failed": Z},
                "progress": {"completed": A, "items_per_sec": B, "elapsed": C},
                "dead_letter": {"total": D},
            }
        """
        # Worker 统计
        active_workers = await self._registry.get_active_workers() if self._registry else []
        idle_count = sum(1 for w in active_workers if w.get("status") == "idle")
        total_workers = len(active_workers)

        # 队列统计
        pending = await self._stream_queue.size() if self._stream_queue else 0
        processing = 0
        if self._stream_queue:
            info = await self._stream_queue.pending_info()
            processing = info.get("total", 0) if isinstance(info, dict) else 0

        # 死信统计
        dead_letter = (
            await self._failover.get_dead_letter_stats()
            if self._failover else {"total": 0}
        )

        # 进度统计
        progress = await self._progress.get_global_stats() if self._progress else {}

        return {
            "workers": {
                "active": total_workers - idle_count,
                "idle": idle_count,
                "total": total_workers,
            },
            "queue": {
                "pending": pending,
                "processing": processing,
                "failed": dead_letter.get("total", 0),
            },
            "progress": {
                "completed": progress.get("total_completed", 0),
                "failed": progress.get("total_failed", 0),
                "items": progress.get("total_items", 0),
                "items_per_sec": progress.get("items_per_sec", 0),
                "elapsed": progress.get("elapsed", 0),
            },
            "dead_letter": dead_letter,
        }

    # ---- Worker ----

    async def workers(self) -> List[Dict[str, Any]]:
        """获取所有活跃 Worker 列表"""
        if not self._registry:
            return []
        return await self._registry.get_active_workers()

    async def worker_detail(self, worker_id: str) -> Dict[str, Any]:
        """获取 Worker 详细信息（含统计）"""
        info = {}
        if self._registry:
            info = await self._registry.get_worker_info(worker_id) or {}
        if self._progress:
            stats = await self._progress.get_worker_stats(worker_id)
            if stats:
                info["stats"] = stats
        return info

    # ---- 队列 ----

    async def queue_info(self) -> Dict[str, Any]:
        """获取队列详情"""
        info = {
            "pending": await self._stream_queue.size() if self._stream_queue else 0,
            "processing": 0,
            "failed": 0,
            "consumers": [],
        }

        if self._stream_queue:
            p = await self._stream_queue.pending_info()
            if isinstance(p, dict):
                info["processing"] = p.get("total", 0)

        if self._failover:
            dl = await self._failover.get_dead_letter_stats()
            info["failed"] = dl.get("total", 0)

        return info

    async def pending_tasks(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取未确认的任务列表"""
        tasks = []
        if not self._stream_queue:
            return tasks

        # 使用 XPENDING 获取 pending 消息
        try:
            result = await self._stream_queue._redis.xpending_range(
                self._stream_queue.stream,
                self._stream_queue.group_name,
                min="-", max="+", count=count,
            )
            if result:
                for entry in result:
                    tasks.append({
                        "message_id": entry.get("message_id"),
                        "consumer": entry.get("consumer"),
                        "idle_ms": entry.get("idle", 0),
                        "delivery_count": entry.get("delivery_count", 0),
                        "stream": self._stream_queue.stream,
                    })
        except Exception:
            pass

        return tasks[:count]

    # ---- 诊断 ----

    async def diagnose(self) -> Dict[str, Any]:
        """运行诊断，检测常见问题"""
        issues = []
        status = await self.status()

        # 检查空闲 Worker
        if status["workers"]["idle"] > 0 and status["queue"]["pending"] > 0:
            issues.append(
                f"{status['workers']['idle']} idle workers with {status['queue']['pending']} pending tasks"
            )

        # 检查 Pending 积压
        if status["queue"]["processing"] > 1000:
            issues.append(
                f"High pending count ({status['queue']['processing']}), "
                f"possible worker crashes"
            )

        # 检查死信
        if status["dead_letter"].get("total", 0) > 0:
            issues.append(
                f"{status['dead_letter']['total']} messages in dead letter queue"
            )

        # 检查速率
        if status["progress"]["items_per_sec"] == 0 and status["progress"]["elapsed"] > 60:
            issues.append("No progress in last 60s")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "status": status,
        }

    # ---- 概要打印 ----

    async def print_summary(self):
        """打印集群状态概要"""
        s = await self.status()
        w = s["workers"]
        q = s["queue"]
        p = s["progress"]

        print("\n" + "=" * 55)
        print("  Crawlo Cluster Status")
        print("=" * 55)
        print(f"  Workers:   {w['active']} active / {w['idle']} idle / {w['total']} total")
        print(f"  Queue:     {q['pending']} pending / {q['processing']} processing / {q['failed']} failed")
        print(f"  Progress:  {p['completed']} completed ({p['items_per_sec']}/s) / {p['elapsed']}s elapsed")
        if p.get("failed", 0) > 0:
            print(f"  Failed:    {p['failed']} tasks")
        print("=" * 55 + "\n")


__all__ = ["ClusterMonitor"]
