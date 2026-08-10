# 分布式 Worker 生命周期与集群组件

> 从 `distributed_architecture.md` 拆分而来，讲述 Worker 启动/运行/退出与集群组件职责。

## 4. Worker 生命周期

### 4.1 启动流程

```
run.py
 └─ CrawlerProcess.crawl(spider_name)
 └─ Engine.start_spider(spider)
 ├─ 1. Scheduler.create_instance() → QueueManager + RedisStreamQueue
 ├─ 2. Downloader.create()
 ├─ 3. Processor.create()
 ├─ 4. ExtensionManager
 ├─ 5. Engine.engine_start()
 ├─ 6. _init_cluster() ←── 初始化 9 个集群组件
 ├─ 7. Checkpoint resume (if enabled)
 ├─ 8. start_requests (spider 种子 URL 生成)
 ├─ 各 Worker SETNX 竞选种子生成器 (只有一个生成 start_requests)
 └─ 9. _open_spider() → crawl()
```

### 4.2 `_init_cluster()` 初始化顺序

```
_step 0_: 获取/创建 RedisStreamQueue + Redis 客户端
_step 0.5_: 创建 Leader 选举 DistributedLock (SET NX PX 原子获取)

_step 1_: WorkerRegistry.register(worker_info)
 ─ 生成 worker_id = "{host}-{pid}-{uuid[:8]}"
 ─ HSET registry:workers ZADD registry:heartbeats

_step 2_: HeartbeatDaemon(registry, worker_id, interval=15s ±20% jitter)
 ─ 注入 TaskTracker 作为 stats provider
 ─ 心跳携带 tasks_completed / tasks_failed / tasks_processing

_step 3_: DistributedLock("lock:failover")
 ─ 默认 TTL=30s, 3次重试, 0.5s间隔
 ─ acquire: SET NX PX (原子)
 ─ release: Lua 脚本 (防误删)

_step 4_: FailoverManager(registry, queue, lock, redis)
 ─ suspect_timeout=30s, failover_interval=30s

_step 5_: ProgressAggregator(redis, key_manager)
 ─ 每 10s 上报一次全局统计 (HINCRBY)

_step 6_: DistributedRateLimiter(redis)
 ─ Lua 令牌桶, 默认关闭

_step 7_: ClusterMonitor(registry, progress, stream_queue, failover)
 ─ 集群状态总览

_step 8_: ClusterMessenger(redis)
 ─ Pub/Sub 监听 4 个频道: control config events alerts
 ─ 断连自动重连 (2s间隔)

_step 9_: DynamicConfig(redis, messenger, rate_limiter)
 ─ 双通道: Pub/Sub 即时 + Redis Key 持久化兜底
```

### 4.3 运行状态

```python
# main loop (crawl()):
while self.running:
 # 1. 检查控制状态 (paused/shutdown)
 state = dynamic_config.get_control_state()
 
 # 2. 从队列取任务
 for _ in range(batch_size):
 request = scheduler.next_request()
 # └─ XREADGROUP GROUP group consumer BLOCK ms STREAMS stream >
 
 # 3. 批量派发 (受 max_inflight 流控)
 for req in requests:
 _create_background_task(_crawl(req))
 
 # 4. 空闲处理
 if 无任务:
 if run_mode == 'distributed':
 # BZPOPMIN 阻塞等待 or XREADGROUP BLOCK
 request = scheduler.next_request_blocking(timeout=30s)
 # 空闲超时 (idle_timeout=120s) → Worker 自动退出
```

### 4.4 优雅关闭

```
触发源: SIGTERM / Leader broadcast shutdown / Pub/Sub shutdown 消息

Engine.close_spider(reason='shutdown')
 └─ _shutdown_cluster()
 ├─ 0. update_status(STATUS_STOPPING) ← 标记停止，防止 failover 误回收
 ├─ 1. stop ClusterMessenger (Pub/Sub 断开)
 ├─ 2. stop HeartbeatDaemon (停止心跳)
 ├─ 3. cancel FailoverManager (停止故障检测，await 完成)
 ├─ 4. cancel Leader 选举循环 (await 完成)
 ├─ 5. release Leader lock (Lua 原子释放)
 ├─ 6. _drain_inflight_tasks() (等待在途任务完成, timeout=30s)
 │ └─ 超时 → cancel + await gather 残留任务 (由 failover 回收)
 └─ 7. WorkerRegistry.deregister()
 ─ HDEL registry:workers ZREM registry:heartbeats
```

### 4.5 动态扩缩容

#### 新增 Worker（Scale Up）

运行中加入新 Worker，**即插即用，无需任何人工干预**。

