# Crawlo 分布式架构

Crawlo 支持三种运行模式，覆盖从单机调试到生产级大规模分布式爬取的全场景需求。

| 模式 | 队列 | 去重 | 协调机制 | 适用场景 |
|------|------|------|---------|---------|
| **内存模式** | in-memory PriorityQueue | 内存 | 无（单进程） | 开发调试、快速验证、小规模单机 |
| **多节点协作** | Redis ZSET / Stream | Redis SET | 竞争消费（BZPOPMIN） | 多机并发，能接受任务丢失 |
| **分布式系统** | Redis Stream + CG | Redis SET | ACK + 心跳 + 故障转移 | 生产环境，任务可靠性要求高 |

---

## 一、内存模式

### 1.1 概述

内存模式是 Crawlo 的默认运行方式，所有数据存储在进程内存中，不依赖外部服务。

- 运行模式：`RUN_MODE='standalone'`
- 队列类型：`QUEUE_TYPE='memory'`（`auto` 模式在无 Redis 时的回退）

### 1.2 架构

```
┌─────────────────────────────────────┐
│             Crawlo 进程              │
│                                      │
│  Spider ─► Scheduler ─► Engine ─► Downloader
│              │                          │
│              ▼                          ▼
│    SpiderPriorityQueue           HTTP 请求
│   (asyncio.PriorityQueue)             │
│              │                          ▼
│              └───────► Processor ◄────┘
│                            │
│                            ▼
│                       Pipeline
│                    (内存去重 + 输出)
└─────────────────────────────────────┘
```

### 1.3 关键组件

| 组件 | 文件 | 说明 |
|------|------|------|
| `SpiderPriorityQueue` | `crawlo/queue/memory_queue.py` | 基于 `asyncio.PriorityQueue`，优先级数值越小越优先 |
| `MemoryFilter` | `crawlo/filters/memory_filter.py` | 基于 `set()` 的本地请求去重 |
| `MemoryDedupPipeline` | `crawlo/pipelines/dedup/memory_dedup.py` | 基于 `set()` 的数据项去重 |

### 1.4 优先级模型

所有请求根据优先级 `priority` 入队，数值越小越优先出队：

```python
class QueuePriority(Enum):
    CRITICAL = 100     # 种子 URL、重试请求
    HIGH = 75          # 重要列表页
    NORMAL = 50        # 普通详情页
    LOW = 25           # 低优先级链接
    BACKGROUND = 0     # 后台任务（最低优先级，数值小是因为 PriorityQueue 的排序规则）
```

实际出队使用 `heapq` 堆排序，`PriorityQueue` 天然支持 N 级连续优先级。

### 1.5 退出条件

- 队列为空 + 所有组件（下载器、处理器、调度器）空闲
- 默认情况下任务全部完成后自动退出

### 1.6 局限性

| 缺陷 | 影响 |
|------|------|
| 单进程，无法利用多机资源 | 吞吐量受单机限制 |
| 进程重启后所有状态丢失 | 无法断点续爬（除非启用检查点） |
| 队列内存占用与请求量成正比 | 大规模爬取可能导致 OOM |

---

## 二、多节点协作模式

### 2.1 概述

多节点协作是 Crawlo 当前的**中间方案**，通过共享 Redis 实现多个 Worker 并行爬取，
但缺乏 ACK 确认和故障转移机制。Worker 之间通过"竞争消费"协作，无直接通信。

- 运行模式：`RUN_MODE='standalone'`（队列类型选 Redis 即可）或 `RUN_MODE='distributed'`
- 队列类型：`QUEUE_TYPE='redis'`（ZSET）或 `QUEUE_TYPE='redis_stream'`（Stream）

### 2.2 架构

