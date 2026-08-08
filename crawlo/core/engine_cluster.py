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
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from crawlo.logging import get_logger
from crawlo.utils.misc import safe_get_config
from crawlo.queue.task_tracker import TaskTracker

# Cluster module (distributed only)
try:
    from crawlo.cluster import WorkerRegistry, HeartbeatDaemon, DistributedLock, FailoverManager
    from crawlo.cluster import ProgressAggregator, DistributedRateLimiter, ClusterMonitor
    from crawlo.cluster import DynamicConfig, ClusterMessenger
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False
    WorkerRegistry = HeartbeatDaemon = DistributedLock = FailoverManager = None
    ProgressAggregator = DistributedRateLimiter = ClusterMonitor = None
    DynamicConfig = ClusterMessenger = None


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
    """Engine 集群组件状态容器（Phase 3 Step 2）。

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


class ClusterMixin:
    """
    Engine 集群功能 Mixin。

    提供分布式模式下的所有集群协调逻辑：
    组件初始化、后台任务启停、故障检测、Leader 选举、协调退出、种子锁。
    """

    # ========================================================================
    # 种子锁（Phase 3 从 Engine 迁入，本就属于分布式协调）
    # ========================================================================

    # 种子锁原子获取的 Lua 脚本
    # KEYS[1] = seed_lock_key
    # ARGV[1] = worker_id
    # ARGV[2] = ttl (120)
    # ARGV[3..] = 已知的活跃 worker_id 列表（registry 中存活的）
    # 逻辑：
    #   1. 若 key 不存在 -> SETNX 成功，返回 1
    #   2. 若 key 存在且 owner == worker_id -> 续期，返回 1
    #   3. 若 key 存在且 owner 在活跃列表中 -> 锁有效，返回 0
    #   4. 若 key 存在但 owner 不在活跃列表中：
    #        4a. active_count == 0 -> 注册信息还没写好，禁止清死锁，返回 0（等下一轮）
    #        4b. active_count >= 1 -> 判定为死锁，DEL 后重新 SETNX，返回 2
    _SEED_LOCK_LUA = """
local key = KEYS[1]
local worker_id = ARGV[1]
local ttl = tonumber(ARGV[2])
local active_count = tonumber(ARGV[3])
local current = redis.call('GET', key)
if current == false then
    redis.call('SET', key, worker_id, 'EX', ttl)
    return 1
end
if current == worker_id then
    redis.call('EXPIRE', key, ttl)
    return 1
end
for i = 1, active_count do
    if ARGV[3 + i] == current then
        return 0
    end
end
-- 活跃列表为空：说明 registry 尚未完成写入 / 心跳未同步，禁止清死锁
if active_count == 0 then
    return 0