```
新 Worker 启动 Redis
 │ │
 ├─ SETNX seed:generator ────────────► │ 已存在 → 返回 False
 │ └─ 跳过 start_requests │ 避免重复生成种子 URL
 │ │
 ├─ WorkerRegistry.register() ───────► │ HSET registry + ZADD heartbeats
 ├─ HeartbeatDaemon.start() │
 │ │
 ├─ XGROUP CREATECONSUMER ───────────► │ Consumer Group 加入新消费者
 │ │ Redis 自动负载均衡后续 XREADGROUP 消息
 │ │
 ├─ _recover_orphan_pending() │
 │ └─ XINFO CONSUMERS │
 │ → 活跃 Consumer 存在 (idle<30s) │
 │ → 跳过孤儿回收 │ │ │
 └─ main loop │
 └─ XREADGROUP stream > ──────────► │ 立即参与消息消费
 │ Pub/Sub 同步限速/配置
```

| 步骤 | 机制 | 说明 |
|---|---|---|
| 种子生成 | `SET NX EX 120` | 首个 Worker 获取锁后生成种子，后续 Worker 跳过 |
| 消费组加入 | `XGROUP CREATECONSUMER` | Redis 自动负载均衡，新 Consumer 无缝接管 |
| 孤儿回收 | `XINFO CONSUMERS` idle 检查 | 已有活跃 Consumer → 不误触回收 |
| 配置同步 | Pub/Sub + 持久化 Key | 即时 + 兜底，新 Worker 自动继承当前配置 |
| 进度统计 | `ProgressAggregator` | `HINCRBY` 全局聚合，新 Worker 统计自动合并 |

#### Worker 退出（Scale Down）

##### 正常退出（SIGTERM / 协调退出信号）

```
退出的 Worker 其他 Worker
 │ │
 ├─ update_status(STOPPING) ──► Redis │
 │ │ ├─ FailoverManager 扫描到该 Worker
 │ │ │ status == "stopping" → 跳过 ├─ _drain_inflight_tasks() │ │
 │ └─ 等待在途任务完成(30s) │ │
 │ ├─ 完成 → XACK │ │ │ └─ 超时 → cancel │ │
 │ └─ NACK → 回到 Stream │ │
 │ │ ├─ XREADGROUP 取到该消息
 │ │ │ 正常处理 → XACK
 │ │ │
 └─ deregister() ────────────────► Redis │
```

- **STATUS_STOPPING 豁免**：FailoverManager 跳过 stopping 状态的 Worker，防止 drain 期间误回收
- **Drain 兜底**：30 秒超时后 cancel 并 NACK 回 Stream，其他 Worker 自动接管

##### 崩溃退出（进程 kill、OOM、网络分区）

```
时间线 事件
─────────────────────────────────────────────────────
t=0 Worker 崩溃，心跳停止
t=90s detect_dead_workers() 心跳超时 → mark suspect
t=120s 二次确认 → DistributedLock 持锁 → 正式回收

崩溃 Worker 其他 Worker
 │ │
 │ heartbeat 停止 ──► Redis ZSET 无更新 │
 │ │ │
 │ │ 每 30s 执行 FailoverManager.check_and_recover()
 │ │ ├─ Phase 1: mark suspect (防网络抖动)
 │ │ └─ Phase 2 (30s 后确认):
 │ │ └─ DistributedLock 持锁
 │ │ ├─ XAUTOCLAIM 回收两个 Stream
 │ │ │ └─ XRANGE → XACK+XDEL → XADD (retry+1)
 │ │ │ 超限 → stream:failed (死信)
 │ │ └─ deregister()
```

**最坏恢复时间**：约 120 秒（90s 超时 + 30s 确认）。

#### 数据丢失分析

| 崩溃时机 | 丢数据？ | 处理方式 |
|---|---|---|
| 消息仍在 Stream 未消费 | **不丢**| XREADGROUP 原子分配，其他 Worker 正常读取 |
| 消息已消费、下载中 | **不丢**| 消息在 PEL pending 中，XAUTOCLAIM 回收重新入队 |
| 处理完成、ACK 前 | **不丢，可能重复**| 回收重新执行（**至少一次**语义）；MySQL 唯一键 / dedup 作为最后防线 |
| 处理完成、ACK 后 | **不丢**| XACK 已将消息从 PEL 移除 |
| 死信 | **不丢**| 转入 `stream:failed`，通过 `crawlo dead-letter list/retry` 排查或重新入队 |

> **唯一风险——重复消费**：Worker 完成 MySQL 写入但 XACK 前崩溃 → 消息被回收重放。
> 数据库唯一键约束保证幂等写入，不会产生脏数据。

---


## 5. 集群组件详解

### 5.1 WorkerRegistry

