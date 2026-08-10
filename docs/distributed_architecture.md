# Crawlo 分布式架构设计文档

---

## 目录

- [1. 架构概览](#1-架构概览)
- [2. 任务生命周期](#2-任务生命周期)
- [3. 协调退出](#3-协调退出)
- [4. 动态配置](#4-动态配置)
- [5. 配置参考](#5-配置参考)
---


## 1. 架构概览

### 设计原则

Crawlo 分布式系统采用 **无中心 Leader + Redis 中心化存储**架构。

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
| **最低版本**| **Redis 5.0+**| Stream 基础功能（XADD / XREADGROUP / XACK / XCLAIM） |
| **推荐版本**| **Redis 6.2+**| XAUTOCLAIM 一步完成 orphan 回收，效率更高 |
| **部署推荐**| **Redis 7+**| 生产环境推荐使用最新稳定版（`redis:7-alpine`） |
| **最高版本**| **无上限**| 向下兼容，无最大版本限制 |

**自动降级策略**：框架启动时通过 `crawlo.utils.redis.stream_utils` 检测 Redis 版本：
- `supports_xstream()` → 检查 `major >= 5`，不满足则**无法使用分布式模式**- `supports_xautoclaim()` → 检查 `major > 6 or (major == 6 and minor >= 2)`
  - ✅ 6.2+：使用 XAUTOCLAIM（原子 claim + 自动清理已删除消息）
  - ⚠️ 5.0-6.1：降级为 XPENDING + XCLAIM 手动两步回收（功能等价，多一次 Redis 往返）

> `crawlo/utils/redis/stream_utils.py` 中 `detect_redis_version()` 从 Redis INFO 命令
> 解析版本号，连接时自动检测并记录日志。

#### 各版本对分布式设计的影响

Crawlo 的分布式设计**不因 Redis 版本而改变架构思路**——始终基于 Stream + Consumer Groups + ACK。
不同版本的区别仅在于**故障回收的实现路径**和**性能开销**：

**Redis 5.0-6.1（最低可用）**Stream 在 5.0 引入，提供了 Crawlo 分布式所需的全部基础原语：
- `XADD`（入队）、`XREADGROUP`（消费）、`XACK`（确认）、`XCLAIM`（手动转移任务）
- `XPENDING`（查询 PENDING 列表）

但缺少 `XAUTOCLAIM` 命令（6.2 才引入）。Crawlo 在此版本下的故障回收路径为：

```
XPENDING（列出超时任务）→ 逐条 XCLAIM（转移所有权）→ XRANGE（读内容）
 → XACK + XDEL（清理原消息）→ XADD（重新入队，retry+1）
```

这是**三步手动回收**，每次回收一批任务需要多次 Redis 往返。功能上与 XAUTOCLAIM 完全等价，
但在高并发故障场景下（如同时崩溃多个 Worker），回收延迟略高（多 1-2 次 RTT）。

**Redis 6.2+（推荐）**引入了 `XAUTOCLAIM` 命令，将上述三步合并为一步原子操作：

```
XAUTOCLAIM（自动 claim 超时任务 + 返回任务内容）→ XACK + XDEL → XADD
```

Crawlo 在此版本下：
- 孤儿回收（启动时）：单次 `XAUTOCLAIM` 批量 claim，减少 Redis 往返
- Failover 回收（运行时）：持有 DistributedLock 后执行 `XAUTOCLAIM`，原子性更强
- 自动清理已删除的消息，避免 PENDING 列表膨胀

**Redis 7+（生产推荐）**7.0+ 在 Stream 性能和稳定性上有显著提升，但 Crawlo 的分布式设计思路不变：
- Stream 的 `MAXLEN` trimming 性能优化（`XADD ... MAXLEN ~ N` 近似修剪更高效）
- ACL（访问控制列表）支持更完善，适合多团队共享 Redis 的场景
- Sentinel 和 Cluster 的故障转移速度更快（对 Crawlo 透明，Crawlo 只需重连）

> **总结**：Redis 版本影响的是故障回收的效率，不是架构设计。Crawlo 在 5.0 上就能
> 完整运行分布式模式，6.2+ 只是让故障回收更快更简洁。

### 架构全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Redis (7.2+) │
│ ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│ │ Stream Queue │ │ Worker │ │ Config & Control │ │
│ │ ─ tasks (normal)│ │ Registry │ │ ─ rate_limits (HASH) │ │
│ │ ─ tasks:high │ │ ─ workers HASH │ │ ─ seed_urls (LIST) │ │
│ │ ─ failed (DLQ) │ │ ─ heartbeats │ │ ─ control:state (STR) │ │
│ │ ─ Consumer Group│ │ ZSET │ │ ─ Pub/Sub 2 channels │ │
│ └─────────────────┘ └──────────────────┘ └──────────────────────────┘ │
│ ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│ │ Dedup Sets │ │ Progress │ │ Locks │ │
│ │ ─ dedup:request │ │ Aggregator │ │ ─ lock:leader (选举) │ │
│ │ ─ dedup:item │ │ ─ stats HASH │ │ ─ lock:failover (互斥) │ │
│ └─────────────────┘ └──────────────────┘ └──────────────────────────┘ │
│ ┌──────────────────┐ ┌──────────────────────────────────────────────┐ │
│ │ Seed Generator │ │ DistributedRateLimiter (Lua Token Bucket) │ │
│ │ ─ SETNX 互斥 │ └──────────────────────────────────────────────┘ │
│ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
 ▲ ▲
 │ XREADGROUP / XACK │ Heartbeat / Failover
 │ Pub/Sub │ Progress Report
 │ │
 ┌──────┴──────┐ ┌───────┴───────┐
 │ Worker #1 │ ... │ Worker #N │
 │ ─ Engine │ │ ─ Engine │
 │ ─ Spiders │ │ ─ Spiders │
 │ ─ Heartbeat│ │ ─ Heartbeat │
 │ ─ Failover │ │ ─ Failover │
 └─────────────┘ └───────────────┘
```

### 核心特性

| 特性 | 说明 |
|---|---|
| **无中心 Leader**| 所有 Worker 对等，平等竞争任务；仅在协调退出时自选举临时 Leader |
| **双 Stream 优先级**| 高优 `stream:tasks:high` + 普通 `stream:tasks`，支持 `STREAM_PRIORITY_ENABLED` 开关 |
| **Consumer Group + ACK**| XREADGROUP 消费 + XACK 确认，崩溃任务自动回收 |
| **种子去重**| Worker 通过 SETNX 互斥选举唯一的种子 URL 生成器 |
| **两阶段故障检测**| suspect 标记 → 30s 二次确认 → XAUTOCLAIM 回收 |
| **优雅协调退出**| Leader 检测全部空闲 → 广播 shutdown → 所有 Worker drain 后退出 |
| **动态扩缩容**| 新 Worker 即插即用，崩溃 Worker 任务 120s 内自动回收，不丢数据 |
| **持久化控制状态**| 双通道 (Pub/Sub + Redis Key) 保证退出信号不丢失 |

---


## 2. 任务生命周期

每个爬取请求在分布式系统中的完整生命周期：

```
 Worker A Worker B
 
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
 │ │
 新 URL │ │ 已存在
 ▼ ▼
 QueueManager.put() 丢弃 (日志: Filtered duplicate)
 │
 ▼
 RedisStreamQueue.put()
 ┌─ priority < 0 → XADD stream:tasks:high
 └─ priority ≥ 0 → XADD stream:tasks
                    * data priority retry_count enqueued_at
 │
 ┌───────────────┴────────────────┐
 │ │
 ▼ ▼
 XREADGROUP stream > XREADGROUP stream >
 (_read: 先非阻塞 high, (_read: 先非阻塞 high,
 后阻塞 normal) 后阻塞 normal)
 │ │
 ▼ ▼
 _parse_message() _parse_message()
 注入 meta: 注入 meta:
 __stream_message_id __stream_message_id
 __stream_retry_count __stream_retry_count
 __stream (stream key) __stream (stream key)
 记录映射: 记录映射:
 _message_stream[id]=stream _message_stream[id]=stream
 │ │
 ▼ ▼
 Engine._crawl() Engine._crawl()
 ├─ Downloader.fetch() ├─ Downloader.fetch()
 ├─ Spider callback ├─ Spider callback
 ├─ Pipeline ├─ Pipeline
 └─ _ack_message(success=True) └─ _ack_message(success=False)
 │ │
 ▼ ▼
 scheduler.ack_request() scheduler.nack_request()
 ├─ _get_message_stream(id) ├─ classify error → RETRY/DEAD
 │ → 查 _message_stream 映射 ├─ _get_message_stream(id)
 │ → 路由到正确的 Stream │ → 路由到正确的 Stream
 ├─ XACK (从 pending 移除) ├─ XRANGE (读原始字段)
 └─ XDEL (物理删除消息) ├─ XACK + XDEL
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


## 3. 协调退出

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
 ├─ _start_requests_source 已耗尽 ├─ 队列为空（两次检查，间隔 2s，防瞬态误判） ├─ 无在途后台任务 └─ 所有注册 Worker 的 tasks_processing == 0（基于心跳数据） 
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
 ├─ SET control:state = "shutdown" ← 持久化（断连 Worker 恢复后可见）
 └─ PUBLISH channel:control "shutdown" ← 即时通知
 │
 ├─ Worker A 收到 Pub/Sub → _on_control_message → running=False
 ├─ Worker B 未收到 Pub/Sub → 启动时检查 Persistent shutdown → 退出
 └─ Worker C 中途崩溃 → 超时后 failover 检测到 → claim 其任务 → 重新入队

各 Worker 退出:
 _shutdown_cluster()
 ├─ 0. update_status(STOPPING) ← 防止 failover 误回收
 ├─ 1~5. 停止 Messenger / Heartbeat / Failover / Leader (await 完成)
 ├─ 6. drain_inflight_tasks(timeout=30s)
 │ └─ 超时 → cancel + await gather 残留任务
 │ └─ 残留任务由下次启动的 _recover_orphan_pending 回收
 └─ 7. deregister()
```

---


## 4. 动态配置

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


## 5. 配置参考

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

