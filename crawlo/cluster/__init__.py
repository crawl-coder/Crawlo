#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
集群管理模块

提供 Worker 注册、心跳检测、故障转移、进度聚合等分布式协调功能。
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
]