**数据结构**：
```
registry:workers (HASH)
 worker:{worker_id} → {
 "id": "host-pid-uuid",
 "host": "localhost",
 "pid": 12345,
 "concurrency": 12,
 "started_at": 1234567890.0,
 "status": "running",
 "tasks_completed": 100,
 "tasks_failed": 5,
 "tasks_processing": 3,
 "last_heartbeat": 1234567890.0
 }

registry:heartbeats (ZSET)
 worker:{worker_id} → Unix timestamp (score)
```

**状态机**：
```
 running ──超时──► suspect ──二次确认──► deregister
 │ │ ▲
 │ └──恢复心跳──────────┘
 │
 ├──优雅退出────► stopping ──drain完成──► deregister
 │ │
 │ └── failover 豁免（不回收 stopping 状态的 Worker 任务）
 │
 └──主动上报────► idle
```

> **STATUS_STOPPING 豁免**：Worker 被标记为 stopping 后，FailoverManager 的
> `_handle_suspected_worker` 会跳过该 Worker，防止在优雅退出过程中误回收其正在 drain 的任务。

**detect_dead_workers()**：
```python
# 使用 ZRANGEBYSCORE 查心跳过期的 Worker
deadline = time.time() - worker_timeout # 默认 90s
dead = redis.zrangebyscore(heartbeats_key, 0, deadline)
# 返回不含 "worker:" 前缀的 ID 列表
```

### 5.2 HeartbeatDaemon

```
心跳间隔: 15s (CLUSTER_HEARTBEAT_INTERVAL)
Jitter: ±20% (12s~18s，防止心跳风暴)

_loop():
 while _running:
 stats = _collect_stats() # 从 TaskTracker 读取
 registry.heartbeat(worker_id, extra=stats)
 sleep(interval * (1 + random.uniform(-0.2, 0.2)))
 失败 → sleep(5s) # 短间隔重试，无 jitter
```

### 5.3 DistributedLock

基于 Redis 的简化 Redlock，原子所有操作：

| 操作 | Redis 命令 | 防误操作机制 |
|---|---|---|
| `acquire(timeout)` | `SET key val NX PX ttl` | 一步原子获取 + 自动过期 |
| `release(holder_id)` | Lua: `if GET == holder then DEL` | 仅持有者可释放 |
| `extend(additional)` | Lua: `if GET == holder then PEXPIRE` | 仅持有者可续期 |

### 5.4 FailoverManager

**两阶段故障检测**：

```
Phase 1 (首次检测):
 detect_dead_workers(timeout=90s)
 ─ 对每个 dead worker:
 ├─ 检查 worker status
 │ ├─ STATUS_STOPPING → 跳过（正在优雅退出，不应回收）
 │ └─ 其他状态 → 继续
 ├─ 第1次发现 → update_status(suspect, suspect_since=now)
 └─ 已知 suspect → 进入 Phase 2

Phase 2 (二次确认, suspect_status > 30s):
 获取 DistributedLock("lock:failover", timeout=30s)
 ─ 持锁后：
 ├─ _claim_worker_tasks(dead_worker_id)
 │ └─ 同时回收两个 Stream 的 pending：high + normal
 │ └─ 循环 claim_pending(min_idle=60s, count=100)
 │ └─ 对每条消息: XRANGE → XACK+XDEL → XADD (重新入队到原 Stream)
 │ ├─ retry_count+1
 │ ├─ 标记 failover_from=dead_worker_id
 │ └─ 超限 → XADD stream:failed (死信)
 └─ deregister(dead_worker_id)
 释放锁
```

**Failover 后台循环**：
```python
_failover_interval = 30s
while running:
 check_and_recover()
 sleep(30s)
```

### 5.5 ClusterMessenger + DynamicConfig (双通道通信)

```
┌──────────────────────────────────────┐
│ 即时通道: Pub/Sub │
│ channel:control → _on_control_msg │
│ (pause / resume / shutdown) │
│ channel:config → _on_config_msg │
│ (rate_limit / seed_urls) │
│ │
│ 断连 → 2s 自动重连 + 重新订阅 │
└──────────────────────────────────────┘
 │
 │ 消息可能丢失 (fire-and-forget)
 ▼
┌──────────────────────────────────────┐
│ 持久化通道: Redis Key │
│ control:state (STRING) │
│ ─ SET "paused"/"running"/"shutdown"│
│ ─ 每个循环周期检查，兜底恢复 │
│ │
│ config:rate_limits (HASH) │
│ config:seed_urls (LIST) │
│ config:concurrency (HASH) │
└──────────────────────────────────────┘
```

**控制消息处理**：
```python
_on_control_message(action):
 "pause" → _cluster_paused = True
 "resume" → _cluster_paused = False
 "shutdown" → self.running = False

_on_config_message(action):
 "rate_limit" → rate_limiter.set_rate(domain, rate)
 "seed_urls" → pop seed URLs → scheduler.enqueue()
```

---

