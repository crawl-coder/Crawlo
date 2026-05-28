# 三种部署模式详解

Crawlo 提供三种部署模式，覆盖从单机调试到生产级大规模分布式爬取的全场景需求。

## 模式对比

| 特性 | 内存模式 | 多节点协作 | 分布式系统 ⭐ |
|------|---------|-----------|-------------|
| **配置** | `RUN_MODE='standalone'` `QUEUE_TYPE='memory'` | `RUN_MODE='auto'` `QUEUE_TYPE='redis'` | `RUN_MODE='distributed'` `QUEUE_TYPE='redis_stream'` |
| **队列** | in-memory PriorityQueue | Redis ZSET | Redis Stream + Consumer Group |
| **去重** | 内存 SET | Redis SET | Redis SET |
| **协调机制** | 无（单进程） | 竞争消费（BZPOPMIN） | ACK + 心跳 + 故障转移 + Leader 协调退出 |
| **Redis 要求** | ❌ 不需要 | ✅ 必需 | ✅ 必需 |
| **退出方式** | 队列空 + 组件空闲，自动退出 | 队列空 + 组件空闲，自动退出 | Leader 检测全空闲后 broadcast shutdown |
| **适用场景** | 开发调试、小规模单机 | 多机并发，可接受任务丢失 | 生产环境，任务可靠性要求高 |

> 三种模式的优先级模型完全一致（数值越小越优先），切换模式无需修改爬虫代码。

---

## 1. 内存模式

### 适用场景

- ✅ 本地开发调试
- ✅ 学习框架特性
- ✅ 小规模数据采集（< 1万条）
- ✅ 不想安装 Redis

### 配置

```python
# settings.py
RUN_MODE = 'standalone'
QUEUE_TYPE = 'memory'
CONCURRENCY = 8
DOWNLOAD_DELAY = 1.0
```

### 运行机制

```
Spider → Scheduler(in-memory queue) → Engine → Downloader → Processor → Pipeline
```

- 使用 `MemoryQueue`（`asyncio.PriorityQueue`）
- 使用 `MemoryFilter`（内存 `set()` 去重）
- 所有组件空闲 + 队列空 → 自动退出

### 优势

- ✅ 无需任何外部依赖
- ✅ 启动速度快
- ✅ 适合快速开发调试

### 限制

- ❌ 不支持多机扩展
- ❌ 重启后队列数据丢失
- ❌ 不适合大规模数据采集

### 注意事项

1. **内存占用**：队列中所有等待的 Request 都存储在内存中。大规模爬取时请关注内存使用，可通过 `MEMORY_SCHEDULER_MAX_QUEUE_SIZE` 限制队列大小。
2. **进程崩溃**：进程异常退出会导致所有未处理的请求丢失。如需可靠性，请启用检查点（`CHECKPOINT_ENABLED=True`）。
3. **适用粒度**：建议 1 万条以内的采集任务使用内存模式，超过此规模请考虑使用多节点协作或分布式系统模式。
4. **并发控制**：单进程内并发数（`CONCURRENCY`）建议不超过 32，过高会导致事件循环调度开销增加。

---

## 2. 多节点协作模式

### 适用场景

- ✅ 多机并发爬取
- ✅ 已有 Redis 环境
- ✅ 能接受 Worker 崩溃导致任务丢失

### 配置

```python
# settings.py
RUN_MODE = 'auto'
QUEUE_TYPE = 'redis'
CONCURRENCY = 16

# Redis 配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
```

### 运行机制

```
                ┌──────────────────────┐
                │    Redis              │
                │  ZSET + SET 去重      │
                └──────────────────────┘
                    ▲            ▲
              竞争消费        共享去重
              ┌──┴──┐       ┌──┴──┐
           Worker 1  ...  Worker N
```

多个 Worker 通过共享 Redis 实现并行爬取，Worker 之间通过 `BZPOPMIN` 竞争消费，无直接通信。

### 退出条件

每个 Worker 独立判断：队列空 + 所有组件空闲 → 自动退出。各 Worker 不协调，跑完即停。

### 优势

- ✅ 支持多机并发
- ✅ 全局去重
- ✅ 代码与分布式系统模式兼容

### 局限性

| 缺陷 | 影响 | 严重度 |
|------|------|--------|
| 无 ACK 机制 | Worker 崩溃后已出队的任务丢失 | 🔴 |
| 无节点注册/心跳 | 无法感知在线节点 | 🔴 |
| 无故障转移 | 崩溃 Worker 的任务永久丢失 | 🔴 |
| 无进度聚合 | 无法查询全局爬取进度 | 🟡 |

### 注意事项

1. **任务丢失风险**：Worker 出队后尚未处理完成就崩溃，该任务将永久丢失（无 ACK 机制）。适合对任务完整性要求不高的场景。
2. **Worker 独立退出**：各 Worker 独立检测空闲状态并退出。Worker A 可能先于 Worker B 退出，导致队尾部分任务集中到剩余 Worker 上。建议各 Worker 的并发数和配置保持一致。
3. **Redis 是硬依赖**：所有 Worker 必须能访问同一个 Redis 实例/集群。Redis 故障时，队列操作会抛出异常，爬虫需自行处理重连逻辑。
4. **队列大小限制**：ZSET 队列的请求数量受 Redis 内存限制。大量请求积压时，建议监控 Redis 内存使用，或通过 `backpressure` 控制入队速率。

---

## 3. 分布式系统模式 ⭐

### 适用场景

- ✅ 生产环境部署
- ✅ 任务可靠性要求高
- ✅ 需要自动故障转移
- ✅ 多节点大规模爬取

### 配置

