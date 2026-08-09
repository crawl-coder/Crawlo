#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""ClusterMixin 生命周期子 Mixin（P2-6 从 coordinator.py 拆分）"""
from __future__ import annotations

import asyncio
from crawlo.utils.misc import safe_get_config


try:
    from crawlo.cluster import WorkerRegistry, HeartbeatDaemon, DistributedLock, FailoverManager
    from crawlo.cluster import ProgressAggregator, DistributedRateLimiter, ClusterMonitor
    from crawlo.cluster import DynamicConfig, ClusterMessenger
    from crawlo.queue.task_tracker import TaskTracker
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False
    WorkerRegistry = HeartbeatDaemon = DistributedLock = FailoverManager = None
    ProgressAggregator = DistributedRateLimiter = ClusterMonitor = None
    DynamicConfig = ClusterMessenger = None
    TaskTracker = None


class ClusterLifecycleMixin:
    """集群组件初始化、后台任务启停与优雅关闭。"""

    async def _init_cluster(self):
        """
        初始化集群组件（distributed 模式）。

        - WorkerRegistry: 注册到 Redis
        - HeartbeatDaemon: 周期性心跳
        - FailoverManager: 故障检测与任务回收
        - DistributedLock: 故障检测互斥锁
        - TaskTracker: 任务生命周期追踪
        """
        run_mode = safe_get_config(self.settings, 'RUN_MODE', 'standalone')
        queue_type = safe_get_config(self.settings, 'QUEUE_TYPE', 'memory')

        # distributed 模式下，_determine_queue_type 会将 QUEUE_TYPE=redis 升级为 redis_stream
        # 此处需同步判断：只要 run_mode=distributed 且配置的 queue_type 属于 Redis 系列，就应初始化集群组件
        # （_determine_queue_type 已保证 distributed 模式最终一定使用 redis_stream）
        if run_mode != 'distributed':
            return
        if queue_type not in ('redis_stream', 'redis'):
            return
        if not CLUSTER_AVAILABLE:
            self.logger.warning("Cluster module not available, distributed features disabled")
            return

        try:
            redis_client = None
            from crawlo.queue.backends.redis_stream import RedisStreamQueue

            # 优先尝试复用 scheduler.queue_manager 中的队列
            if self.scheduler and self.scheduler.queue_manager:
                q = getattr(self.scheduler.queue_manager, '_queue', None)
                if isinstance(q, RedisStreamQueue):
                    queue = q
                    redis_client = queue._redis
                else:
                    self.logger.debug(
                        f"scheduler.queue_manager._queue is {type(q).__name__} (not RedisStreamQueue), "
                        f"creating a fresh stream queue for cluster components"
                    )

            if not redis_client:
                redis_url = safe_get_config(self.settings, 'REDIS_URL', None)
                if not redis_url:
                    self.logger.error("REDIS_URL not configured, cluster init failed")
                    return

                project = safe_get_config(self.settings, 'PROJECT_NAME', 'crawlo')
                spider_name = safe_get_config(self.settings, 'SPIDER_NAME', 'default')
                queue = RedisStreamQueue(
                    redis_url=redis_url,
                    project_name=project,
                    spider_name=spider_name,
                    serialization_format=safe_get_config(
                        self.settings, 'STREAM_SERIALIZATION_FORMAT', 'json'
                    ),
                    stream_compact=safe_get_config(
                        self.settings, 'STREAM_COMPACT', True, bool
                    ),
                    priority_enabled=safe_get_config(
                        self.settings, 'STREAM_PRIORITY_ENABLED', True, bool
                    ),
                    sentinel_urls=safe_get_config(
                        self.settings, 'REDIS_SENTINEL_URLS', []
                    ),
                    sentinel_service=safe_get_config(
                        self.settings, 'REDIS_SENTINEL_SERVICE', 'mymaster'
                    ),
                    cluster_enabled=safe_get_config(
                        self.settings, 'REDIS_CLUSTER_ENABLED', False, bool
                    ),
                    cluster_nodes=safe_get_config(
                        self.settings, 'REDIS_CLUSTER_NODES', []
                    ),
                )
                await queue.connect()
                redis_client = queue._redis
                self.logger.info("Created dedicated RedisStreamQueue for cluster init")

            # connect() 已在上面调用过（scheduler 复用 or 新建），无需重复

            from crawlo.utils.redis.keys import RedisKeyManager
            project = safe_get_config(self.settings, 'PROJECT_NAME', 'crawlo')
            spider_name = safe_get_config(self.settings, 'SPIDER_NAME', 'default')
            key_manager = RedisKeyManager(project, spider_name)

            self._cluster_state.redis = redis_client
            leader_lock_ttl = safe_get_config(
                self.settings, 'CLUSTER_HEARTBEAT_INTERVAL', 15, int
            ) * 2
            self._cluster_state.leader_lock = DistributedLock(
                redis_client,
                f"{project}:{spider_name}:lock:leader",
                default_timeout=leader_lock_ttl,
                retry_count=1,
                retry_delay=0.5,
            )

            worker_timeout = safe_get_config(self.settings, 'CLUSTER_WORKER_TIMEOUT', 90)
            heartbeat_interval = safe_get_config(self.settings, 'CLUSTER_HEARTBEAT_INTERVAL', 15)
            failover_interval = safe_get_config(self.settings, 'CLUSTER_FAILOVER_CHECK_INTERVAL', 30)

            # 1. WorkerRegistry
            self._cluster_state.registry = WorkerRegistry(
                redis_client, key_manager,
                worker_timeout=worker_timeout,
            )
            worker_info = {
                'host': safe_get_config(self.settings, 'HOST', 'localhost'),
                'pid': __import__('os').getpid(),
                'concurrency': self.task_manager._concurrency_limit if self.task_manager else 0,
            }
            self._cluster_state.worker_id = await self._cluster_state.registry.register(worker_info)

            # 2. HeartbeatDaemon
            self._cluster_state.heartbeat = HeartbeatDaemon(
                self._cluster_state.registry,
                self._cluster_state.worker_id,
                interval=heartbeat_interval,
            )
            self._cluster_state.task_tracker = TaskTracker(self._cluster_state.worker_id)
            self._cluster_state.heartbeat.set_stats_provider(self._cluster_state.task_tracker)

            # 3. DistributedLock (failover)
            lock_timeout = safe_get_config(self.settings, 'CLUSTER_FAILOVER_LOCK_TIMEOUT', 30)
            lock_retry = safe_get_config(self.settings, 'DISTRIBUTED_LOCK_RETRY_COUNT', 3)
            lock_retry_delay = safe_get_config(self.settings, 'DISTRIBUTED_LOCK_RETRY_DELAY', 0.5)
            self._cluster_state.lock = DistributedLock(
                redis_client,
                f"{project}:{spider_name}:lock:failover",
                default_timeout=lock_timeout,
                retry_count=lock_retry,
                retry_delay=lock_retry_delay,
            )

            # 4. FailoverManager
            self._cluster_state.failover = FailoverManager(
                self._cluster_state.registry,
                queue,
                self._cluster_state.lock,
                redis_client,
                suspect_timeout=30,
                failover_interval=failover_interval,
            )

            # 5. ProgressAggregator
            report_interval = safe_get_config(self.settings, 'PROGRESS_REPORT_INTERVAL', 10)
            self._cluster_state.progress = ProgressAggregator(
                redis_client, key_manager,
                report_interval=report_interval,
            )

            # 6. DistributedRateLimiter
            rate_limit_enabled = safe_get_config(self.settings, 'DISTRIBUTED_RATE_LIMIT_ENABLED', False)
            rate_limit_rate = safe_get_config(self.settings, 'DISTRIBUTED_RATE_LIMIT_DEFAULT_RATE', 0)
            rate_limit_capacity = safe_get_config(self.settings, 'DISTRIBUTED_RATE_LIMIT_CAPACITY', 10)
            self._cluster_state.rate_limiter = DistributedRateLimiter(
                redis_client, f"crawlo:{project}:{spider_name}",
                enabled=rate_limit_enabled,
                default_rate=rate_limit_rate,
                default_capacity=rate_limit_capacity,
            )

            # 7. ClusterMonitor
            self._cluster_state.monitor = ClusterMonitor(
                self._cluster_state.registry,
                self._cluster_state.progress,
                stream_queue=queue,
                failover_manager=self._cluster_state.failover,
            )

            # 8. ClusterMessenger
            self._cluster_state.messenger = ClusterMessenger(
                redis_client, f"crawlo:{project}:{spider_name}"
            )

            # 9. DynamicConfig
            dynamic_config_enabled = safe_get_config(self.settings, 'DYNAMIC_CONFIG_ENABLED', False)
            self._cluster_state.dynamic_config = DynamicConfig(
                redis_client,
                messenger=self._cluster_state.messenger,
                namespace=f"crawlo:{project}:{spider_name}",
                rate_limiter=self._cluster_state.rate_limiter,
                enabled=dynamic_config_enabled,
            )

            self.logger.info(
                f"Cluster initialized: worker={self._cluster_state.worker_id}, "
                f"heartbeat={heartbeat_interval}s, failover={failover_interval}s, "
                f"rate_limit={'on' if rate_limit_enabled else 'off'}, "
                f"dynamic_config={'on' if dynamic_config_enabled else 'off'}"
            )

        except Exception as e:
            self.logger.error(f"Cluster initialization failed: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            # 清理已初始化的部分资源
            if self._cluster_state.redis:
                try:
                    await self._cluster_state.redis.close()
                except Exception:
                    pass
                self._cluster_state.redis = None

    # ========================================================================
    # 后台任务
    # ========================================================================

    async def _start_cluster_tasks(self):
        """启动集群后台任务（心跳 + 故障检测 + 消息监听）"""
        if not self._cluster_state.worker_id:
            return

        if self._cluster_state.heartbeat:
            self._cluster_state.heartbeat_task = await self._cluster_state.heartbeat.start()

        if self._cluster_state.messenger:
            await self._cluster_state.messenger.start()
            await self._cluster_state.messenger.subscribe("control", self._on_control_message)
            await self._cluster_state.messenger.subscribe("config", self._on_config_message)

        if self._cluster_state.failover:
            self._cluster_state.failover_task = asyncio.create_task(self._failover_loop())

        if self._cluster_state.coordinated_shutdown_enabled and self._cluster_state.dynamic_config:
            self._cluster_state.leader_shutdown_task = asyncio.create_task(self._leader_shutdown_loop())

        self.logger.debug("Cluster background tasks started")

    # ========================================================================
    # Pub/Sub 消息处理
    # ========================================================================

    async def _shutdown_cluster(self):
        """
        优雅关闭集群组件。

        1. 标记 Worker 为 stopping（防止 failover 误回收）
        2. 停止 Pub/Sub 消息监听
        3. 停止心跳
        4. 停止故障检测
        5. 等待在途任务 drain（超时保护）
        6. 注销 Worker
        """
        if not self._cluster_state.worker_id:
            return

        try:
            if self._cluster_state.registry:
                await self._cluster_state.registry.update_status(
                    self._cluster_state.worker_id,
                    self._cluster_state.registry.STATUS_STOPPING,
                )
                self.logger.debug(f"Worker {self._cluster_state.worker_id} marked as stopping")

            if self._cluster_state.messenger:
                await self._cluster_state.messenger.stop()

            if self._cluster_state.heartbeat:
                await self._cluster_state.heartbeat.stop()
            cancelled_tasks = []
            if self._cluster_state.heartbeat_task and not self._cluster_state.heartbeat_task.done():
                self._cluster_state.heartbeat_task.cancel()
                cancelled_tasks.append(self._cluster_state.heartbeat_task)

            if self._cluster_state.failover_task and not self._cluster_state.failover_task.done():
                self._cluster_state.failover_task.cancel()
                cancelled_tasks.append(self._cluster_state.failover_task)

            if self._cluster_state.leader_shutdown_task and not self._cluster_state.leader_shutdown_task.done():
                self._cluster_state.leader_shutdown_task.cancel()
                cancelled_tasks.append(self._cluster_state.leader_shutdown_task)

            if cancelled_tasks:
                await asyncio.gather(*cancelled_tasks, return_exceptions=True)
            await self._release_leader_lock()

            await self._drain_inflight_tasks()

            if self._cluster_state.registry:
                await self._cluster_state.registry.deregister(self._cluster_state.worker_id)

            self.logger.info(f"Cluster shutdown complete: {self._cluster_state.worker_id}")

        except Exception as e:
            self.logger.debug(f"Cluster shutdown error: {e}")

    async def _drain_inflight_tasks(self):
        """
        等待在途任务完成后再注销 Worker。

        超时后取消残留任务（由 failover 机制回收）。
        """
        drain_timeout = safe_get_config(
            self.settings, 'CLUSTER_GRACEFUL_SHUTDOWN_TIMEOUT', 30, int
        )

        inflight = [t for t in self._background_tasks if not t.done()]
        if not inflight:
            return

        self.logger.info(
            f"Draining {len(inflight)} inflight tasks (timeout={drain_timeout}s)..."
        )

        try:
            done, pending = await asyncio.wait(inflight, timeout=drain_timeout)
            if pending:
                self.logger.warning(
                    f"Drain timeout: {len(pending)}/{len(inflight)} tasks still pending, "
                    f"forcing shutdown (tasks will be recovered by failover)"
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
            else:
                self.logger.info(
                    f"All {len(done)} inflight tasks drained successfully"
                )
        except Exception as e:
            self.logger.warning(f"Drain error: {e}")
