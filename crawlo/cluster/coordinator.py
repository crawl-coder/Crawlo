#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 集群功能 Mixin

将 Engine 中所有分布式/集群相关方法提取到此 Mixin，
保持与 RequestGenerationMixin 一致的设计模式。

包含：
- _init_cluster: 初始化 9 个集群组件
- _start_cluster_tasks: 启动集群后台任务
- _shutdown_cluster / _drain_inflight_tasks: 优雅关闭
- _failover_loop / _leader_shutdown_loop: 后台循环
- _on_control_message / _on_config_message: Pub/Sub 处理
- _try_acquire_leader_lock / _release_leader_lock: Leader 选举
- _check_leader_shutdown_conditions: 退出条件检查
"""
from dataclasses import dataclass
from typing import Any, Optional


async def _ack_message(request, engine, success: bool, error: Exception = None):
    """
    Distributed ACK helper.

    Sends XACK on success, NACK on failure (with error classification).
    Called from crawl_task() to confirm task completion in distributed mode.
    """
    if not engine._cluster_state.worker_id:
        return
    meta = getattr(request, 'meta', None) if request else None
    if not meta:
        return
    message_id = meta.get('__stream_message_id')
    # 注意：必须用 `is None` 而非 `not`，因为 Scheduler 实现了 __len__
    # 当队列为空时 __len__ 返回 0，`not scheduler` 为 True（误判为无 scheduler）
    if not message_id or engine.scheduler is None:
        return

    try:
        if success:
            await engine.scheduler.ack_request(message_id)
        else:
            from crawlo.queue.task_tracker import TaskResult
            result = TaskResult.RETRY
            if engine._cluster_state.task_tracker and error:
                result = engine._cluster_state.task_tracker.classify_error(error)
            await engine.scheduler.nack_request(message_id, result=result)
    except Exception as ack_err:
        # 修复：原实现 except Exception: pass 静默吞错
        # ACK 失败会导致任务被重复投递或卡在 PEL，NACK 失败会导致死任务不进死信
        # 改为记录警告日志 + 统计计数，便于运维定位问题
        engine.logger.warning(
            f"ACK/NACK failed for message {message_id} "
            f"(success={success}, error={ack_err!r})"
        )
        if hasattr(engine.crawler, 'stats') and engine.crawler.stats is not None:
            try:
                engine.crawler.stats.inc_value('scheduler/ack_failure_count')
            except Exception:
                pass


@dataclass
class ClusterState:
    """Engine 集群组件状态容器。

    将 Engine 的 18 个 _cluster_*/_leader_*/_task_tracker 字段收入此 dataclass，
    减少 Engine.__init__ 顶层赋值数。
    """
    registry: Optional[Any] = None              # WorkerRegistry
    heartbeat: Optional[Any] = None             # HeartbeatDaemon
    failover: Optional[Any] = None              # FailoverManager
    lock: Optional[Any] = None                  # DistributedLock (for failover)
    progress: Optional[Any] = None              # ProgressAggregator
    monitor: Optional[Any] = None               # ClusterMonitor
    rate_limiter: Optional[Any] = None          # DistributedRateLimiter
    messenger: Optional[Any] = None             # ClusterMessenger
    dynamic_config: Optional[Any] = None        # DynamicConfig
    worker_id: Optional[str] = None             # Worker ID
    heartbeat_task: Optional[Any] = None        # asyncio.Task
    failover_task: Optional[Any] = None         # asyncio.Task
    paused: bool = False                        # pause flag from control channel
    redis: Optional[Any] = None                 # Redis client
    leader_lock: Optional[Any] = None           # DistributedLock for leader election
    leader_shutdown_task: Optional[Any] = None  # asyncio.Task
    task_tracker: Optional[Any] = None          # TaskTracker
    coordinated_shutdown_enabled: bool = True


from crawlo.cluster.coordinator_seed import ClusterSeedMixin
from crawlo.cluster.coordinator_lifecycle import ClusterLifecycleMixin
from crawlo.cluster.coordinator_leader import ClusterLeaderMixin
from crawlo.cluster.coordinator_messaging import ClusterMessagingMixin


class ClusterMixin(ClusterSeedMixin, ClusterLifecycleMixin, ClusterLeaderMixin, ClusterMessagingMixin):
    """Engine 集群功能 Mixin（P2-6 按关注点拆分：seed / lifecycle / leader / messaging）。"""