```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis_stream'

# Redis 配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# 并发控制
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5

# 集群配置（可选，默认启用）
CLUSTER_HEARTBEAT_INTERVAL = 15      # 心跳间隔（秒）
CLUSTER_WORKER_TIMEOUT = 90          # Worker 超时（秒）
CLUSTER_FAILOVER_CHECK_INTERVAL = 30  # 故障检测间隔（秒）
DISTRIBUTED_COORDINATED_SHUTDOWN_ENABLED = True  # Leader 协调退出
```

### 运行机制

```
┌─────────────────────────────────────────────────────┐
│                   Redis Cluster                      │
│  Streams | Registry | Locks | Filters | Config      │
└─────────────────────────────────────────────────────┘
        ▲          ▲          ▲
   Worker 1    Worker 2    Worker N   (各内嵌 Coordinator)
```

#### 任务状态流转

```
XADD → PENDING → XREADGROUP → PROCESSING → XACK → DONE
                              ↘ 崩溃/超时
                                XCLAIM → 其他 Worker 回收
                                  ↘ 重试耗尽 → 死信队列
```

#### 核心能力

| 能力 | 实现方式 |
|------|---------|
| **ACK 确认** | XACK 确认完成，NACK 重试或进死信 |
| **节点注册** | Redis HASH 注册表，ZSET 心跳 |
| **故障转移** | 心跳超时 → suspect 二次确认（30s）→ XCLAIM 回收任务 |
| **Leader 协调退出** | SETNX 选举，检测全空闲后 broadcast shutdown |
| **分布式限流** | Lua 令牌桶，跨 Worker 共享配额 |
| **动态配置** | Pub/Sub + 持久化 Key 双通道 |

### 退出方式

```
Leader 每 10s 检查:
  种子已全部生成完毕
  + Stream 队列为空
  + 所有 Worker 空闲 (tasks_processing == 0)
  + 2s 后重检（防瞬态误判）
  → 全部满足 → broadcast shutdown → 所有 Worker 优雅退出
```

兜底：`DISTRIBUTED_WORKER_IDLE_TIMEOUT`（默认 120s，设为 0 禁用）。

### Redis Key 一览

| Key | 类型 | 用途 |
|-----|------|------|
| `{ns}:stream:tasks` | Stream | 任务队列 |
| `{ns}:stream:failed` | Stream | 死信队列 |
| `{ns}:group:workers` | CG | Consumer Group |
| `{ns}:registry:workers` | HASH | Worker 注册表 |
| `{ns}:registry:heartbeats` | ZSET | 心跳记录 |
| `{ns}:lock:failover` | String | 故障检测锁 |
| `{ns}:filter:fingerprint` | SET | 请求去重 |
| `{ns}:item:fingerprint` | SET | 数据项去重 |
| `{ns}:control:state` | String | 控制状态 |
| `{ns}:cluster:leader` | String | Leader 选举锁 |

> 详细说明见：[Redis Key 说明](../concepts/redis-keys.md)

### 5 Worker 测试结果

| Worker | 运行时长 | Item | Pages/min |
|--------|----------|:----:|:---------:|
| Worker 1 | 323s | 814 | 164 |
| Worker 2 | 317s | 800 | 161 |
| Worker 3 | 313s | 780 | 159 |
| Worker 4 | 308s | 790 | 160 |
| Worker 5 | 303s | 810 | 161 |
| **合计** | **~5.3min** | **3,994** | **avg 161** |

跨 5 个 Worker 零重复，Leader 自动协调退出。

> 详细测试步骤见：[5 Worker 分布式测试](../guides/distributed-test.md)

### 注意事项

1. **Redis 版本要求**：基础功能需要 Redis 5.0+（Consumer Group + XREADGROUP/XACK）。XAUTOCLAIM（6.2+）用于故障转移，Redes 5.0~6.1 自动降级为 XPENDING + XCLAIM。
2. **Redis 不可用**：分布式系统模式严格要求 Redis，Redis 不可用时爬虫会报错退出（不会降级到内存模式）。请确保 Redis 的高可用（主从/集群/哨兵）。
3. **Leader 协调退出依赖 Redis**：Leader 通过 Redis SETNX 选举，检测到全空闲后通过 Pub/Sub + 持久化 Key 广播 shutdown。若 Redis 故障导致广播失败，Worker 会在 `DISTRIBUTED_WORKER_IDLE_TIMEOUT`（默认 120s）后自行退出。
4. **种子 URL 幂等**：多个 Worker 启动时各自调用 `start_requests()` 入队种子 URL。去重过滤器保证相同 URL 只入队一次，无需额外协调。
5. **Worker 数量**：Redis Stream 的 Consumer Group 对消费者数量没有硬限制，但过多 Worker 可能导致 XPENDING 查询和 XCLAIM 操作的开销增加。建议单任务不超过 20 个 Worker。
6. **时间同步**：故障检测依赖心跳时间戳（Redis ZSET score）。各 Worker 的系统时间偏差过大可能导致心跳误判。建议所有 Worker 使用 NTP 同步时间。

---

## 如何选择？

### 决策树

```
你的需求是什么？
│
├─ 本地开发调试、快速验证
│   └─> 内存模式
│
├─ 多机并发，可接受任务丢失
│   └─> 多节点协作模式
│
└─ 生产环境，任务可靠性要求高
    └─> 分布式系统模式 ⭐
```

### 快速选择表

| 你的情况 | 推荐模式 |
|---------|---------|
| 第一次学习 Crawlo | 内存模式 |
| 本地开发测试 | 内存模式 |
| 有 Redis，需要多机并发 | 多节点协作 |
| 有 Redis，生产环境 | 分布式系统 ⭐ |
| 需要 ACK/故障转移/协调退出 | 分布式系统 ⭐ |
| 需要分布式限流/动态配置 | 分布式系统 ⭐ |