```
┌────────────────────────────────────────────────────────┐
│                     Redis                              │
│                                                        │
│  ┌──────────────────────┐  ┌────────────────────────┐ │
│  │  ZSET queue:requests  │  │  SET filter:fingerprint │ │
│  │  HASH queue:data      │  │  SET item:fingerprint   │ │
│  └──────────────────────┘  └────────────────────────┘ │
└────────────────────────────────────────────────────────┘
          ▲ 竞争消费 (BZPOPMIN)       ▲ 共享去重 (SISMEMBER)
          │                            │
    ┌─────┴─────┐            ┌──────┴──────┐
    │ Worker 1  │    ...     │  Worker N   │
    │ (BZPOPMIN)│            │ (BZPOPMIN)  │
    └───────────┘            └─────────────┘
```

### 2.3 关键组件

| 组件 | 文件 | 说明 |
|------|------|------|
| `RedisPriorityQueue` | `crawlo/queue/redis_priority_queue.py` | ZSET + HASH，`BZPOPMIN` 阻塞出队 |
| `RedisStreamQueue` | `crawlo/queue/redis_stream_queue.py` | Stream + Consumer Group，XREADGROUP 出队 |
| `AioRedisFilter` | `crawlo/filters/aioredis_filter.py` | Redis SET + SISMEMBER 请求去重 |
| `RedisDedupPipeline` | `crawlo/pipelines/dedup/redis_dedup.py` | Redis SET 数据项去重 |

### 2.4 优先级模型

与内存模式一致的连续优先级口径：

| 队列类型 | 实现方式 | 出队语义 |
|----------|---------|---------|
| Redis ZSET | `ZADD score=priority` | `BZPOPMIN`（score 最小先出） |
| Redis Stream | `XADD` 携带 `priority` 字段 | FIFO（先入先出，priority 作为消��字段保留） |

两种队列的 priority 数值含义相同（越小越优先），与内存队列口径一致。

### 2.5 工作原理

**种子 URL 入队**：
- 第一个启动的 Worker 调用 `start_requests()` 生成种子 URL 并入队
- 后续 Worker 中也运行 `start_requests()`，但去重过滤器（Redis SET）确保相同 URL 只入队一次

**任务消费**：
- 所有 Worker 通过 `BZPOPMIN` / `XREADGROUP` 从共享队列中竞争获取任务
- 谁先抢到谁处理，天然负载均衡

