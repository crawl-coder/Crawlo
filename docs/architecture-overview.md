# Crawlo 三种部署模式详解

> 从单机调试到千节点集群，一份文档讲透三种部署模式的设计差异。

---

## 目录

- [1. 设计哲学](#1-设计哲学)
- [2. 三种部署模式总览](#2-三种部署模式总览)
- [3. 单机模式（Standalone）](#3-单机模式standalone)
- [4. 多节点协作模式（Auto + Redis）](#4-多节点协作模式auto--redis)
- [5. 分布式系统模式（Distributed）](#5-分布式系统模式distributed)
- [6. 三种模式对比](#6-三种模式对比)
- [7. 模式切换：零代码改动](#7-模式切换零代码改动)
- [8. 共享引擎层](#8-共享引擎层)

---

## 1. 设计哲学

Crawlo 的核心设计原则只有一条：

> **同一份爬虫代码，能跑在单机上，也能跑在集群上。**

这意味着：

- 爬虫的 `parse()` 逻辑不需要关心自己跑在哪
- 队列、去重、调度等基础设施根据配置自动切换
- 从单机扩展到集群时，只需要改配置文件，不需要重构代码

为了实现这一点，Crawlo 将爬虫的执行分为两层：

```
┌─────────────────────────────────────────┐
│           业务层（不变）                  │
│  Spider.parse() / Item / Pipeline       │
├─────────────────────────────────────────┤
│           基础设施层（可切换）             │
│  Queue / Filter / Coordinator / Lock    │
└─────────────────────────────────────────┘
```

业务层写一次就够了。基础设施层根据 `RUN_MODE` 和 `QUEUE_TYPE` 的组合自动选择实现。

---

## 2. 三种部署模式总览

| 维度 | 单机模式 | 多节点协作 | 分布式系统 |
|------|---------|-----------|-----------|
| **配置** | `standalone` + `memory` | `auto` + `redis` | `distributed` + `redis_stream` |
| **队列** | 内存 PriorityQueue | Redis ZSET | Redis Streams + Consumer Groups |
| **去重** | 内存 Set | Redis SET | Redis SET |
| **任务确认** | 无需（进程内） | 无 ACK | XACK 确认 |
| **崩溃恢复** | 进程重启 → 从头开始 | 任务丢失 | XAUTOCLAIM 自动回收 |
| **节点协调** | 无 | 竞争消费 | Leader 选举 + 心跳 + 故障转移 |
| **外部依赖** | 无 | Redis | Redis 5.0+ |
| **适用场景** | 开发调试 | 多机分摊压力 | 生产环境 |
| **任务可靠性** | N/A | 最多一次 | 至少一次 |

---

## 3. 单机模式（Standalone）

### 设计目标

零外部依赖、零配置、即装即用。适合开发调试、快速验证和单机小规模采集。

### 架构图

```
┌──────────────────────────────────────────────┐
│                  单进程                        │
│                                               │
│  Spider → Scheduler(memory) → Engine          │
│               ↓                               │
│          Downloader(aiohttp)                   │
│               ↓                               │
│          Processor → Pipeline(MySQL/CSV/...)  │
│                                               │
│  去重：MemoryFilter (Python set)              │
│  队列：PriorityQueue (heapq)                   │
│  检查点：本地 JSON/SQLite 文件                  │
└──────────────────────────────────────────────┘
```

### 核心设计

**内存优先级队列**：基于 `asyncio.PriorityQueue` 实现，数值越小优先级越高。支持优先级分组（CRITICAL / HIGH / NORMAL / LOW / BACKGROUND），与分布式模式完全一致。

**内存去重**：`MemoryFilter` 使用 Python `set` 存储请求指纹（URL + method 的 SHA1），进程结束即释放。适合一次性采集，不适合需要跨运行去重的场景。

**退出条件**：当队列为空 **且** 所有组件空闲（无在途请求、无 Pipeline 写入）时，引擎自动退出。这是三种模式中唯一会自动退出的模式。

**检查点**：可选启用（`CHECKPOINT_ENABLED=True`），将请求队列序列化到本地文件（JSON 或 SQLite）。重启时 `resume=True` 自动恢复。

### 配置

```python
RUN_MODE = "standalone"
QUEUE_TYPE = "memory"
FILTER_CLASS = "crawlo.filters.MemoryFilter"
```

### 局限性

- 单进程，无法利用多机 IP 分散
- 进程崩溃后未完成的任务丢失（除非启用检查点）
- 去重集合随采集量线性增长，长时间运行可能占用大量内存

---

## 4. 多节点协作模式（Auto + Redis）

### 设计目标

多台机器分摊采集压力，共享去重，但不需要复杂的集群管理。适合可接受任务偶发丢失的场景。

### 架构图

```
        ┌──────────────────────────┐
        │        Redis              │
        │                          │
        │  ZSET (任务队列)           │
        │  SET  (全局去重)           │
        └──────────────────────────┘
             ▲            ▲
        BZPOPMIN      BZPOPMIN
             │            │
     ┌───────┴──┐   ┌─────┴────┐
     │ Worker 1 │   │ Worker N │
     │ (独立进程) │   │ (独立进程) │
     └──────────┘   └──────────┘
```

### 核心设计

**Redis ZSET 队列**：任务以 `member=序列化请求, score=优先级` 的形式存入 Redis Sorted Set（`RedisPriorityQueue` 类）。Worker 通过 `BZPOPMIN` 阻塞弹出最小 score 的任务，实现优先级消费。

**竞争消费**：多个 Worker 监听同一个 ZSET，谁先 `BZPOPMIN` 谁获得任务。没有任务分配器，纯竞争模式。

**全局去重**：`AioRedisFilter` 将请求指纹写入 Redis SET（`SADD`），所有 Worker 共享同一个去重集合。同一个 URL 只会被采集一次。

**无 ACK**：任务一旦从 ZSET 弹出，就不再属于队列。如果 Worker 在处理过程中崩溃，这个任务就丢失了——没有 PENDING 列表、没有重试机制。

**无心跳**：Worker 之间不知道彼此的存在。没有注册、没有心跳检测、没有故障转移。一个 Worker 崩溃了，其他 Worker 不会感知到。

### 配置

```python
RUN_MODE = "auto"
QUEUE_TYPE = "redis"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
```

### 适用场景

- 同一个爬虫需要在多台机器上同时运行
- 可以接受偶发的任务丢失（如全量采集可以重跑）
- 不需要 Worker 管理、不需要动态扩缩容
- Redis 已有但不想引入复杂的分布式协调

### 局限性

- **任务丢失**：Worker 崩溃时正在处理的任务直接丢失
- **无协调退出**：每个 Worker 独立判断队列空就退出，可能导致提前退出或永远不退出
- **无故障转移**：没有心跳检测，其他 Worker 无法接管崩溃 Worker 的任务
- **无动态配置**：无法运行时调整并发、限速、暂停

---

## 5. 分布式系统模式（Distributed）

### 设计目标

生产级可靠性。任务不丢失、崩溃可恢复、集群可管理。适合 7×24 小时长期运行的采集系统。

### 架构图

```
┌─────────────────────────────────────────────────────┐
│                   Redis (5.0+)                       │
│                                                      │
│  Streams (任务队列)     Registry (Worker 注册表)      │
│  Consumer Groups       Heartbeats (心跳)              │
│  Locks (分布式锁)       Config (动态配置)              │
│  Filters (去重 SET)     Control (控制状态)            │
└─────────────────────────────────────────────────────┘
     ▲              ▲              ▲
     │              │              │
┌────┴────┐   ┌────┴────┐   ┌────┴────┐
│Worker 1 │   │Worker 2 │   │Worker N │
│         │   │         │   │         │
│Coordinator│  │Coordinator│  │Coordinator│
│Engine    │   │Engine   │   │Engine   │
│Spider    │   │Spider   │   │Spider   │
└─────────┘   └─────────┘   └─────────┘
```

> 每个 Worker 内嵌一组集群组件（WorkerRegistry、HeartbeatDaemon、FailoverManager、DistributedLock、ClusterMessenger、DynamicConfig），通过 Engine 的 ClusterMixin 组合使用，而非单一 Coordinator 类。

### 核心设计

**Redis Streams + Consumer Groups**：

每个 Worker 属于同一个 Consumer Group。任务通过 `XADD` 写入 Stream，Worker 通过 `XREADGROUP` 消费。消费后必须 `XACK` 确认，否则任务留在 PENDING 列表中。

```
XADD → Stream → XREADGROUP → PROCESSING → XACK → DONE
                                    ↓ (未 ACK)
                              PENDING 列表
                                    ↓ (超时)
                              XAUTOCLAIM → 重新分配
```

这是与多节点协作模式最本质的区别：**任务有状态**。不是弹出就消失，而是要确认才完成。

**心跳注册**：每个 Worker 启动时向 Redis Hash 注册自己（`HSET registry:workers worker_id info`），然后每 15 秒（±20% Jitter）更新心跳时间戳。其他组件通过心跳判断 Worker 是否存活。

**两阶段故障检测**：

```
Worker 心跳超时（90s 未更新）
  → 标记为 suspect（怀疑）
  → 等待 30 秒二次确认
  → 仍无心跳 → 确认死亡
  → XAUTOCLAIM 回收其 PENDING 任务
  → 重新分配给其他 Worker
```

两阶段设计避免了网络抖动导致的误判。

**Leader 选举**：使用 Redis `SETNX` 实现。第一个成功设置 `lock:leader` 的 Worker 成为 Leader。Leader 负责：

1. 判断集群是否应该退出（队列空 + 所有 Worker 空闲）
2. 广播 shutdown 信号
3. 清理本轮运行的 Redis 数据

**双 Stream 优先级路由**：

```
Stream:tasks:high  ← 优先级 < 0 的任务（CRITICAL/HIGH）
Stream:tasks       ← 优先级 >= 0 的任务（NORMAL/LOW/BACKGROUND）
```

Worker 先读 high Stream，无任务时再读 normal Stream，保证高优先级任务优先处理。

**动态配置**：通过 Pub/Sub + 持久化 Key 双通道实现运行时配置变更：

- Pub/Sub：即时通知所有 Worker
- 持久化 Key：断连重连后恢复状态

支持运行时暂停/恢复/停止、调整并发、调整限速、动态注入种子 URL。

### 配置

```python
RUN_MODE = "distributed"
QUEUE_TYPE = "redis_stream"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
```

或使用工厂方法：

```python
from crawlo.config import CrawloConfig
config = CrawloConfig.distributed(
    redis_host="10.0.0.1",
    redis_port=6379,
    concurrency=16,
)
```

### 适用场景

- 7×24 小时长期运行的采集系统
- 任务不能丢失（如订单监控、价格追踪）
- 需要动态扩缩容（白天加机器、晚上减机器）
- 需要运行时管理（暂停、限速调整、紧急停止）

> **详细设计文档**：[分布式架构设计文档](distributed_architecture.md)（覆盖 10 大章节 + 8 个附录）

---

## 6. 三种模式对比

### 任务可靠性对比

| 场景 | 单机模式 | 多节点协作 | 分布式系统 |
|------|---------|-----------|-----------|
| 正常完成 | ✅ | ✅ | ✅ |
| Worker 崩溃 | ❌ 任务丢失 | ❌ 任务丢失 | ✅ XAUTOCLAIM 回收 |
| Redis 重启 | N/A | ❌ ZSET 丢失 | ✅ Stream 持久化 |
| 网络抖动 | N/A | ❌ 无检测 | ✅ 两阶段确认 |
| 进程重启续爬 | ⚠️ 需检查点 | ❌ | ✅ PENDING 恢复 |

### 集群管理能力对比

| 能力 | 单机模式 | 多节点协作 | 分布式系统 |
|------|---------|-----------|-----------|
| Worker 注册 | N/A | ❌ | ✅ |
| 心跳检测 | N/A | ❌ | ✅ 15s + Jitter |
| 故障转移 | N/A | ❌ | ✅ 两阶段 |
| Leader 选举 | N/A | ❌ | ✅ SETNX |
| 协调退出 | 自动 | ❌ 各自退出 | ✅ Leader 广播 |
| 动态扩缩容 | N/A | ⚠️ 可加可减 | ✅ 有数据丢失分析 |
| 动态配置 | N/A | ❌ | ✅ Pub/Sub + Key |
| 死信队列 | N/A | ❌ | ✅ 最多 3 次重试 |

### 性能对比

| 指标 | 单机模式 | 多节点协作 | 分布式系统 |
|------|---------|-----------|-----------|
| 单机 QPS | 500+ | 500+ | 500+ |
| 扩展性 | 1x | ~Nx（无协调开销） | ~Nx（有协调开销） |
| Redis 延迟 | 0 | ~1ms/操作 | ~1ms/操作 |
| 内存占用 | 随采集量增长 | 固定 | 固定 |
| 启动时间 | <1s | <2s | <3s（含集群初始化） |

---

## 7. 模式切换：零代码改动

三种模式的切换**只改配置，不改代码**：

```python
# 单机模式
RUN_MODE = "standalone"
QUEUE_TYPE = "memory"

# 多节点协作
RUN_MODE = "auto"
QUEUE_TYPE = "redis"

# 分布式系统
RUN_MODE = "distributed"
QUEUE_TYPE = "redis_stream"
```

爬虫代码完全不变：

```python
class MySpider(Spider):
    name = "my_spider"

    async def parse(self, response):
        yield Item(title=response.css("h1::text").get())
        yield response.follow(response.css(".next::attr(href)").get())
```

框架根据配置自动选择对应的队列实现、去重过滤器、协调器。业务层完全无感知。

### 切换路径建议

```
开发阶段                生产阶段                大规模阶段
  │                      │                      │
  ▼                      ▼                      ▼
standalone          auto + redis          distributed + redis_stream
(memory)            (ZSET)                (Streams + CG)
  │                      │                      │
  └── 验证逻辑 ──────────┘                      │
                         └── 多机分摊 ──────────┘
                                                 └── 集群管理
```

---

## 8. 共享引擎层

无论哪种模式，爬虫的执行引擎是同一套：

```
Spider.start_requests()
    ↓
Scheduler (去重 + 入队)
    ↓
Engine (调度循环)
    ↓
Middleware (process_request)
    ↓
Downloader (aiohttp / Playwright / Camoufox)
    ↓
Middleware (process_response)
    ↓
Spider.parse()
    ↓
Pipeline (清洗 → 入库)
    ↓
新的 Request → 回到 Scheduler
```

差异只在于 Scheduler 的内部实现：

| 组件 | 单机 | 多节点协作 | 分布式 |
|------|------|-----------|--------|
| 队列 | `asyncio.PriorityQueue` | `RedisPriorityQueue` | `RedisStreamQueue` |
| 去重 | `MemoryFilter` | `AioRedisFilter` | `AioRedisFilter` |
| 协调器 | 无 | 无 | 集群组件集群（WorkerRegistry / HeartbeatDaemon / FailoverManager 等） |
| 检查点 | 本地文件 | 本地文件 | 本地文件 + Redis PENDING |

引擎层的代码不需要 `if mode == 'distributed'` 这样的分支——它只调用 `scheduler.get()` 和 `scheduler.put()`，具体实现由配置决定。

---

*更多详情：[分布式架构设计文档](distributed_architecture.md) | [部署模式配置指南](guides/configuration/run-modes.md) | [生产部署](deployment.md)*
