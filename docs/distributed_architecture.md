# Crawlo 分布式架构设计文档

---

## 目录

- [1. 架构概览](#1-架构概览)
  - [设计原则](#设计原则)
  - [激活条件](#激活条件)
  - [Redis 版本要求](#redis-版本要求)
  - [架构全景](#架构全景)
  - [核心特性](#核心特性)
- [2. Redis Key 命名空间](#2-redis-key-命名空间)
  - [2.1 完整 Key 清单](#21-完整-key-清单)
- [3. 任务生命周期](#3-任务生命周期)
  - [关键点](#关键点)
- [4. Worker 生命周期](#4-worker-生命周期)
  - [4.1 启动流程](#41-启动流程)
  - [4.2 _init_cluster() 初始化顺序](#42-_init_cluster-初始化顺序)
  - [4.3 运行状态](#43-运行状态)
  - [4.4 优雅关闭](#44-优雅关闭)
  - [4.5 动态扩缩容](#45-动态扩缩容)
- [5. 集群组件详解](#5-集群组件详解)
  - [5.1 WorkerRegistry](#51-workerregistry)
  - [5.2 HeartbeatDaemon](#52-heartbeatdaemon)
  - [5.3 DistributedLock](#53-distributedlock)
  - [5.4 FailoverManager](#54-failovermanager)
  - [5.5 双通道通信](#55-clustermessenger-dynamicconfig-双通道通信)
- [6. 消息可靠投递](#6-消息可靠投递)
  - [6.1 ACK/NACK 机制](#61-ack--nack-机制)
  - [6.2 重试与死信](#62-重试与死信)
  - [6.3 序列化策略](#63-序列化策略)
- [7. 故障恢复](#7-故障恢复)
  - [7.1 孤儿 Pending 回收](#71-孤儿-pending-回收-启动时)
  - [7.2 Failover 任务回收](#72-failover-任务回收-运行时)
  - [7.3 恢复对比](#73-恢复对比)
- [8. 协调退出](#8-协调退出)
  - [8.1 Leader 选举](#81-leader-选举)
  - [8.2 退出时序](#82-退出时序)
- [9. 动态配置](#9-动态配置)
  - [9.1 控制命令](#91-控制命令)
  - [9.2 运行时配置](#92-运行时配置)
- [10. 配置参考](#10-配置参考)
  - [10.1 核心配置](#101-核心配置)
  - [10.2 集群配置](#102-集群配置)
  - [10.3 Stream 配置](#103-stream-配置)
  - [10.4 Worker 行为](#104-worker-行为)
- [附录 A：Worker 批量启动脚本](#附录-aworker-批量启动脚本)
- [附录 B：监控命令](#附录-b监控命令)

---

## 1. 架构概览

### 设计原则

Crawlo 分布式系统采用 **无中心 Leader + Redis 中心化存储** 架构。

- 所有 Worker 对等，平等竞争任务
- Redis 作为唯一的状态存储和协调中心
- 仅在"协调退出"场景中存在临时 Leader（自选举，仅用于广播退出信号）

### 激活条件

```
RUN_MODE = "distributed"
QUEUE_TYPE = "redis_stream"
```

两个条件同时满足时，集群组件（9 个子模块）全部启动。

### Redis 版本要求

| 需求 | 版本 | 说明 |
|---|---|---|
| **最低版本** | **Redis 5.0+** | Stream 基础功能（XADD / XREADGROUP / XACK / XCLAIM） |
| **推荐版本** | **Redis 6.2+** | XAUTOCLAIM 一步完成 orphan 回收，效率更高 |
| **部署推荐** | **Redis 7+** | 生产环境推荐使用最新稳定版（`redis:7-alpine`） |
| **最高版本** | **无上限** | 向下兼容，无最大版本限制 |

**自动降级策略**：框架启动时通过 `crawlo.utils.redis.stream_utils` 检测 Redis 版本：
- `supports_xstream()` → 检查 `major >= 5`，不满足则**无法使用分布式模式**
- `supports_xautoclaim()` → 检查 `major > 6 or (major == 6 and minor >= 2)`
  - ✅ 6.2+：使用 XAUTOCLAIM（原子 claim + 自动清理已删除消息）
  - ⚠️ 5.0-6.1：降级为 XPENDING + XCLAIM 手动两步回收（功能等价，多一次 Redis 往返）

> `crawlo/utils/redis/stream_utils.py` 中 `detect_redis_version()` 从 Redis INFO 命令
> 解析版本号，连接时自动检测并记录日志。

#### 各版本对分布式设计的影响

Crawlo 的分布式设计**不因 Redis 版本而改变架构思路**——始终基于 Stream + Consumer Groups + ACK。
不同版本的区别仅在于**故障回收的实现路径**和**性能开销**：

**Redis 5.0-6.1（最低可用）**

Stream 在 5.0 引入，提供了 Crawlo 分布式所需的全部基础原语：
- `XADD`（入队）、`XREADGROUP`（消费）、`XACK`（确认）、`XCLAIM`（手动转移任务）
- `XPENDING`（查询 PENDING 列表）

但缺少 `XAUTOCLAIM` 命令（6.2 才引入）。Crawlo 在此版本下的故障回收路径为：

```
XPENDING（列出超时任务）→ 逐条 XCLAIM（转移所有权）→ XRANGE（读内容）
  → XACK + XDEL（清理原消息）→ XADD（重新入队，retry+1）
```

这是**三步手动回收**，每次回收一批任务需要多次 Redis 往返。功能上与 XAUTOCLAIM 完全等价，
但在高并发故障场景下（如同时崩溃多个 Worker），回收延迟略高（多 1-2 次 RTT）。

**Redis 6.2+（推荐）**

引入了 `XAUTOCLAIM` 命令，将上述三步合并为一步原子操作：

```
XAUTOCLAIM（自动 claim 超时任务 + 返回任务内容）→ XACK + XDEL → XADD
```

Crawlo 在此版本下：
- 孤儿回收（启动时）：单次 `XAUTOCLAIM` 批量 claim，减少 Redis 往返
- Failover 回收（运行时）：持有 DistributedLock 后执行 `XAUTOCLAIM`，原子性更强
- 自动清理已删除的消息，避免 PENDING 列表膨胀

**Redis 7+（生产推荐）**

7.0+ 在 Stream 性能和稳定性上有显著提升，但 Crawlo 的分布式设计思路不变：
- Stream 的 `MAXLEN` trimming 性能优化（`XADD ... MAXLEN ~ N` 近似修剪更高效）
- ACL（访问控制列表）支持更完善，适合多团队共享 Redis 的场景
- Sentinel 和 Cluster 的故障转移速度更快（对 Crawlo 透明，Crawlo 只需重连）

> **总结**：Redis 版本影响的是故障回收的效率，不是架构设计。Crawlo 在 5.0 上就能
> 完整运行分布式模式，6.2+ 只是让故障回收更快更简洁。

### 架构全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             Redis (7.2+)                                 │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐  │
│  │  Stream Queue    │ │  Worker          │ │  Config & Control        │  │
│  │  ─ tasks (normal)│ │  Registry        │ │  ─ rate_limits (HASH)    │  │
│  │  ─ tasks:high    │ │  ─ workers HASH  │ │  ─ seed_urls (LIST)      │  │
│  │  ─ failed (DLQ)  │ │  ─ heartbeats    │ │  ─ control:state (STR)   │  │
│  │  ─ Consumer Group│ │    ZSET          │ │  ─ Pub/Sub 2 channels    │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐  │
│  │  Dedup Sets      │ │  Progress        │ │  Locks                   │  │
│  │  ─ dedup:request │ │  Aggregator      │ │  ─ lock:leader (选举)    │  │
│  │  ─ dedup:item    │ │  ─ stats HASH    │ │  ─ lock:failover (互斥)  │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────────┘  │
│  ┌──────────────────┐ ┌──────────────────────────────────────────────┐  │
│  │  Seed Generator   │ │  DistributedRateLimiter (Lua Token Bucket)    │  │
│  │  ─ SETNX 互斥     │ └──────────────────────────────────────────────┘  │
│  └──────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │  XREADGROUP / XACK            │  Heartbeat / Failover
         │  Pub/Sub                      │  Progress Report
         │                               │
  ┌──────┴──────┐               ┌───────┴───────┐
  │  Worker #1  │     ...       │  Worker #N    │
  │  ─ Engine   │               │  ─ Engine     │
  │  ─ Spiders  │               │  ─ Spiders    │
  │  ─ Heartbeat│               │  ─ Heartbeat  │
  │  ─ Failover │               │  ─ Failover   │
  └─────────────┘               └───────────────┘
```

### 核心特性

| 特性 | 说明 |
|---|---|
| **无中心 Leader** | 所有 Worker 对等，平等竞争任务；仅在协调退出时自选举临时 Leader |
| **双 Stream 优先级** | 高优 `stream:tasks:high` + 普通 `stream:tasks`，支持 `STREAM_PRIORITY_ENABLED` 开关 |
| **Consumer Group + ACK** | XREADGROUP 消费 + XACK 确认，崩溃任务自动回收 |
| **种子去重** | Worker 通过 SETNX 互斥选举唯一的种子 URL 生成器 |
| **两阶段故障检测** | suspect 标记 → 30s 二次确认 → XAUTOCLAIM 回收 |
| **优雅协调退出** | Leader 检测全部空闲 → 广播 shutdown → 所有 Worker drain 后退出 |
| **动态扩缩容** | 新 Worker 即插即用，崩溃 Worker 任务 120s 内自动回收，不丢数据 |
| **持久化控制状态** | 双通道 (Pub/Sub + Redis Key) 保证退出信号不丢失 |

---

## 2. Redis Key 命名空间

所有 Key 遵循 `crawlo:{project}:{spider}:{component}:{sub}` 命名规范。

### 2.1 完整 Key 清单

| 组件 | Key 模式 | 数据类型 | 用途 |
|---|---|---|---|
| **StreamQueue** | `crawlo:{ns}:stream:tasks` | STREAM | 普通优先级任务队列 |
| | `crawlo:{ns}:stream:tasks:high` | STREAM | 高优先级任务队列（priority < 0） |
| | `crawlo:{ns}:stream:failed` | STREAM | 死信队列 |
| | `crawlo:{ns}:group:workers` | CONSUMER GROUP | 消费者组名 |
| **Registry** | `crawlo:{ns}:registry:workers` | HASH | Worker 注册表 |
| | `crawlo:{ns}:registry:heartbeats` | ZSET | 心跳时间戳 (score=timestamp) |
| **Dedup** | `crawlo:{ns}:dedup:request` | SET | 请求去重指纹 |
| | `crawlo:{ns}:dedup:item` | SET | 数据项去重指纹 |
| **Progress** | `crawlo:{ns}:progress:stats` | HASH | 全局统计 |
| | `crawlo:{ns}:progress:first_report` | STRING | 首次上报时间戳 |
| **RateLimiter** | `crawlo:{ns}:rate:{domain}` | STRING | 令牌计数 |
| | `crawlo:{ns}:rate:{domain}:ts` | STRING | 上次补充时间戳 |
| **Lock** | `crawlo:{ns}:lock:failover` | STRING | Failover 互斥锁（SET NX PX） |
| | `crawlo:{ns}:lock:leader` | STRING | Leader 选举锁（SET NX PX + Lua 续期） |
| **Seed** | `crawlo:{ns}:seed:generator` | STRING | 种子生成器选举锁（SET NX EX 120） |
| **Config** | `crawlo:{ns}:control:state` | STRING | 控制状态（running/paused/shutdown） |
| | `crawlo:{ns}:config:rate_limits` | HASH | 域名速率覆盖 |
| | `crawlo:{ns}:config:seed_urls` | LIST | 动态种子 URL |
| | `crawlo:{ns}:config:concurrency` | HASH | Worker 并发度 |

> `{ns}` = `{project}:{spider}`，如 `ofweek_distributed:of_week_distributed`

---

## 3. 任务生命周期

每个爬取请求在分布式系统中的完整生命周期：

```
                        Worker A                         Worker B
                        
  Spider.start_requests()
         │
         ▼
  种子生成器选举（SET NX EX 120）
     ├── 获取成功 → 生成 start_requests
     └── 获取失败 → skip（另一个 Worker 已在生成）
         │
         ▼
    生成 Request ────► scheduler.enqueue_request()
                              │
                              ▼
                      dupe filter 检查
                      (Redis SET: dedup:request)
                         │         │
                    新 URL │         │ 已存在
                         ▼         ▼
                   QueueManager.put()   丢弃 (日志: Filtered duplicate)
                         │
                         ▼
              RedisStreamQueue.put()
              ┌─ priority < 0 → XADD stream:tasks:high
              └─ priority ≥ 0 → XADD stream:tasks
                    * data priority retry_count enqueued_at
                         │
         ┌───────────────┴────────────────┐
         │                                │
         ▼                                ▼
  XREADGROUP stream >                  XREADGROUP stream >
  (_read: 先非阻塞 high,                (_read: 先非阻塞 high,
   后阻塞 normal)                       后阻塞 normal)
         │                                │
         ▼                                ▼
  _parse_message()                   _parse_message()
  注入 meta:                          注入 meta:
    __stream_message_id                 __stream_message_id
    __stream_retry_count                __stream_retry_count
    __stream (stream key)               __stream (stream key)
  记录映射:                            记录映射:
    _message_stream[id]=stream     _message_stream[id]=stream
         │                                │
         ▼                                ▼
  Engine._crawl()                      Engine._crawl()
  ├─ Downloader.fetch()                ├─ Downloader.fetch()
  ├─ Spider callback                   ├─ Spider callback
  ├─ Pipeline                          ├─ Pipeline
  └─ _ack_message(success=True)        └─ _ack_message(success=False)
         │                                    │
         ▼                                    ▼
  scheduler.ack_request()              scheduler.nack_request()
  ├─ _get_message_stream(id)           ├─ classify error → RETRY/DEAD
  │   → 查 _message_stream 映射        ├─ _get_message_stream(id)
  │   → 路由到正确的 Stream            │   → 路由到正确的 Stream
  ├─ XACK (从 pending 移除)            ├─ XRANGE (读原始字段)
  └─ XDEL (物理删除消息)               ├─ XACK + XDEL
                                       └─ XADD (重入队，retry_count+1)
                                                     │
                                              超 max_delivery?
                                              YES ──► XADD stream:failed
```

### 关键点

- **种子去重**：所有 Worker 启动时通过 `SET NX EX 120` 竞选种子生成器，只有一个 Worker 生成 `start_requests`。其余 Worker 跳过种子生成，直接进入任务消费。种子生成器启动后台续期任务（每 60 秒延长 TTL），启动前检测死锁并自动接管
- **双 Stream 路由**：`priority < 0` → `stream:tasks:high`；`priority ≥ 0` → `stream:tasks`。可通过 `STREAM_PRIORITY_ENABLED=False` 降级为单 Stream
- **优先级消费策略**：`_read()` 策略为先非阻塞检查高优 Stream（10ms 超时），有消息则返回；无消息则阻塞等待普通 Stream
- **消息-Stream 映射**：`_message_stream` 字典记录每个 `message_id` 的来源 Stream，确保 ACK/NACK 路由回正确的 Stream
- **入队去重**：`QueueManager.put()` → `AioRedisFilter` 检查 Redis SET，已存在的 URL 不入队
- **ACK + XDEL**：ACK 后立即 XDEL，避免 Stream 堆积已处理消息
- **NACK 重入队**：XRANGE 读原字段 → XACK+XDEL 原消息 → XADD 重新入队（retry+1），保证幂等重放
- **死信升级**：`retry_count >= delivery_count_limit (3)` → 转入 `stream:failed`

---

## 4. Worker 生命周期

### 4.1 启动流程

```
run.py
  └─ CrawlerProcess.crawl(spider_name)
       └─ Engine.start_spider(spider)
            ├─ 1. Scheduler.create_instance()    → QueueManager + RedisStreamQueue
            ├─ 2. Downloader.create()
            ├─ 3. Processor.create()
            ├─ 4. ExtensionManager
            ├─ 5. Engine.engine_start()
            ├─ 6. _init_cluster()     ←── 初始化 9 个集群组件
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
          ─ HSET registry:workers  ZADD registry:heartbeats

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
        #   └─ XREADGROUP GROUP group consumer BLOCK ms STREAMS stream >
    
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
       ├─ 2. stop HeartbeatDaemon     (停止心跳)
       ├─ 3. cancel FailoverManager   (停止故障检测，await 完成)
       ├─ 4. cancel Leader 选举循环   (await 完成)
       ├─ 5. release Leader lock      (Lua 原子释放)
       ├─ 6. _drain_inflight_tasks()  (等待在途任务完成, timeout=30s)
       │       └─ 超时 → cancel + await gather 残留任务 (由 failover 回收)
       └─ 7. WorkerRegistry.deregister()
              ─ HDEL registry:workers  ZREM registry:heartbeats
```

### 4.5 动态扩缩容

#### 新增 Worker（Scale Up）

运行中加入新 Worker，**即插即用，无需任何人工干预**。

```
新 Worker 启动                         Redis
  │                                     │
  ├─ SETNX seed:generator ────────────► │ 已存在 → 返回 False
  │  └─ 跳过 start_requests             │ 避免重复生成种子 URL
  │                                     │
  ├─ WorkerRegistry.register() ───────► │ HSET registry + ZADD heartbeats
  ├─ HeartbeatDaemon.start()            │
  │                                     │
  ├─ XGROUP CREATECONSUMER ───────────► │ Consumer Group 加入新消费者
  │                                     │ Redis 自动负载均衡后续 XREADGROUP 消息
  │                                     │
  ├─ _recover_orphan_pending()          │
  │  └─ XINFO CONSUMERS                │
  │    → 活跃 Consumer 存在 (idle<30s) │
  │    → 跳过孤儿回收 ✓                 │
  │                                     │
  └─ main loop                          │
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
退出的 Worker                              其他 Worker
  │                                          │
  ├─ update_status(STOPPING) ──► Redis       │
  │                               │           ├─ FailoverManager 扫描到该 Worker
  │                               │           │   status == "stopping" → 跳过 ✓
  ├─ _drain_inflight_tasks()      │           │
  │  └─ 等待在途任务完成(30s)      │           │
  │     ├─ 完成 → XACK ✓          │           │
  │     └─ 超时 → cancel          │           │
  │        └─ NACK → 回到 Stream   │           │
  │                               │           ├─ XREADGROUP 取到该消息
  │                               │           │   正常处理 → XACK
  │                               │           │
  └─ deregister() ────────────────► Redis     │
```

- **STATUS_STOPPING 豁免**：FailoverManager 跳过 stopping 状态的 Worker，防止 drain 期间误回收
- **Drain 兜底**：30 秒超时后 cancel 并 NACK 回 Stream，其他 Worker 自动接管

##### 崩溃退出（进程 kill、OOM、网络分区）

```
时间线                    事件
─────────────────────────────────────────────────────
t=0       Worker 崩溃，心跳停止
t=90s     detect_dead_workers() 心跳超时 → mark suspect
t=120s    二次确认 → DistributedLock 持锁 → 正式回收

崩溃 Worker                                 其他 Worker
  │                                            │
  │ heartbeat 停止 ──► Redis ZSET 无更新       │
  │                     │                      │
  │                     │    每 30s 执行 FailoverManager.check_and_recover()
  │                     │    ├─ Phase 1: mark suspect (防网络抖动)
  │                     │    └─ Phase 2 (30s 后确认):
  │                     │       └─ DistributedLock 持锁
  │                     │          ├─ XAUTOCLAIM 回收两个 Stream
  │                     │          │   └─ XRANGE → XACK+XDEL → XADD (retry+1)
  │                     │          │       超限 → stream:failed (死信)
  │                     │          └─ deregister()
```

**最坏恢复时间**：约 120 秒（90s 超时 + 30s 确认）。

#### 数据丢失分析

| 崩溃时机 | 丢数据？ | 处理方式 |
|---|---|---|
| 消息仍在 Stream 未消费 | **不丢** | XREADGROUP 原子分配，其他 Worker 正常读取 |
| 消息已消费、下载中 | **不丢** | 消息在 PEL pending 中，XAUTOCLAIM 回收重新入队 |
| 处理完成、ACK 前 | **不丢，可能重复** | 回收重新执行（**至少一次**语义）；MySQL 唯一键 / dedup 作为最后防线 |
| 处理完成、ACK 后 | **不丢** | XACK 已将消息从 PEL 移除 |
| 死信 | **不丢** | 转入 `stream:failed`，通过 `crawlo dead-letter list/retry` 排查或重新入队 |

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
    │                  │                    ▲
    │                  └──恢复心跳──────────┘
    │
    ├──优雅退出────► stopping ──drain完成──► deregister
    │                   │
    │                   └── failover 豁免（不回收 stopping 状态的 Worker 任务）
    │
    └──主动上报────► idle
```

> **STATUS_STOPPING 豁免**：Worker 被标记为 stopping 后，FailoverManager 的
> `_handle_suspected_worker` 会跳过该 Worker，防止在优雅退出过程中误回收其正在 drain 的任务。

**detect_dead_workers()**：
```python
# 使用 ZRANGEBYSCORE 查心跳过期的 Worker
deadline = time.time() - worker_timeout  # 默认 90s
dead = redis.zrangebyscore(heartbeats_key, 0, deadline)
# 返回不含 "worker:" 前缀的 ID 列表
```

### 5.2 HeartbeatDaemon

```
心跳间隔: 15s (CLUSTER_HEARTBEAT_INTERVAL)
Jitter:    ±20% (12s~18s，防止心跳风暴)

_loop():
  while _running:
      stats = _collect_stats()  # 从 TaskTracker 读取
      registry.heartbeat(worker_id, extra=stats)
      sleep(interval * (1 + random.uniform(-0.2, 0.2)))
      失败 → sleep(5s)  # 短间隔重试，无 jitter
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
      │    ├─ STATUS_STOPPING → 跳过（正在优雅退出，不应回收）
      │    └─ 其他状态 → 继续
      ├─ 第1次发现 → update_status(suspect, suspect_since=now)
      └─ 已知 suspect → 进入 Phase 2

Phase 2 (二次确认, suspect_status > 30s):
  获取 DistributedLock("lock:failover", timeout=30s)
  ─ 持锁后：
      ├─ _claim_worker_tasks(dead_worker_id)
      │    └─ 同时回收两个 Stream 的 pending：high + normal
      │    └─ 循环 claim_pending(min_idle=60s, count=100)
      │         └─ 对每条消息: XRANGE → XACK+XDEL → XADD (重新入队到原 Stream)
      │              ├─ retry_count+1
      │              ├─ 标记 failover_from=dead_worker_id
      │              └─ 超限 → XADD stream:failed (死信)
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
│          即时通道: Pub/Sub            │
│  channel:control → _on_control_msg   │
│    (pause / resume / shutdown)       │
│  channel:config  → _on_config_msg    │
│    (rate_limit / seed_urls)          │
│                                      │
│  断连 → 2s 自动重连 + 重新订阅       │
└──────────────────────────────────────┘
         │
         │ 消息可能丢失 (fire-and-forget)
         ▼
┌──────────────────────────────────────┐
│        持久化通道: Redis Key          │
│  control:state (STRING)              │
│    ─ SET "paused"/"running"/"shutdown"│
│    ─ 每个循环周期检查，兜底恢复       │
│                                      │
│  config:rate_limits (HASH)           │
│  config:seed_urls (LIST)             │
│  config:concurrency (HASH)           │
└──────────────────────────────────────┘
```

**控制消息处理**：
```python
_on_control_message(action):
    "pause"    → _cluster_paused = True
    "resume"   → _cluster_paused = False
    "shutdown" → self.running = False

_on_config_message(action):
    "rate_limit" → rate_limiter.set_rate(domain, rate)
    "seed_urls"  → pop seed URLs → scheduler.enqueue()
```

---

## 6. 消息可靠投递（Lua 原子化 ACK/NACK/重试）

### 6.1 ACK / NACK 机制

ACK 使用 Lua 脚本在 Redis 服务端原子执行 XACK + XDEL，消除进程崩溃窗口：

```python
async def _ack_message(request, engine, success, error=None):
    if not engine._cluster_worker_id:
        return  # 非分布式模式，跳过

    message_id = request.meta['__stream_message_id']

    if success:
        # Lua 脚本原子执行 XACK + XDEL
        # → 消除了 XACK 和 XDEL 之间的崩溃窗口（幽灵消息问题）
        await engine.scheduler.ack_request(message_id)
    else:
        result = engine._task_tracker.classify_error(error)
        # → RETRY / DEAD_LETTER / ACK
        # 重试路径同样使用 Lua 脚本原子执行：XRANGE + XACK + XDEL + XADD
        await engine.scheduler.nack_request(message_id, result=result)
```

**原子 ACK Lua 脚本**：
```lua
local acked = redis.call('XACK', KEYS[1], ARGV[1], ARGV[2])
if acked > 0 then
    redis.call('XDEL', KEYS[1], ARGV[2])
end
return tostring(acked)
```

**原子重试 Lua 脚本**（XRANGE → 转 hash 表 → XACK+XDEL → XADD 重新入队，全程原子）：
```lua
local msgs = redis.call('XRANGE', KEYS[1], ARGV[1], ARGV[1], 'COUNT', 1)
local flat = msgs[1][2]
local fields = {}
for i = 1, #flat, 2 do fields[flat[i]] = flat[i + 1] end
-- 注意：XRANGE 返回的 fields 是平铺数组 [k1,v1,k2,v2,...]，需先转 hash 表
local retry_count = 1
if fields['retry_count'] then retry_count = tonumber(fields['retry_count']) + 1 end
if retry_count >= tonumber(ARGV[5]) then
    redis.call('XACK', KEYS[1], ARGV[2], ARGV[1])
    redis.call('XDEL', KEYS[1], ARGV[1])
    return {0, retry_count}  -- 超限进死信
end
redis.call('XACK', KEYS[1], ARGV[2], ARGV[1])
redis.call('XDEL', KEYS[1], ARGV[1])
fields['retry_count'] = tostring(retry_count)
-- unpack(fields) 重新入队
local nf = {}
for k, v in pairs(fields) do nf[#nf + 1] = k; nf[#nf + 1] = v end
redis.call('XADD', KEYS[1], 'MAXLEN', '~', tonumber(ARGV[6]), '*', unpack(nf))
return {1, retry_count}
```

> **双 Stream ACK 路由**：`_message_stream` 字典记录每个 `message_id` 的来源 Stream
> （high/normal）。ACK/NACK/重试/死信升级均通过此映射路由到正确的 Stream，确保
> `high_stream` 的消息不会被错误 ACK 到 `stream`。

### 6.2 重试与死信

```
投递次数       动作
─────────────────────────────────
第1次 (retry=0)  → 正常处理
第2次 (retry=1)  → NACK(RETRY) → XRANGE 读字段 → XACK+XDEL → XADD (重新入队)
第3次 (retry=2)  → NACK(RETRY) → XRANGE 读字段 → XACK+XDEL → XADD (重新入队)
第4次 (retry=3)  → 超限 → XADD stream:failed (死信)
                      dead_fields: {original_message_id, dead_at, dead_reason, retry_count}
```

### 6.3 序列化策略

| 策略 | 配置 | 效果 |
|---|---|---|
| 紧凑序列化 | `STREAM_COMPACT=True` | 跳过 None/空容器/空字符串/默认值字段 |
| JSON 格式 | `STREAM_SERIALIZATION_FORMAT='json'` | redis-cli 可读，跨语言兼容 |

```
完整 fields (14):
  url, method, callback, meta, headers, cookies, body, encoding,
  priority, dont_filter, allow_redirects, verify, use_dynamic_loader, errback

紧凑后 fields (通常只存 ~5):
  url, callback, meta(非空), body(非空), encoding(非None)
```

---

## 7. 故障恢复

### 7.1 孤儿 Pending 回收 (启动时)

**场景**：上一轮所有 Worker 已退出，留下已读但未 ACK 的消息。

```python
RedisStreamQueue.connect()
  └─ _ensure_consumer_groups()    # 创建 Consumer Group
  └─ self._connected = True        # 必须先标记（claim_pending 需要）
  └─ _recover_orphan_pending()     # 回收孤儿消息
       ├─ 并发启动检查（防误回收）:
       │    └─ XINFO CONSUMERS 检查两个 Stream（high + normal）
       │        若存在 idle < 30s 的活跃 Consumer → 跳过回收
       │        （说明有其他 Worker 正在处理，不是孤儿场景）
       └─ 无活跃 Consumer → 执行回收:
            └─ XPENDING 查 pending 数量
            └─ 对两个 Stream（high + normal）分别:
                 while True:
                     claim_pending(min_idle_ms=1, count=100)
                     └─ XAUTOCLAIM / XPENDING+XCLAIM 原子 claim
                     └─ 逐条:
                          XRANGE 读原始字段
                          XACK + XDEL 原消息
                          XADD 重新入队 (retry_count+1)
                          超限 → XADD stream:failed (死信)
```

> **防误触发机制**：`_orphan_idle_threshold_ms` 可配置（默认 30000ms）。
> 并发启动时，各 Worker 的 Consumer 均在 Group 中且 idle 极短，检查会跳过回收，仅留待 Failover 机制处理。

### 7.2 Failover 任务回收 (运行时)

**场景**：某 Worker 心跳超时被判定为崩溃，其 pending 任务需回收。

```python
FailoverManager.check_and_recover()
  └─ detect_dead_workers(90s)
  └─ 两阶段检测:
       Phase 1: 首次发现 → 检查 status
            ├─ STATUS_STOPPING → 跳过（优雅退出中，不回收）
            └─ 其他 → mark suspect, suspect_since=now (不回收)
       Phase 2: suspect > 30s → acquire lock → _claim_worker_tasks()
                                     └─ 回收两个 Stream 的 pending（high + normal）
                                     └─ 循环 claim_pending(min_idle=60s, count=100)
                                          └─ XRANGE → XACK+XDEL → XADD (retry+1, failover_from=worker_id)
                                     └─ deregister()
```

### 7.3 恢复对比

| 维度 | 孤儿回收 (`_recover_orphan_pending`) | Failover 回收 (`_claim_worker_tasks`) |
|---|---|---|
| 触发时机 | Worker 启动时 | 心跳超时 + 30s confirm |
| idle 阈值 | 1ms (立即) | 60s (consumer_idle_timeout) |
| Stream 范围 | high + normal 两个 Stream | high + normal 两个 Stream |
| 活跃检查 | XINFO CONSUMERS: idle < 30s → 跳过 | 两阶段检测 + STATUS_STOPPING 豁免 |
| 锁保护 | 无 (各 Worker 并发回收) | DistributedLock (互斥) |
| 互斥性 | XAUTOCLAIM 原子 claim | 同一任务只被一个 Worker claim |

---

## 8. 协调退出

### 8.1 Leader 选举

```
每个 Worker 运行 _leader_shutdown_loop()，仅 DYNAMIC_CONFIG_ENABLED=True 时启用：

1. _try_acquire_leader_lock(ttl=heartbeat_interval*2)
   └─ DistributedLock.acquire() → SET NX PX (原子获取 + 自动过期)
   └─ 已持有 → DistributedLock.extend() → Lua 原子续期（防误续他人锁）

2. 不是 Leader → sleep(10s)，重试

3. 是 Leader → 检查 control:state:
   └─ 若已是 "shutdown" → 其他 Leader 已触发，直接停止

4. 检查退出条件 _check_leader_shutdown_conditions():
   ├─ ✅ _start_requests_source 已耗尽
   ├─ ✅ 队列为空（两次检查，间隔 2s，防瞬态误判）
   ├─ ✅ 无在途后台任务
   └─ ✅ 所有注册 Worker 的 tasks_processing == 0（基于心跳数据）

5. 条件满足 → DynamicConfig.shutdown_cluster(cleanup=False):
   ├─ SET control:state = "shutdown"（持久化，保证断连 Worker 能感知）
   ├─ PUBLISH channel:control {action: "shutdown"}（即时通知）
   └─ cleanup=False：保留 control:state（值设为 "running" 而非删除）
       避免后续 Worker 获取 Leader 锁后重复触发 shutdown

6. self.running = False (Leader 自己也停止)
```

> **防重复触发**：Leader 广播前先检查 `control:state`，若已为 "shutdown" 则直接退出；
> `_cleanup_run_data` 将 `control:state` 重设为 "running" 而非删除，防止后续启动的 Worker
> 在 Leader 已退出后获取锁并误判需要重新广播。

### 8.2 退出时序

```
Leader 检测到完成条件
  │
  ├─ SET control:state = "shutdown"     ← 持久化（断连 Worker 恢复后可见）
  └─ PUBLISH channel:control "shutdown" ← 即时通知
       │
       ├─ Worker A 收到 Pub/Sub → _on_control_message → running=False
       ├─ Worker B 未收到 Pub/Sub → 启动时检查 Persistent shutdown → 退出
       └─ Worker C 中途崩溃 → 超时后 failover 检测到 → claim 其任务 → 重新入队

各 Worker 退出:
  _shutdown_cluster()
    ├─ 0. update_status(STOPPING)  ← 防止 failover 误回收
    ├─ 1~5. 停止 Messenger / Heartbeat / Failover / Leader (await 完成)
    ├─ 6. drain_inflight_tasks(timeout=30s)
    │       └─ 超时 → cancel + await gather 残留任务
    │       └─ 残留任务由下次启动的 _recover_orphan_pending 回收
    └─ 7. deregister()
```

---

## 9. 动态配置

### 9.1 控制命令

| 命令 | API | Redis 操作 | 效果 |
|---|---|---|---|
| 暂停 | `DynamicConfig.pause_spider()` | SET control:state=paused + PUBLISH pause | 所有 Worker 停止消费新任务 |
| 恢复 | `DynamicConfig.resume_spider()` | SET control:state=running + PUBLISH resume | 恢复消费 |
| 停止 | `DynamicConfig.shutdown_cluster()` | SET control:state=shutdown + PUBLISH shutdown | 所有 Worker 优雅退出 |

### 9.2 运行时配置

| 配置 | API | 持久化 Key |
|---|---|---|
| 域名限速 | `set_rate_limit(domain, rate, capacity)` | `config:rate_limits` (HASH) |
| 动态种子 URL | `add_seed_urls(urls)` | `config:seed_urls` (LIST) |
| 并发度调整 | `set_concurrency(worker_id, n)` | `config:concurrency` (HASH) |

---

## 10. 配置参考

### 10.1 核心配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `RUN_MODE` | `standalone` | 设为 `distributed` 激活集群 |
| `QUEUE_TYPE` | `auto` | 设为 `redis_stream` 使用 Stream 队列 |
| `CONCURRENCY` | `8` | 每 Worker 并发请求数 |
| `DOWNLOAD_DELAY` | `1.0` | 请求间隔（秒） |

> **环境依赖**：分布式模式依赖 **Redis 5.0+**（推荐 6.2+），详见
> [Redis 版本要求](#redis-版本要求)。

### 10.2 集群配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `CLUSTER_HEARTBEAT_INTERVAL` | `15` | 心跳间隔（秒） |
| `CLUSTER_WORKER_TIMEOUT` | `90` | Worker 超时（秒），超时后标记 suspect |
| `CLUSTER_FAILOVER_CHECK_INTERVAL` | `30` | Failover 检测间隔（秒） |
| `CLUSTER_FAILOVER_LOCK_TIMEOUT` | `30` | Failover 锁超时（秒） |
| `CLUSTER_GRACEFUL_SHUTDOWN_TIMEOUT` | `30` | 优雅退出 drain 超时（秒） |
| `CLUSTER_CLEANUP_ON_SHUTDOWN` | `True` | 退出时清理 control:state 和 leader lock |

### 10.3 Stream 配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `STREAM_MAX_LENGTH` | `100000` | Stream 最大长度（近似修剪） |
| `STREAM_CONSUMER_IDLE_TIMEOUT` | `60000` | ms，消息超时未 ACK 可被回收 |
| `STREAM_DELIVERY_COUNT_LIMIT` | `3` | 最大投递次数（超限进死信） |
| `STREAM_BLOCK_TIMEOUT` | `5000` | ms，XREADGROUP 阻塞超时 |
| `STREAM_SERIALIZATION_FORMAT` | `json` | Stream 消息序列化格式 |
| `STREAM_COMPACT` | `True` | 跳过默认值字段，节省内存 |
| `STREAM_PRIORITY_ENABLED` | `True` | 启用双 Stream 优先级路由（False 降级为单 Stream） |

### 10.4 Worker 行为

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `DISTRIBUTED_WORKER_IDLE_TIMEOUT` | `120` | 连续空闲 N 秒后退出（0=永不退出） |
| `DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED` | `True` | 启用 Leader 协调退出 |
| `DISTRIBUTED_RATE_LIMIT_ENABLED` | `False` | 启用分布式限速 |
| `DYNAMIC_CONFIG_ENABLED` | `False` | 启用动态配置 |
| `PROGRESS_REPORT_INTERVAL` | `10` | 进度上报间隔（秒） |

---

## 附录 A：Worker 批量启动脚本

```python
# examples/ofweek_distributed/run_10_workers.py
WORKER_COUNT = 10
for i in range(WORKER_COUNT):
    subprocess.Popen([sys.executable, 'run.py'], env=env)
    time.sleep(2)  # 间隔 2s 启动，防止心跳风暴
```

## 附录 B：监控命令

```bash
# Worker 状态
redis-cli HGETALL crawlo:{project}:{spider}:registry:workers

# Stream 长度（包含高优 + 普通）
redis-cli XLEN crawlo:{project}:{spider}:stream:tasks
redis-cli XLEN crawlo:{project}:{spider}:stream:tasks:high

# Pending 消息
redis-cli XPENDING crawlo:{project}:{spider}:stream:tasks crawlo:{project}:{spider}:group:workers
redis-cli XPENDING crawlo:{project}:{spider}:stream:tasks:high crawlo:{project}:{spider}:group:workers

# Consumer Group 信息（含活跃消费者）
redis-cli XINFO GROUPS crawlo:{project}:{spider}:stream:tasks
redis-cli XINFO CONSUMERS crawlo:{project}:{spider}:stream:tasks crawlo:{project}:{spider}:group:workers

# 去重集合大小
redis-cli SCARD crawlo:{project}:{spider}:dedup:request
redis-cli SCARD crawlo:{project}:{spider}:dedup:item

# 死信队列
redis-cli XLEN crawlo:{project}:{spider}:stream:failed

# 控制状态
redis-cli GET crawlo:{project}:{spider}:control:state

# Leader 锁持有者
redis-cli GET crawlo:{project}:{spider}:lock:leader

# 种子生成器
redis-cli GET crawlo:{project}:{spider}:seed:generator

# 集群总览（一行命令）
echo "=== Workers ===" && redis-cli HLEN crawlo:{project}:{spider}:registry:workers && \
echo "=== Tasks ===" && redis-cli XLEN crawlo:{project}:{spider}:stream:tasks && \
echo "=== Control ===" && redis-cli GET crawlo:{project}:{spider}:control:state && \
echo "=== Dead Letters ===" && redis-cli XLEN crawlo:{project}:{spider}:stream:failed
```

---

## 附录 C：Redis 高可用方案

分布式模式依赖 Redis 作为中心化存储，Redis 自身的可用性直接影响集群可用性。

### 主从复制（Master-Slave）

最简单的高可用方案。一个 Master 负责读写，一个或多个 Slave 同步数据。

```conf
# redis.conf (Master)
bind 0.0.0.0
port 6379

# redis.conf (Slave)
replicaof 10.0.0.1 6379
```

**局限**：Master 宕机需手动切换 Slave 为 Master，期间集群不可用。

### 哨兵模式（Sentinel）

Sentinel 监控 Master 状态，自动故障转移。

```conf
# sentinel.conf
sentinel monitor crawlo-master 10.0.0.1 6379 2
sentinel down-after-milliseconds crawlo-master 30000
sentinel failover-timeout crawlo-master 180000
```

**Crawlo 配置**：连接 Sentinel 而非直连 Redis：

```python
REDIS_URL = "redis+sentinel://10.0.0.1:26379,10.0.0.2:26379/0"
```

**故障转移行为**：
- Sentinel 检测到 Master 宕机 → 选举新 Master → 通知 Crawlo
- Crawlo 的 Redis 连接池自动重连新 Master
- 重连期间 PENDING 任务暂时无法 ACK，但不丢失（存在 Stream 中）
- 重连后 XAUTOCLAIM 会回收超时任务

### Redis Cluster

数据分片 + 自动故障转移，适合大规模部署。

> **注意**：当前分布式模式（RedisStreamQueue）已支持通过代码传入 Sentinel 参数。
> 完整的生产级 Sentinel 配置参见 [示例配置文件](../examples/ofweek_distributed/ofweek_distributed/settings.py)。

```python
# Sentinel 模式（代码层已支持）
from crawlo.queue.redis_stream_queue import RedisStreamQueue
queue = RedisStreamQueue(redis_url="", ...)
await queue.connect(sentinel_urls=[
    "redis://10.0.0.1:26379",
    "redis://10.0.0.2:26379",
])
```

**注意**：Redis Cluster 中 Stream 的 Key 必须在同一个 slot，Crawlo 使用 `{project}:{spider}` 作为 hash tag 确保 Stream、Registry、Filter 等 Key 落在同一节点。

### 推荐方案

| 规模 | 方案 | 理由 |
|------|------|------|
| < 5 Worker | 单 Redis | 够用，运维简单 |
| 5-20 Worker | 主从 + Sentinel | 自动故障转移 |
| > 20 Worker | Redis Cluster | 分片提升吞吐 |

---

## 附录 D：网络分区与脑裂处理

### 网络分区场景

当网络分区导致部分 Worker 无法连接 Redis 时：

```
          ┌─── Redis ───┐
          │             │
     ┌────┴────┐   ┌────┴────┐
     │ Worker A │   │ Worker B │
     │ (可达)    │   │ (不可达)  │
     └─────────┘   └─────────┘
        正常运行      心跳超时 → 被 Failover 标记为 suspect
```

### 脑裂风险

Crawlo 的分布式设计中，**不存在真正的脑裂问题**，因为：

1. **Redis 是唯一的真理来源**：所有状态（任务、心跳、锁、配置）都存储在 Redis 中。Worker 之间不直接通信，不持有独立状态。

2. **Leader 选举基于 Redis SETNX**：分区后的 Worker 无法执行 `SETNX`，不会产生两个 Leader。

3. **任务消费基于 Consumer Groups**：即使分区导致 Worker B 无法 ACK，其 PENDING 任务会被 XAUTOCLAIM 回收并重新分配给可达的 Worker A。不会出现同一任务被两个 Worker 同时处理的情况。

### 分区恢复后

Worker B 网络恢复后：

1. 重新连接 Redis
2. 发现心跳已超时 → 自己已被标记为 dead
3. **不会**继续处理旧任务（已被 XCLAIM 走）
4. 重新注册为新 Worker，从 Stream 消费新任务

### 风险点

| 场景 | 风险 | 缓解措施 |
|------|------|---------|
| Worker B 分区时正在处理任务 | 任务被 XCLAIM 后重复执行 | Pipeline 层做幂等处理（RedisDedupPipeline） |
| 分区期间 Leader 不可达 | 无法协调退出 | 等待分区恢复，或手动 `redis-cli SET control:state shutdown` |
| Redis 自身分区 | 全集群暂停 | Sentinel 自动故障转移 |

---

## 附录 E：大规模性能基准

### 10 Worker 测试（1800 页深爬）

| 指标 | 数值 |
|------|------|
| Worker 数 | 10 |
| 总请求数 | ~36,000 |
| 总耗时 | 22.6 分钟 |
| 单 Worker 速度 | ~160 pages/min |
| 成功率 | 99.99% |
| 错误数 | 2（ConnectTimeout，网络波动） |
| 数据丢失 | 0 |
| 死信数 | 0 |

### 扩展性分析

| Worker 数 | 理论加速比 | 实际加速比 | 协调开销 |
|-----------|-----------|-----------|---------|
| 1 | 1x | 1x | 0% |
| 5 | 5x | 4.7x | ~6% |
| 10 | 10x | 9.2x | ~8% |
| 20 | 20x | 17.5x（预估） | ~12% |
| 50 | 50x | 38x（预估） | ~24% |

**结论**：10 Worker 以内扩展性接近线性，20+ Worker 时 Redis 单点成为瓶颈，建议使用 Redis Cluster 或 Redis Sentinel 分片。

### Redis 资源消耗（10 Worker 基准）

| 指标 | 数值 |
|------|------|
| Redis 内存 | ~50 MB |
| Stream 长度 | ~36,000 条（峰值） |
| 每秒操作数 | ~800 ops/s |
| 网络带宽 | ~2 Mbps |

---

## 附录 F：Docker Compose 部署方案

### 单 Redis + N Worker

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy noeviction
    restart: unless-stopped

  worker:
    build: .
    depends_on:
      - redis
    environment:
      - CRAWLO_MODE=distributed
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    command: crawlo run my_spider
    deploy:
      replicas: 5
    restart: unless-stopped

volumes:
  redis-data:
```

### Redis Sentinel 高可用

```yaml
version: "3.8"

services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    restart: unless-stopped

  redis-slave:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379
    depends_on:
      - redis-master
    restart: unless-stopped

  sentinel:
    image: redis:7-alpine
    command: >
      sh -c 'echo "sentinel monitor mymaster redis-master 6379 2" > /etc/sentinel.conf &&
             echo "sentinel down-after-milliseconds mymaster 30000" >> /etc/sentinel.conf &&
             redis-server /etc/sentinel.conf --sentinel'
    depends_on:
      - redis-master
    restart: unless-stopped

  worker:
    build: .
    depends_on:
      - sentinel
    environment:
      - CRAWLO_MODE=distributed
      - REDIS_URL=redis+sentinel://sentinel:26379/0
    command: crawlo run my_spider
    deploy:
      replicas: 10
    restart: unless-stopped
```

### 使用方法

```bash
# 启动集群
docker-compose up -d

# 动态扩容
docker-compose up -d --scale worker=20

# 查看日志
docker-compose logs -f worker

# 停止集群
docker-compose down
```

---

## 附录 G：Prometheus + Grafana 监控集成

### Prometheus 指标采集

Crawlo 的 Redis Key 可以通过 `redis_exporter` 采集为 Prometheus 指标：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "redis"
    static_configs:
      - targets: ["redis:9121"]

  - job_name: "crawlo-workers"
    static_configs:
      - targets: ["worker:9090"]  # 需在 Worker 中启动 metrics server
```

### 关键监控指标

| 指标 | Redis 命令 | 告警阈值 |
|------|-----------|---------|
| 活跃 Worker 数 | `HLEN registry:workers` | < 预期数量 |
| 待处理任务数 | `XLEN stream:tasks` | 持续增长 |
| PENDING 任务数 | `XPENDING stream:tasks` | > 100 |
| 死信队列长度 | `XLEN stream:failed` | > 0 |
| 去重集合大小 | `SCARD dedup:request` | 持续增长 |
| Leader 状态 | `GET lock:leader` | 空值 |
| 控制状态 | `GET control:state` | = "shutdown" |

### Grafana Dashboard

推荐的 Grafana Panel 布局：

1. **集群概览**：Worker 数量、任务总量、处理速度
2. **任务状态**：Stream 长度、PENDING 数、死信数
3. **Worker 健康**：各 Worker 心跳时间、处理量
4. **去重统计**：去重命中率、集合增长曲线
5. **告警面板**：活跃告警列表

---

## 附录 H：多 Spider 资源隔离

### 资源隔离机制

Crawlo 的 Redis Key 以 `{project}:{spider}` 为前缀，天然实现了 Spider 级别的资源隔离：

```
crawlo:myproject:spider_a:stream:tasks    ← Spider A 的任务
crawlo:myproject:spider_b:stream:tasks    ← Spider B 的任务
crawlo:myproject:spider_a:dedup:request   ← Spider A 的去重
crawlo:myproject:spider_b:dedup:request   ← Spider B 的去重
```

### 并行调度

`SchedulerDaemon` 支持多 Spider 并行运行，通过 `asyncio.Semaphore` 控制最大并发 Spider 数（默认 3）：

```python
SCHEDULER_JOBS = [
    {"spider": "news_163", "cron": "0 8 * * *"},
    {"spider": "news_sina", "cron": "0 8 * * *"},
    {"spider": "news_baidu", "cron": "0 8 * * *"},
]
SCHEDULER_MAX_CONCURRENT = 3  # 最多同时运行 3 个 Spider
```

### 资源竞争

多个 Spider 共享同一个 Redis 实例时，可能产生资源竞争。缓解策略：

| 策略 | 说明 |
|------|------|
| 分离 Redis 实例 | 高负载 Spider 使用独立 Redis |
| Redis Cluster 分片 | 利用 hash tag 将不同 Spider 路由到不同节点 |
| 限速配置 | 每个 Spider 独立配置 `CONCURRENCY` 和 `DOWNLOAD_DELAY` |
| 错峰调度 | 通过 Cron 表达式错开高峰 |