end
-- owner 不在非空的活跃列表中，安全地判定为死锁，清理并抢占
redis.call('DEL', key)
redis.call('SET', key, worker_id, 'EX', ttl)
return 2
"""

    async def _renew_seed_lock(self):
        """种子锁续期任务：每 60 秒延长锁 TTL，防止长时种子生成期间锁过期"""
        try:
            while self.running and self._seed_lock_key:
                await asyncio.sleep(60)
                if self._cluster_state.redis and self._seed_lock_key:
                    await self._cluster_state.redis.expire(self._seed_lock_key, 120)
        except asyncio.CancelledError:
            pass

    async def _try_acquire_seed_lock_atomic(
        self, seed_lock_key: str, project: str, spider_name: str
    ) -> bool:
        """
        原子地获取种子锁（含死锁清理 + 启动期协调）。

        修复分布式种子锁的关键竞态：
        - 抢锁前确认自己已写入 registry（避免 registry 读取空列表导致误判死锁）
        - 抢锁前短 sleep，让其他 worker 完成注册写入
        - Lua 已保证 active_count=0 时不清死锁；此处对 "暂无法判定" 的结果做重试
        """
        my_id = self._cluster_state.worker_id
        registry = self._cluster_state.registry
        redis = self._cluster_state.redis
        if redis is None:
            return False

        # 1. 等待自身注册可见（保证 list_workers 至少能看到自己，避免 active=[]）
        if registry is not None:
            for _ in range(20):  # 最多 2.0s
                try:
                    workers = await registry.list_workers() or []
                except Exception:
                    workers = []
                ids = [
                    w.get('worker_id') if isinstance(w, dict) else str(w)
                    for w in workers
                ]
                if my_id in ids:
                    break
                await asyncio.sleep(0.1)
            # 额外等待 0.3s，给其他刚启动的 worker 一个写入窗口（run_10_workers 间隔 1s）
            await asyncio.sleep(0.3)

        # 2. 带重试的抢锁：最多 5 次，每次间隔递增，覆盖活跃列表还没同步的情况
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                active_workers = []
                if registry is not None:
                    try:
                        workers = await registry.list_workers()
                        active_workers = [
                            w.get('worker_id') if isinstance(w, dict) else str(w)
                            for w in (workers or [])
                        ]
                        active_workers = [w for w in active_workers if w]
                    except Exception as e:
                        self.logger.debug(
                            f"Failed to list active workers for seed lock: {e}"
                        )

                args = [my_id, 120, len(active_workers)] + active_workers
                result = await redis.eval(self._SEED_LOCK_LUA, 1, seed_lock_key, *args)
                result_int = int(result) if result is not None else 0

                if result_int == 1:
                    self.logger.debug(
                        f"Acquired seed lock (fresh, attempt={attempt}): {seed_lock_key}"
                    )
                    return True
                if result_int == 2:
                    self.logger.info(
                        f"Cleared stale seed lock and acquired (attempt={attempt}): {seed_lock_key}"
                    )
                    return True
                # result_int == 0
                # 要么锁被活跃 worker 持有（正常情况，seed 由另一个 worker 生成）
                # 要么 active_count=0 时 Lua 拒绝清死锁（注册信息还没完整同步）
                # 做区分：如果锁 holder 就在活跃列表里 -> 直接放弃；否则重试
                if registry is not None and active_workers:
                    try:
                        holder = await redis.get(seed_lock_key)
                        if holder and holder in active_workers and holder != my_id:
                            self.logger.debug(
                                f"Seed lock held by active worker {holder}, skipping"
                            )
                            return False
                    except Exception:
                        pass
                if attempt < max_attempts:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                return False
            except Exception as e:
                self.logger.warning(
                    f"Atomic seed lock acquisition (attempt={attempt}/{max_attempts}) "
                    f"failed: {e}"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                # 最后一轮失败时使用 SETNX 保底
                try:
                    acquired = await redis.set(
                        seed_lock_key, my_id, nx=True, ex=120
                    )
                    return bool(acquired)
                except Exception as fallback_err:
                    self.logger.error(
                        f"Seed lock fallback SETNX failed: {fallback_err}"
                    )
                    return False
        return False

    # ========================================================================
    # 组件初始化
    # ========================================================================

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

        if run_mode != 'distributed' or queue_type != 'redis_stream':
            return
        if not CLUSTER_AVAILABLE:
            self.logger.warning("Cluster module not available, distributed features disabled")
            return

        try:
            redis_client = None
            from crawlo.queue.redis_stream_queue import RedisStreamQueue

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

    async def _on_control_message(self, message: dict):
        """处理控制消息（暂停/恢复/停止）"""
        action = message.get("action", "")
        if action == "pause":
            self._cluster_state.paused = True
            self.logger.info("Cluster control: PAUSED")
        elif action == "resume":
            self._cluster_state.paused = False
            self.logger.info("Cluster control: RESUMED")
        elif action == "shutdown":
            self.logger.warning("Cluster control: SHUTDOWN received")
            self.running = False

    async def _on_config_message(self, message: dict):
        """处理配置变更消息"""
        action = message.get("action", "")
        if action == "rate_limit" and self._cluster_state.rate_limiter:
            domain = message.get("domain", "")
            rate = message.get("rate", 0)
            await self._cluster_state.rate_limiter.set_rate(domain, rate)
        elif action == "seed_urls" and self._cluster_state.dynamic_config:
            urls = await self._cluster_state.dynamic_config.pop_seed_urls(count=100)
            for url in urls:
                from crawlo.network.request import Request
                await self.scheduler.enqueue_request(Request(url=url))

    # ========================================================================
    # 后台循环
    # ========================================================================

    async def _failover_loop(self):
        """故障检测后台循环"""
        while self.running:
            try:
                await self._cluster_state.failover.check_and_recover()
                await asyncio.sleep(self._cluster_state.failover.failover_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

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
