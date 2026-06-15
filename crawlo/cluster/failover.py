#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
故障转移管理器

监听集群中 Worker 的心跳状态，检测崩溃节点并回收其未完成的任务。

工作流程：
1. 周期性获取故障检测锁（分布式锁，避免多节点同时检测）
2. 清理过期心跳记录（ZREMRANGEBYSCORE）
3. 检测心跳超时的 Worker（初次检测）
4. 标记为 suspect 状态，等待二次确认（30s）
5. 二次确认后 XCLAIM 其 pending 消息，回收任务
6. 注销崩溃 Worker

安全冗余：
- 初次检测仅标记 suspect，不立即回收（防网络抖动）
- 二次确认 30s 后才正式回收
- 去重过滤器 + 幂等下载作为最后防线
"""
import time
import asyncio
from typing import Optional, List, Any

from crawlo.logging import get_logger
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.lock import DistributedLock


class FailoverManager:
    """
    故障转移管理器。

    每个 Worker 运行一个实例，通过分布式锁确保同一时刻只有一个 Worker 执行故障检测。

    使用示例：
        manager = FailoverManager(registry, stream_queue, lock, redis_client)
        async def failover_loop():
            while running:
                await manager.check_and_recover()
                await asyncio.sleep(30)  # 每 30s 检测一次
    """

    def __init__(
        self,
        registry: WorkerRegistry,
        stream_queue,
        lock: DistributedLock,
        redis_client,
        suspect_timeout: int = 30,
        failover_interval: int = 30,
    ):
        """
        初始化故障转移管理器。

        Args:
            registry: WorkerRegistry 实例
            stream_queue: RedisStreamQueue 实例（用于 claim_pending）
            lock: 故障检测专用分布式锁
            redis_client: Redis 异步客户端
            suspect_timeout: suspect 二次确认等待时间（秒）
            failover_interval: 故障检测间隔（秒）
        """
        self._registry = registry
        self._stream_queue = stream_queue
        self._lock = lock
        self._redis = redis_client
        self._suspect_timeout = suspect_timeout
        self._failover_interval = failover_interval

        self.logger = get_logger(self.__class__.__name__)

    # ---- 公开属性 ----

    @property
    def failover_interval(self) -> int:
        """故障检测间隔（秒）"""
        return self._failover_interval

    # ---- 故障检测主方法 ----

    async def check_and_recover(self) -> dict:
        """
        执行一轮故障检测与恢复。

        使用分布式锁确保同一时刻只有一个 Worker 执行。

        Returns:
            恢复统计 {"dead_workers": N, "claimed_tasks": M}
        """
        # 获取故障检测锁
        holder = await self._lock.acquire(timeout=self._failover_interval)
        if not holder:
            return {"dead_workers": 0, "claimed_tasks": 0}

        stats = {"dead_workers": 0, "claimed_tasks": 0, "suspect_marked": 0}

        try:
            # 1. 清理过期心跳记录
            await self._cleanup_expired_heartbeats()

            # 2. 检测心跳超时的 Worker
            dead_worker_ids = await self._registry.detect_dead_workers()

            if not dead_worker_ids:
                return stats

            for worker_id in dead_worker_ids:
                await self._handle_suspected_worker(worker_id, stats)

        except Exception as e:
            self.logger.error(f"Failover check failed: {e}")
        finally:
            await self._lock.release(holder)

        if stats["dead_workers"] > 0 or stats["claimed_tasks"] > 0:
            self.logger.info(
                f"Failover round: dead={stats['dead_workers']}, "
                f"claimed={stats['claimed_tasks']}, suspect={stats['suspect_marked']}"
            )

        return stats

    # ---- 内部方法 ----

    async def _cleanup_expired_heartbeats(self):
        """清理过期的 Worker 心跳记录"""
        try:
            # 心跳超时远长于 worker_timeout，清理更旧的数据
            deadline = time.time() - self._registry.worker_timeout * 2
            await self._redis.zremrangebyscore(
                self._registry.heartbeats_key, 0, deadline
            )
        except Exception:
            pass

    async def _handle_suspected_worker(self, worker_id: str, stats: dict):
        """
        处理疑似崩溃的 Worker。

        初次检测：标记 suspect
        二次确认：正式回收任务 + 注销

        注意：跳过 stopping 状态的 Worker（正在优雅退出，不应回收其任务）。
        """
        worker_info = await self._registry.get_worker_info(worker_id)

        if not worker_info:
            return

        current_status = worker_info.get("status", "")

        # stopping 状态的 Worker 正在 drain 在途任务，不应被回收
        if current_status == WorkerRegistry.STATUS_STOPPING:
            return

        if current_status == WorkerRegistry.STATUS_SUSPECT:
            # 二次确认：检查是否超过 suspect 等待期
            suspect_since = worker_info.get("suspect_since", 0)
            now = time.time()

            if now - suspect_since >= self._suspect_timeout:
                # 正式回收
                claimed = await self._claim_worker_tasks(worker_id)
                await self._registry.deregister(worker_id)

                stats["dead_workers"] += 1
                stats["claimed_tasks"] += claimed

                self.logger.warning(
                    f"Worker {worker_id} confirmed dead: "
                    f"recovered {claimed} pending tasks"
                )
        else:
            # 初次检测：标记 suspect，不立即回收
            await self._registry.update_status(
                worker_id,
                WorkerRegistry.STATUS_SUSPECT,
                suspect_since=time.time(),
            )
            stats["suspect_marked"] += 1
            self.logger.info(
                f"Worker {worker_id} marked suspect (first detection, "
                f"will confirm in {self._suspect_timeout}s)"
            )

    async def _claim_worker_tasks(self, dead_worker_id: str) -> int:
        """
        回收崩溃 Worker 的未完成任务。

        使用 XAUTOCLAIM（Redis 6.2+）或 XPENDING+XCLAIM（Redis 5.0-6.1）。
        回收策略：XCLAIM 后 XACK+XDEL 原消息，再 XADD 重新入队（增加 retry_count）。
        重新入队的消息可被任何活跃 Worker 通过 XREADGROUP 消费。

        Returns:
            回收的任务数量
        """
        if not hasattr(self._stream_queue, 'claim_pending'):
            self.logger.warning("Stream queue does not support claim_pending, cannot recover tasks")
            return 0

        total_claimed = 0
        group = self._stream_queue.group_name
        max_len = self._stream_queue.max_length

        try:
            # 回收两个 Stream 的 pending 消息：高优 + 普通
            for stream_key in (self._stream_queue.high_stream, self._stream_queue.stream):
                while True:
                    claimed_messages = await self._stream_queue.claim_pending(
                        min_idle_ms=self._stream_queue.consumer_idle_timeout,
                        count=100,
                        stream=stream_key,
                    )
                    if not claimed_messages:
                        break

                    for msg_id, request, retry_count in claimed_messages:
                        try:
                            if retry_count >= self._stream_queue.delivery_count_limit:
                                await self._stream_queue._escalate_to_dead_letter(
                                    msg_id, f"Worker {dead_worker_id} crashed, max retries exceeded"
                                )
                                self.logger.debug(f"Message {msg_id} escalated to dead letter (retries={retry_count})")
                            else:
                                msgs = await self._redis.xrange(stream_key, min=msg_id, max=msg_id, count=1)
                                if not msgs:
                                    await self._redis.xack(stream_key, group, msg_id)
                                    continue

                                _, fields = msgs[0]

                                await self._redis.xack(stream_key, group, msg_id)
                                await self._redis.xdel(stream_key, msg_id)

                                new_fields = {k: v for k, v in fields.items() if k != b"retry_count"}
                                new_fields[b"retry_count"] = str(retry_count + 1).encode()
                                new_fields[b"reenqueued_at"] = str(time.time()).encode()
                                new_fields[b"failover_from"] = dead_worker_id.encode()
                                await self._redis.xadd(stream_key, new_fields, maxlen=max_len, approximate=True)
                                total_claimed += 1
                        except Exception as e:
                            self.logger.warning(f"Failed to re-enqueue claimed message {msg_id}: {e}")
                            total_claimed += 1

        except Exception as e:
            self.logger.error(f"Claim worker tasks failed for {dead_worker_id}: {e}")

        if total_claimed > 0:
            self.logger.info(
                f"Failover: recovered {total_claimed} tasks from dead worker {dead_worker_id}, "
                f"re-enqueued for processing"
            )

        return total_claimed

    # ---- 死信管理 ----

    async def get_dead_letter_stats(self) -> dict:
        """查询死信队列状态"""
        stats = {"total": 0}
        try:
            info = await self._redis.xinfo_stream(self._stream_queue.failed_stream)
            stats["total"] = info.get("length", 0)
        except Exception:
            pass
        return stats

    async def retry_dead_letters(self, count: int = 10) -> int:
        """
        重新处理死信队列中的消息。

        读取死信 Stream → 重新 XADD 到低优先级队列 → XACK 死信。

        Returns:
            重试的消息数量
        """
        retried = 0
        try:
            msgs = await self._redis.xrange(
                self._stream_queue.failed_stream, count=count
            )
            for msg_id, fields in msgs:
                # 复制字段，重置 retry_count
                new_fields = {k: v for k, v in fields.items() if k != b"retry_count"}
                new_fields[b"retry_count"] = b"0"
                new_fields[b"reenqueued_at"] = str(time.time()).encode()

                await self._redis.xadd(
                    self._stream_queue.stream,
                    new_fields,
                    maxlen=self._stream_queue.max_length,
                    approximate=True,
                )
                await self._redis.xdel(self._stream_queue.failed_stream, msg_id)
                retried += 1
        except Exception as e:
            self.logger.error(f"Retry dead letters failed: {e}")

        if retried > 0:
            self.logger.info(f"Retried {retried} messages from dead letter queue")

        return retried


__all__ = [
    "FailoverManager",
]
