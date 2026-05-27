#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Worker 注册中心

管理集群中所有 Worker 节点的注册、心跳、注销和状态查询。
基于 Redis HASH（注册表）+ ZSET（心跳）实现。

Key 设计：
    crawlo:{project}:{spider}:registry:workers     HASH   Worker 注册表
    crawlo:{project}:{spider}:registry:heartbeats  ZSET   心跳时间戳（score=timestamp）
"""
import json
import time
from typing import Optional, Dict, List, Any

from crawlo.logging import get_logger
from crawlo.utils.redis.keys import RedisKeyManager


class WorkerRegistry:
    """
    Worker 注册中心。

    使用示例：
        registry = WorkerRegistry(redis_client, key_manager)
        worker_id = await registry.register({
            'host': '192.168.1.10',
            'pid': 12345,
            'concurrency': 16,
        })
        await registry.heartbeat(worker_id)
        await registry.deregister(worker_id)
    """

    # Worker 状态常量
    STATUS_RUNNING = "running"
    STATUS_IDLE = "idle"
    STATUS_STOPPING = "stopping"
    STATUS_SUSPECT = "suspect"  # 疑似崩溃，等待二次确认

    def __init__(
        self,
        redis_client,
        key_manager: RedisKeyManager,
        worker_timeout: int = 90,
        auto_deregister: bool = True,
    ):
        """
        初始化 Worker 注册中心。

        Args:
            redis_client: Redis 异步客户端
            key_manager: Redis Key 管理器
            worker_timeout: Worker 心跳超时（秒），超过则判定为崩溃
            auto_deregister: 是否在检测到崩溃后自动注销
        """
        self._redis = redis_client
        self._key_manager = key_manager
        self._worker_timeout = worker_timeout
        self._auto_deregister = auto_deregister
        self.logger = get_logger(self.__class__.__name__)

        # Key
        ns = key_manager.namespace
        self._workers_key = f"crawlo:{ns}:registry:workers"
        self._heartbeats_key = f"crawlo:{ns}:registry:heartbeats"

    # ---- 注册 / 注销 ----

    async def register(self, worker_info: Dict[str, Any]) -> str:
        """
        注册 Worker，返回 worker_id。

        自动生成唯一 worker_id，写入注册表，记录初始心跳。

        Args:
            worker_info: Worker 信息字典，需包含 host/pid/concurrency 等

        Returns:
            worker_id: 分配的 Worker 唯一标识
        """
        import socket
        import os
        import uuid

        # 生成 worker_id（如果调用方未提供）
        worker_id = worker_info.get("id") or self._generate_worker_id()

        # 补全字段
        info = {
            "id": worker_id,
            "host": worker_info.get("host", socket.gethostname()),
            "pid": worker_info.get("pid", os.getpid()),
            "concurrency": worker_info.get("concurrency", 0),
            "started_at": worker_info.get("started_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
            "status": self.STATUS_RUNNING,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_processing": 0,
            "last_heartbeat": time.time(),
        }

        # HSET 注册表
        await self._redis.hset(
            self._workers_key,
            f"worker:{worker_id}",
            json.dumps(info, ensure_ascii=False),
        )

        # ZADD 心跳
        await self._redis.zadd(
            self._heartbeats_key,
            {f"worker:{worker_id}": time.time()},
        )

        self.logger.info(
            f"Worker registered: {worker_id} (host={info['host']}, pid={info['pid']})"
        )
        return worker_id

    async def deregister(self, worker_id: str):
        """
        正常注销 Worker。
        从注册表和心跳中移除。
        """
        field = f"worker:{worker_id}"

        await self._redis.hdel(self._workers_key, field)
        await self._redis.zrem(self._heartbeats_key, field)

        self.logger.info(f"Worker deregistered: {worker_id}")

    # ---- 心跳 ----

    async def heartbeat(self, worker_id: str, extra: Optional[Dict[str, Any]] = None):
        """
        发送心跳，更新最后活跃时间和可选状态字段。

        Args:
            worker_id: Worker ID
            extra: 额外更新的字段（如 tasks_completed, tasks_processing 等）
        """
        field = f"worker:{worker_id}"
        now = time.time()

        # 更新心跳 ZSET
        await self._redis.zadd(self._heartbeats_key, {field: now})

        # 更新注册表中的心跳时间戳
        worker_info = await self._get_worker_info_raw(field)
        if worker_info:
            worker_info["last_heartbeat"] = now
            if extra:
                worker_info.update(extra)
            await self._redis.hset(
                self._workers_key,
                field,
                json.dumps(worker_info, ensure_ascii=False),
            )

    async def update_status(self, worker_id: str, status: str, **extra):
        """
        更新 Worker 状态（running/idle/suspect/stopping）。

        Args:
            worker_id: Worker ID
            status: 新状态
            **extra: 额外字段（如 suspect_since）
        """
        field = f"worker:{worker_id}"
        worker_info = await self._get_worker_info_raw(field)
        if worker_info:
            worker_info["status"] = status
            worker_info.update(extra)
            await self._redis.hset(
                self._workers_key,
                field,
                json.dumps(worker_info, ensure_ascii=False),
            )
        # 同步更新心跳
        await self._redis.zadd(self._heartbeats_key, {field: time.time()})

    # ---- 查询 ----

    async def get_active_workers(self) -> List[Dict[str, Any]]:
        """
        获取活跃 Worker 列表（心跳未超时）。

        Returns:
            活跃 Worker 信息列表
        """
        now = time.time()
        deadline = now - self._worker_timeout

        # 清理过期心跳
        await self._redis.zremrangebyscore(
            self._heartbeats_key, 0, deadline
        )

        # 获取存活的心跳记录
        alive = await self._redis.zrangebyscore(
            self._heartbeats_key, deadline, "+inf"
        )

        if not alive:
            return []

        # 批量获取 Worker 信息
        workers = []
        for field in alive:
            field_str = field.decode("utf-8") if isinstance(field, bytes) else field
            info = await self._get_worker_info_raw(field_str)
            if info:
                workers.append(info)

        return workers

    async def get_worker_info(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 Worker 的详细信息。

        Args:
            worker_id: Worker ID

        Returns:
            Worker 信息字典，不存在时返回 None
        """
        field = f"worker:{worker_id}"
        return await self._get_worker_info_raw(field)

    async def get_worker_count(self) -> int:
        """获取当前注册的 Worker 总数（含超时未清理的）"""
        return await self._redis.hlen(self._workers_key)

    async def detect_dead_workers(self, timeout: Optional[int] = None) -> List[str]:
        """
        检测崩溃 Worker（心跳超时）。

        返回 worker_id 列表（不含 "worker:" 前缀）。
        注意：此方法不做清理，只做检测。清理由 check_and_recover() 完成。

        Args:
            timeout: 超时阈值（秒），None 则使用初始化时设置的 worker_timeout

        Returns:
            崩溃的 worker_id 列表
        """
        ttl = timeout or self._worker_timeout
        now = time.time()
        deadline = now - ttl

        # 获取超时的心跳记录
        dead = await self._redis.zrangebyscore(
            self._heartbeats_key, 0, deadline
        )

        dead_ids = []
        for entry in dead:
            entry_str = entry.decode("utf-8") if isinstance(entry, bytes) else str(entry)
            # 去掉 "worker:" 前缀
            worker_id = entry_str.replace("worker:", "", 1) if entry_str.startswith("worker:") else entry_str
            dead_ids.append(worker_id)

        return dead_ids

    # ---- 内部方法 ----

    def _generate_worker_id(self) -> str:
        """生成唯一的 Worker ID"""
        import socket
        import os
        import uuid
        host = socket.gethostname()
        pid = os.getpid()
        uid = uuid.uuid4().hex[:8]
        return f"{host}-{pid}-{uid}"

    async def _get_worker_info_raw(self, field: str) -> Optional[Dict[str, Any]]:
        """从 Redis HASH 读取 Worker 信息（原始字段名）"""
        raw = await self._redis.hget(self._workers_key, field)
        if raw:
            raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            return json.loads(raw_str)
        return None


__all__ = [
    "WorkerRegistry",
]
