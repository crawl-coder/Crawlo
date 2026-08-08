#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
集群管理模块

提供 Worker 注册、心跳检测、故障转移、进度聚合等分布式协调功能。

注意：ClusterMixin / ClusterState 从原 crawlo.core.engine_cluster 迁入，
作为 Engine 的分布式 Mixin 和状态容器存在，属于集群协调层面，
因此与其他 cluster 组件一起统一导出。
"""
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.heartbeat import HeartbeatDaemon
from crawlo.cluster.lock import DistributedLock
from crawlo.cluster.failover import FailoverManager
from crawlo.cluster.progress import ProgressAggregator
from crawlo.cluster.rate_limiter import DistributedRateLimiter
from crawlo.cluster.monitor import ClusterMonitor
from crawlo.cluster.config import DynamicConfig
from crawlo.cluster.messaging import ClusterMessenger
from crawlo.cluster.coordinator import (
    ClusterMixin,
    ClusterState,
    _ack_message,
)

__all__ = [
    'WorkerRegistry',
    'HeartbeatDaemon',
    'DistributedLock',
    'FailoverManager',
    'ProgressAggregator',
    'DistributedRateLimiter',
    'ClusterMonitor',
    'DynamicConfig',
    'ClusterMessenger',
    # Engine 集群 Mixin / 状态（从 crawlo.core.engine_cluster 迁入）
    'ClusterMixin',
    'ClusterState',
    '_ack_message',
]