**Worker 退出**（分布式模式）：
- Leader Worker 协调退出：当队列空 + 所有 Worker 空闲时，Leader 广播 shutdown
- 兜底：300s 空闲超时后自动退出（`DISTRIBUTED_WORKER_IDLE_TIMEOUT`）
- 参见：[Leader 协调退出](#%E5%9B%9B%E5%88%86%E5%B8%83%E5%BC%8F%E7%B3%BB%E7%BB%9F%E6%A8%A1%E5%BC%8F)

### 2.6 局限性

| 缺陷 | 影响 | 严重度 |
|------|------|--------|
| 无 ACK 机制 | Worker 崩溃后已出队的任务丢失，无法重分配 | 🔴 |
| 无节点注册/心跳 | 无法感知在线节点，无法做负载均衡 | 🔴 |
| 无任务状态流转 | 出队即视为"处理中"，无 processing/完成/失败状态 | 🔴 |
| 无故障转移 | 节点崩溃后其任务永久丢失 | 🔴 |
| 无进度聚合 | 无法查询全局爬取进度 | 🟡 |
| 无分布式锁 | 多节点可能重复初始化/清理 | 🟡 |
| 无节点间通信 | 无法协调速率限制、暂停/恢复等操作 | 🟡 |

---

## 三、分布式系统模式

### 3.1 概述

分布式系统模式是 Crawlo 的目标架构，基于 **Redis Streams + Consumer Groups** 构建，
提供 ACK 确认、故障转移、心跳检测、进度聚合、动态配置等生产级能力。

- 运行模式：`RUN_MODE='distributed'`
- 队列类型：`QUEUE_TYPE='redis_stream'`

### 3.2 架构

```
┌────────────────────────────────────────────────────────────────┐
│                         Redis Cluster                          │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Streams     │  │   Registry   │  │   Locks      │        │
│  │  (任务队列)    │  │  (节点注册)   │  │ (分布式锁)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Filters    │  │   Progress   │  │   Config     │        │
│  │  (去重SET)    │  │  (进度聚合)   │  │ (动态配置)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
         ▲              ▲              ▲
         │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ Worker1 │    │ Worker2 │    │ Worker3 │
    │(Consumer)│   │(Consumer)│   │(Consumer)│
    └─────────┘    └─────────┘    └─────────┘
```

### 3.3 节点角色

| 角色 | 职责 | 数量 |
|------|------|------|
| **Worker** | 从 Stream 消费请求、执行爬取、XACK 完成 | 1~N |
| **Coordinator** | 节点注册、心跳检测、故障转移、进度聚合 | 嵌入每个 Worker（去中心化） |

> 不采用 Master/Worker 分离模式，避免单点故障。
> 每个 Worker 内嵌 Coordinator 逻辑，通过 Redis 原子操作实现协调。

### 3.4 任务状态流转

```
                  XADD
  [新请求] ──────────────► PENDING (Stream 中等待消费)
                              │
                    XREADGROUP │ (分配给 Consumer)
                              ▼
                          PROCESSING (Consumer 持有，有 lease)
                         ╱          ╲
                   XACK ╱            ╲ 超时/崩溃
                       ▼              ▼
                    DONE          XCLAIM/XAUTOCLAIM
                   (完成)           转移给其他 Consumer
                                      │
                                      ▼
                                  PROCESSING (新 Consumer)
                                 ╱          ╲
                           XACK ╱            ╲ 重试次数耗尽
                               ▼              ▼
                            DONE          FAILED QUEUE
                           (完成)         (死信队列)
```

### 3.5 关键组件

#### 3.5.1 队列层

**Redis Streams + Consumer Groups**

```python
# crawlo/queue/redis_stream_queue.py
class RedisStreamQueue:
    put(request)       # XADD 入队
    get_blocking()     # XREADGROUP 阻塞消费
    ack(message_id)    # XACK 确认完成
    nack(message_id)   # NACK → 重试或死信
    pending_info()     # XPENDING 查询未确认
    claim_pending()    # XCLAIM 回收超时任务
```

**Redis Key**（单 Stream）：

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:stream:tasks` | Stream | 统一任务队列 |
| `crawlo:{project}:{spider}:stream:failed` | Stream | 死信队列 |
| `crawlo:{project}:{spider}:group:workers` | Consumer Group | Worker 消费组 |

> **优先级设计**：与内存/多节点协作模式口径一致，`priority` 作为消息字段保留，
> 出队采用 FIFO 语义。种子 URL 先入队自然先被消费，无需双 Stream。

#### 3.5.2 节点注册与心跳

```python
# crawlo/cluster/registry.py
class WorkerRegistry:
    register(worker_info) → worker_id   # HSET + ZADD
    heartbeat(worker_id)                # ZADD 更新时间戳
    deregister(worker_id)               # HDEL + ZREM
    get_active_workers()                # ZRANGEBYSCORE
    detect_dead_workers(timeout)        # 心跳超时检测

# crawlo/cluster/heartbeat.py
class HeartbeatDaemon:
    start(interval=15)                  # 周期性发送心跳
    stop()                              # 停止心跳
```

**Redis Key**：

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:registry:workers` | HASH | Worker 注册表 |
| `crawlo:{project}:{spider}:registry:heartbeats` | ZSET | Worker 心跳（score=时间戳） |

**Worker 注册表结构**：
```json
{
  "id": "worker-abc123",
  "host": "192.168.1.10",
  "pid": 12345,
  "status": "running",         // running / idle / suspect / stopping
  "tasks_completed": 1000,
  "tasks_processing": 5
}
```

#### 3.5.3 故障转移

```python
# crawlo/cluster/failover.py
class FailoverManager:
    check_and_recover()                  # 检测崩溃 Worker → 回收任务
    claim_worker_tasks(worker_id)        # XPENDING + XCLAIM 回收
    handle_orphaned_tasks()              # 清理孤儿 Consumer
    escalate_to_dead_letter(msg_id)      # 投递超限 → 死信
```

**安全机制**（二次确认防误判）：
```
检测到心跳超时 → 标记 suspect（30s 观察期）
                → 二次确认仍超时 → 正式回收任务
                → 网络抖动恢复 → 移除 suspect 标记，继续工作
```

**Redis 版本适配**：
- 6.2+：`XAUTOCLAIM` 一步完成筛选+转移
- 5.0~6.1：`XPENDING` + `XCLAIM` 手动 fallback

#### 3.5.4 分布式锁

```python
# crawlo/cluster/lock.py
class DistributedLock:
    acquire(name, timeout=30)     # SET NX PX
    release(name)                # Lua 原子防误删
    extend(name, additional=10)  # 续期
```

| Key | 用途 |
|-----|------|
| `crawlo:{project}:{spider}:lock:failover` | 故障检测锁（避免多节点同时检测） |
| `crawlo:{project}:{spider}:lock:init` | 爬虫初始化锁 |

#### 3.5.5 进度聚合

```python
# crawlo/cluster/progress.py
class ProgressAggregator:
    report(worker_id, stats)     # HSET 上报进度
    get_global_stats()           # HGETALL 全局统计
    estimate_completion()        # 预估完成时间
```

#### 3.5.6 分布式限流

```python
# crawlo/cluster/rate_limiter.py
class DistributedRateLimiter:
    acquire(domain, rate, capacity)      # Lua 令牌桶
    wait_and_acquire(domain, rate)       # 阻塞等待令牌
```

> **核心价值**：多 Worker 即使分布在多台机器，对同一域名的总请求速率仍受控。
> 3 个 Worker 限速 1 req/s → 总计仍为 1 req/s，而非 3 req/s。

**Lua 令牌桶脚本**：
```lua
local tokens = tonumber(redis.call('GET', KEYS[1])) or tonumber(ARGV[2])
local last_ts = tonumber(redis.call('GET', KEYS[2])) or tonumber(ARGV[3])
local elapsed = tonumber(ARGV[3]) - last_ts
tokens = math.min(tonumber(ARGV[2]), tokens + elapsed * tonumber(ARGV[1]))
if tokens >= 1 then
    redis.call('SET', KEYS[1], tokens - 1)
    redis.call('SET', KEYS[2], ARGV[3])
    return 1     -- 允许
else
    redis.call('SET', KEYS[1], tokens)
    return 0     -- 拒绝
end
```

**限流优先级链**：分布式限流 > Spider 级 `download_delay` > 单机 AutoThrottle

#### 3.5.7 动态配置与节点间通信

```python
# crawlo/cluster/config.py
class DynamicConfig:
    pause_spider()              # 暂停所有 Worker
    resume_spider()             # 恢复
    shutdown_cluster()          # 关闭所有 Worker
    set_rate_limit(domain, r)  # 动态调整限速

# crawlo/cluster/messaging.py
class ClusterMessenger:
    publish(channel, msg)       # Pub/Sub 即时通知
    subscribe(channel, cb)      # 订阅消息
    get_control_state()         # 持久化 Key 兜底读取
```

**双通道通知机制**：
1. **Pub/Sub**：即时通知所有在线 Worker（fire-and-forget）
2. **持久化 Key**：断连 Worker 重连后检查恢复（兜底）

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:control:state` | String | 控制状态（running/paused/shutdown） |
| `crawlo:{project}:{spider}:config:rate_limits` | HASH | 域名级速率覆盖 |
| `crawlo:{project}:{spider}:config:seed_urls` | LIST | 动态种子 URL |

#### 3.5.8 Leader 协调退出

分布式模式下，Worker 不再依赖固定的空闲超时退出，而是通过 Leader 选举自动协调：

```
Leader 选举 (SETNX + TTL 30s)
  └─ 唯一 Leader 每 10s 检查:
       ├─ 种子 URL 已全部生成完毕
       ├─ Stream 队列为空
       ├─ 所有 Worker 空闲 (tasks_processing == 0)
       └─ 2s 后重检（防瞬态误判）
           └─ 全部满足 → 广播 shutdown 信号 → 所有 Worker 优雅退出
```

Leader 崩溃后，锁 TTL 过期后自动重新选举。

### 3.6 分布式模式的 `crawl()` 主循环

```python
async def crawl(self):
    # 1. 注册 Worker
    worker_id = await registry.register(worker_info)

    # 2. 启动心跳
    heartbeat_task = create_task(heartbeat_loop())

    # 3. 启动故障检测（带分布式锁）
    failover_task = create_task(failover_loop())

    # 4. 启动 Pub/Sub 监听
    messenger_task = create_task(messaging_loop())

    # 5. 启动 Leader 协调退出循环
    if coordinated_shutdown_enabled:
        leader_task = create_task(leader_shutdown_loop())

    # 6. 主循环
    while running:
        request = await scheduler.next_request_blocking()
        if request is None:
            continue
        try:
            await process_request(request)
            await scheduler.ack_request(message_id)
        except Exception as e:
            result = classify_error(e)
            await scheduler.nack_request(message_id, result=result)

    # 7. 优雅关闭
    await graceful_shutdown()
```

### 3.7 优雅关闭

```
收到 shutdown 信号（Ctrl+C / Leader 广播 / Pub/Sub 控制消息）
  └─ running = False → 主循环退出
  └─ cancel 心跳 / 故障检测 / Leader / messenger 协程
  └─ drain 在途任务（最多 30s）
  └─ 注销 Worker（从注册表移除）
  └─ close 调度器 / 下载器 / pipeline
```

---

## 四、模式选择指南

```python
# settings.py

# ─── 内存模式（单机开发调试）───
RUN_MODE = 'standalone'
QUEUE_TYPE = 'memory'           # 或 'auto'（无 Redis 时自动回退内存）
# 无需配置 Redis

# ─── 多节点协作（多机并发，可接受任务丢失）───
RUN_MODE = 'standalone'         # 或 'distributed'
QUEUE_TYPE = 'redis'            # ZSET 方案
# 或
QUEUE_TYPE = 'redis_stream'     # Stream 方案（推荐）
REDIS_URL = 'redis://127.0.0.1:6379/0'

# ─── 分布式系统（生产环境，全功能）───
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis_stream'
REDIS_URL = 'redis://127.0.0.1:6379/0'

# 集群配置
CLUSTER_HEARTBEAT_INTERVAL = 15          # 心跳间隔
CLUSTER_WORKER_TIMEOUT = 90              # Worker 超时
CLUSTER_FAILOVER_CHECK_INTERVAL = 30     # 故障检测间隔
CLUSTER_GRACEFUL_SHUTDOWN_TIMEOUT = 30   # 优雅关闭超时

# 协调退出（默认开启）
DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED = True

# 可选功能
DISTRIBUTED_RATE_LIMIT_ENABLED = False
DYNAMIC_CONFIG_ENABLED = False
```

---

## 五、Redis Key 总览

| Key | 类型 | 模式 | 用途 |
|-----|------|------|------|
| `crawlo:{ns}:stream:tasks` | Stream | 多节点协作 / 分布式 | 任务队列 |
| `crawlo:{ns}:stream:failed` | Stream | 分布式 | 死信队列 |
| `crawlo:{ns}:group:workers` | CG | 分布式 | Consumer Group |
| `crawlo:{ns}:queue:requests` | ZSET+HASH | 多节点协作 | ZSET 请求队列 |
| `crawlo:{ns}:filter:fingerprint` | SET | 全部 | 请求去重 |
| `crawlo:{ns}:item:fingerprint` | SET | 全部 | 数据项去重 |
| `crawlo:{ns}:registry:workers` | HASH | 分布式 | Worker 注册表 |
| `crawlo:{ns}:registry:heartbeats` | ZSET | 分布式 | 心跳记录 |
| `crawlo:{ns}:lock:failover` | String+TTL | 分布式 | 故障检测锁 |
| `crawlo:{ns}:progress:stats` | HASH | 分布式 | 全局统计 |
| `crawlo:{ns}:config:rate_limits` | HASH | 分布式 | 限速配置 |
| `crawlo:{ns}:control:state` | String | 分布式 | 控制状态 |
| `crawlo:{ns}:cluster:leader` | String+TTL | 分布式 | Leader 锁 |

> `ns` = `{project}:{spider}`

---

## 六、兼容性策略

| 场景 | 策略 |
|------|------|
| 旧配置 `QUEUE_TYPE='redis'` | 继续使用 ZSET，不强制迁移 |
| `QUEUE_TYPE='auto'` | 有 Redis → 自动选 `redis_stream`；无 Redis → 回退 `memory` |
| `RUN_MODE='standalone'` + `QUEUE_TYPE='redis_stream'` | 使用 Stream 但不启动集群功能（不注册、不心跳） |
| Redis < 5.0 | 自动降级到 ZSET，打印警告 |
| Redis 5.0~6.1 | Stream 基础可用，XAUTOCLAIM 降级 XPENDING+XCLAIM |
| Redis 6.2+ | 全部功能可用 |

### 演进路线

```
内存模式（单机）──► 多节点协作（共享队列+共享去重）
                        │
                        ▼
                  分布式系统（ACK + 心跳 + 故障转移 + 监控）
```

---

## 七、配置项汇总

```python
# ===== 队列类型 =====
QUEUE_TYPE = 'auto'                         # memory | redis | redis_stream | auto
QUEUE_MAX_RETRIES = 3                       # 队列操作重试次数
QUEUE_SERIALIZATION_FORMAT = 'pickle'       # 序列化格式：pickle | json | msgpack

# ===== Stream 配置 =====
STREAM_MAX_LENGTH = 100000                  # Stream 最大长度（近似修剪）
STREAM_CONSUMER_IDLE_TIMEOUT = 60000        # ms，任务超时未 ACK 可被回收
STREAM_DELIVERY_COUNT_LIMIT = 3             # 最大投递次数（超过进死信）
STREAM_BLOCK_TIMEOUT = 5000                 # ms，XREADGROUP 阻塞超时

# ===== 分布式 Worker =====
DISTRIBUTED_WORKER_IDLE_TIMEOUT = 300       # 空闲超时（秒），0=永不退出
DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED = True  # Leader 协调退出

# ===== 集群配置 =====
CLUSTER_HEARTBEAT_INTERVAL = 15             # 心跳间隔（秒）
CLUSTER_WORKER_TIMEOUT = 90                 # Worker 超时（秒）
CLUSTER_AUTO_DEREGISTER = True              # 崩溃后自动注销
CLUSTER_FAILOVER_CHECK_INTERVAL = 30        # 故障检测间隔（秒）
CLUSTER_FAILOVER_LOCK_TIMEOUT = 30          # 故障检测锁超时（秒）
CLUSTER_GRACEFUL_SHUTDOWN_TIMEOUT = 30      # 优雅关闭超时（秒）

# ===== 分布式锁 =====
DISTRIBUTED_LOCK_TIMEOUT = 30               # 默认锁超时（秒）
DISTRIBUTED_LOCK_RETRY_COUNT = 3            # 获取锁重试次数
DISTRIBUTED_LOCK_RETRY_DELAY = 0.5          # 重试间隔（秒）

# ===== 进度聚合 =====
PROGRESS_REPORT_INTERVAL = 10               # 进度上报间隔（秒）

# ===== 分布式限流 =====
DISTRIBUTED_RATE_LIMIT_ENABLED = False      # 是否启用
DISTRIBUTED_RATE_LIMIT_DEFAULT_RATE = 0     # 默认速率（0=不限，单位：req/s）
DISTRIBUTED_RATE_LIMIT_CAPACITY = 10        # 令牌桶容量

# ===== 动态配置 =====
DYNAMIC_CONFIG_ENABLED = False              # 是否启用
```

---

## 八、新增文件清单

```
crawlo/
├── cluster/                      # 新建模块（分布式模式）
│   ├── __init__.py
│   ├── config.py                 # 动态配置
│   ├── failover.py               # 故障转移
│   ├── heartbeat.py              # 心跳守护
│   ├── lock.py                   # 分布式锁
│   ├── messaging.py              # 节点间消息通信
│   ├── monitor.py                # 集群监控
│   ├── progress.py               # 进度聚合
│   ├── rate_limiter.py           # 分布式限流
│   └── registry.py               # Worker 注册中心
├── queue/
│   ├── redis_stream_queue.py     # 新建：Redis Streams 队列
│   └── task_tracker.py           # 新建：任务生命周期追踪
└── utils/redis/
    └── stream_utils.py           # 新建：Stream 工具函数
```

---

## 九、测试计划

### 单元测试

| 模块 | 测试内容 | 优先级 |
|------|---------|--------|
| `RedisStreamQueue` | 入队/出队/ACK/NACK/claim/消费组竞态 | P0 |
| `WorkerRegistry` | 注册/心跳/注销/超时检测/suspect 状态 | P0 |
| `FailoverManager` | 崩溃检测/二次确认/任务回收/死信升级 | P0 |
| `DistributedRateLimiter` | 令牌桶/多节点速率聚合/Lua 原子性 | P0 |
| `DistributedLock` | 加锁/解锁/续期/防误删 | P1 |
| `ProgressAggregator` | 上报/聚合/预估 | P1 |
| `DynamicConfig` | 动态限速/暂停恢复/双通道通知 | P2 |

### 集成测试

| 场景 | 测试内容 | 优先级 |
|------|---------|--------|
| 双 Worker 竞争消费 | 同一 Stream，2 Worker，任务不重复 | P0 |
| Worker 崩溃恢复 | Worker1 处理中崩溃 → suspect → Worker2 回收 | P0 |
| 网络抖动误判 | Worker 短暂断连 → 不应触发回收 → 重连后继续 | P0 |
| 优雅关闭 | Worker 收到 SIGTERM → 完成当前任务 → 注销 | P0 |
| 分布式限流 | 3 Worker 限速总计 1 req/s | P0 |
| Leader 协调退出 | 队列空 + 所有 Worker 空闲 → 自动广播 shutdown | P0 |
| 3 Worker 弹性伸缩 | 动态启停 Worker，任务自动均衡 | P1 |
| 消费组重建 | 删除 Consumer Group 后重启自动重建 | P1 |
| Pub/Sub 断连恢复 | Worker 断连期间发布暂停 → 重连后检查 Key 感知 | P1 |

---

## 十、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Redis Streams 内存膨胀 | XTRIM 定期修剪 + MAXLEN 限制 + 监控告警 |
| 故障转移误判（网络抖动） | 心跳超时保守（90s）+ suspect 二次确认（30s）+ 去重过滤器兜底 |
| 分布式锁死锁 | 锁自动过期 + Lua 原子防误删 |
| 性能回归（Stream vs ZSET） | Phase 1 完成时基准测试，目标 < 5% 劣化 |
| 消息重复投递 | suspect 二次确认 + 去重过滤器 + 幂等设计 |
| 心跳风暴 | 随机化心跳间隔（±20% jitter） |
| Redis < 5.0 | 运行时检测 + 自动降级到 ZSET |
| Redis 5.0-6.1（无 XAUTOCLAIM） | XPENDING + XCLAIM 手动 fallback |
