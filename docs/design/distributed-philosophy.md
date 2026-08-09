# Crawlo 分布式设计哲学

> 本文档回答一个问题：**为什么 Crawlo 的分布式模块会设计成今天这个样子，而不是 Scrapy Redis Queue / Celery / RQ 那种经典做法？**
>
> 配套技术细节见 [distributed_architecture.md](../distributed_architecture.md)。
> 代码入口见 [cluster/coordinator.py](file:///Users/oscar/projects/Crawlo/crawlo/cluster/coordinator.py)、[queue/backends/redis_stream.py](file:///Users/oscar/projects/Crawlo/crawlo/queue/backends/redis_stream.py)、[commands/cluster.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/cluster.py)。

---

## 0. 一句话哲学

> **用最小的外部依赖（只有一个 Redis），做最"正确"的事——不丢数据、不重复生成种子、扩缩容不中断、网络分区不会脑裂。分布式不是把内存队列换成 Redis List 就完事，是把单机下"由 Python 调度器保证"的正确性，搬到 Redis 里重新实现一遍。**

所有的设计选择都来自这条原则，而不是"业界通用方案"。

---

## 1. 为什么不做 Scrapy-Redis / Celery 那套？

先讲"反设计"：我们是**刻意**没做下面这些业界主流方案。

### 1.1 Scrapy-Redis 模式（Redis List / ZSET 作队列）

Scrapy-Redis / Frontera 经典架构：

- 用 `LPUSH / BRPOP` 的 List 当普通队列
- 去重靠外部 Redis SET
- 每个爬虫用独立 key，或者 master spider 负责生成种子

**三大硬伤，Scrapy 社区 10 年没解决**：

| 问题 | Scrapy-Redis 现状 | Crawlo 的看法 |
|---|---|---|
| **BRPOP 拿完就丢** | Worker 拿到请求后崩溃 → **消息永久丢失**，**至少一次**语义都没有 | **不能接受**。长驻爬数据务崩一次就丢一条，跑一周相当于随机丢 N% 数据 |
| **没有 Consumer Group** | 每个 Worker 都在 BRPOP，无法知道"这条消息到底谁在处理"，**没有 PEL（Pending Entries List）** | 必须有。故障回收的前提是：能知道谁拿走了消息多久没 ACK |
| **种子生成靠外部 Master** | 要么跑一个独立 `redis_publisher.py` 放种子，要么所有 Worker 同时 `start_requests` 靠 SET 去重兜底 | Master 是单点；大家一起跑又浪费 CPU + 产大量重复指纹 |

结论：**Redis List 适合"允许丢消息"的任务分发，不适合爬虫。** 爬数据的本质是"**对 URL 全集做精确的一次遍历**"，List 结构天然不适合。

### 1.2 Celery 模式（Broker + Result Backend）

Celery 的设计原点是"**面向函数调用的任务调度**"（dispatch image resize, send email…）：

- 任务就是 Python 函数 `def add(a,b)`
- 核心是 Broker / Result Backend / Chord / Chain / Beat
- Worker 数量由 supervisor/systemd 扩缩容，任务是 **short-lived function call**

**爬虫和函数调用有本质区别**：

| 维度 | Celery 任务 | Crawlo 分布式爬虫 |
|---|---|---|
| **任务大小** | KB 级别（函数参数） | 请求对象本身就有 headers/meta/callback，且产生**递归无限的新请求** |
| **生命周期** | 秒级 | 分钟~小时级，一个在途请求长时间 HOLD 是正常的 |
| **产出** | 一个 return value | 百万级 Item + 百万级 follow-up Request，需要**跨 Worker 去重** |
| **速率** | 1k rps，不要求域名限速 | 需要 per-domain 自适应节流 + robots.txt 遵守，天然非线性 |
| **全局并发** | 由 worker count 决定 | 需要全集群共享的 dedup + rate limiter |
| **故障语义** | 允许重试函数调用 | 需要"至少一次 + 幂等 + 死信"，否则重放会写脏数据 |

把 Crawlo 套进 Celery 等于把爬虫切成一个个短函数，失去了 Engine 的背压、连接池复用、per-domain 队列、渲染内核上下文、ResourceScope 泄漏检测。**是削足适履**。

### 1.3 RQ / Dramatiq / Huey

和 Celery 同样的本质问题：**面向函数调度**，不适合"**会产出无限多新任务 + 需要共享连接池 + 需要每域名限速**"的递归工作负载。

---

## 2. Crawlo 的 4 条设计原则

### 2.1 原则 1：**正确性 > 性能**

分布式爬虫，用户最怕的两件事：

1. **抓了一周，崩一次，进度全没了** → 数据丢失
2. **重启后又从头抓一遍** → 重复抓、写脏、浪费流量

Crawlo 的正确性等级：

| 能力 | 实现位置 | 代价 |
|---|---|---|
| **不丢在途消息** | Stream Pending Entry List + XAUTOCLAIM | 多一次 Redis PEL 记录开销 |
| **不重生成种子** | SETNX `seed:generator` + 后台 TTL 续期 + 死锁检测 | 一次 Redis RTT |
| **至少一次语义** | ACK/XDEL 原子化；ACK 前崩 → 重放 | 数据库端需要唯一键做最终幂等 |
| **死信不丢** | `stream:failed` + `crawlo dead-letter` CLI | 额外 Stream 存储 |

> 只要能保证"正确性"，哪怕单 Worker QPS 降 30% 也值。真实长驻任务里，一天崩一次导致的返工，远比单小时多抓 30% 数据贵。

### 2.2 原则 2：**无中心 Worker，只有一个 Redis 状态中心**

很多框架一上来就做：

- Scheduler / Master / Worker 三种角色
- Leader + Followers，Raft 选主（etcd/zk/redis raft）
- Nacos / Consul 服务发现

Crawlo 的选择：**只有一种节点——Worker，所有 Worker 对等**。Redis 是唯一的状态中心和协调中心。

**理由**：

| 选择 | 收益 |
|---|---|
| 无中心 Worker | 部署成本 = 1：只要能连上 Redis，`crawlo run <spider>` 就加入集群。运维不会问"Master 挂了怎么办" |
| 只有 Redis 一个依赖 | 公司的 Redis 实例已经有 SRE 维护；再部署 ZooKeeper/Consul 成本是 **N×** 倍 |
| 只在协调退出场景自选举临时 Leader | SET NX PX 就能做，不需要 Raft/zk |

代码体现：[cluster/coordinator.py](file:///Users/oscar/projects/Crawlo/crawlo/cluster/coordinator.py#L390) — 每个 Worker 都初始化 9 个相同的集群组件；[commands/cluster.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/cluster.py) 里 state/reset/pause/resume/shutdown 都是直接写 Redis key，不经过任何 master。

### 2.3 原则 3：**配置就是三段式。不要让用户猜**

很多分布式框架的配置地狱：

```
broker_url = …
result_backend = …
task_routes = …
worker_concurrency = …
task_acks_late = …
worker_prefetch_multiplier = …
reject_on_worker_lost = …
task_ignore_result = …
task_track_started = …
```

Crawlo 的配置原则：**用户只说一句"我要分布式"，剩下的一切默认值都自洽。**

配置映射在 [config/base.py](file:///Users/oscar/projects/Crawlo/crawlo/core/config/base.py#L33-L53)：

| RUN_MODE 一行设置 | 自动生效的隐含配置 |
|---|---|
| `standalone`（默认） | `QUEUE_TYPE=memory` + MemoryFilter + MemoryDedupPipeline |
| `distributed` | `QUEUE_TYPE=redis_stream` + AioRedisFilter + RedisDedupPipeline + `CONCURRENCY=16` + `MAX_RUNNING_SPIDERS=10` + `DISTRIBUTED_WORKER_IDLE_TIMEOUT=120` + `STREAM_DELIVERY_COUNT_LIMIT=5` + `STREAM_CONSUMER_IDLE_TIMEOUT=90s` + `CLUSTER_FAILOVER_CHECK_INTERVAL=15s` + `CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START=True` |

一个"用户改了 QUEUE_TYPE=redis 但忘了 RUN_MODE=distributed"的坑？直接在 [queue_manager.py](file:///Users/oscar/projects/Crawlo/crawlo/queue/queue_manager.py#L584) 里自动升级：`Distributed mode: upgrading QUEUE_TYPE=redis → redis_stream`。

**用户不需要理解 Redis List vs Stream 的区别。**

### 2.4 原则 4：**故障检测两阶段，不把网络抖动当 Worker 崩。**

典型分布式系统两种错误倾向：

1. **太敏感**：一次网络抖动（丢 2 个包）就把 Worker 判死 → 它正在处理的消息被回收重放 → 两端同时写 DB → 脏数据
2. **太迟钝**：Worker 真崩了等 10 分钟才回收 → 用户看 0 QPS 以为任务完成了

Crawlo 用两阶段：

```
Phase 1 (t=90s 心跳超时)  →  STATUS=suspect，不做任何事
Phase 2 (suspect 已挂 30s) →  DistributedLock 持锁 → XAUTOCLAIM 回收 + deregister
                                             ↑
                               同一时刻只有 1 个 Worker 做回收，避免惊群
```

代码位置：[cluster/coordinator.py](file:///Users/oscar/projects/Crawlo/crawlo/cluster/coordinator.py) → FailoverManager。

同时 STATUS_STOPPING 的 Worker（正在优雅退出 drain）**被豁免回收**，否则你 Ctrl+C 停一个 Worker 会触发 failover 抢它正在清理的任务。

---

## 3. 分布式的三层心智模型：**Queue / Dedup / Coordination**

很多用户第一次接触分布式爬虫，脑子里只有"换 Redis 当队列"。Crawlo 的分布式其实是三层独立的能力，每一层单独打开或关闭：

```
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 3 — Coordination（协调层）                │
│                                                                  │
│  WorkerRegistry  │ Heartbeat │ FailoverManager │ DistributedLock │
│  ProgressReport  │ DynamicConfig │ ClusterMessenger(Pub/Sub)     │
│  Leader Epoch    │ Control State (pause/resume/shutdown)         │
└─────────────────────────────────────────────────────────────────┘
         │ 90s 心跳 │ 15s Failover 轮询 │ SET NX 原子锁 │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 2 — Dedup（跨 Worker 去重）                │
│                                                                  │
│  dedup:request (Redis SET)  │  dedup:item (Redis SET)           │
│  AioRedisFilter             │  RedisDedupPipeline                │
└─────────────────────────────────────────────────────────────────┘
         │ dedup 必须在 enqueue 之前做
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 1 — Queue（可靠消息队列）                   │
│                                                                  │
│  Redis Stream (tasks / tasks:high / failed)                     │
│  Consumer Group 'workers'   │   Pending Entry List              │
│  XADD / XREADGROUP / XACK / XDEL / XCLAIM / XAUTOCLAIM          │
└─────────────────────────────────────────────────────────────────┘
```

这三层可以独立讨论：

### Layer 1 Queue：为什么是 Stream，而不是 List/ZSET

- `XADD` 带 ID，天然支持幂等重放
- `XREADGROUP GROUP consumer >` 支持**按消费者分配 + 记一条 Pending**
- PEL 是**故障回收的关键**：崩溃 Worker 正在处理的消息不会丢
- `XAUTOCLAIM`（6.2+）一条命令回收超时消息
- Stream 天然支持 MAXLEN 修剪，List 要自己做 LTrim 计数

代码：[RedisStreamQueue](file:///Users/oscar/projects/Crawlo/crawlo/queue/backends/redis_stream.py#L38)。

### Layer 2 Dedup：分布式爬虫不产生重复，比快 20% 重要 10 倍

单机模式下 dedup 是 Python `set()`，秒级判断。分布式下：

- **请求去重**（`AioRedisFilter`）：同一 URL + 同参数 → 只入队一次。避免两个 Worker 各自从不同页面发现同一个链接，都去抓
- **条目去重**（`RedisDedupPipeline`）：同一条业务主键 → pipeline 里就 drop，不灌到 MySQL

很多项目上线后发现 QPS 够但 DB 里全是重复行，就是 dedup 没做分布式。

### Layer 3 Coordination：大部分框架缺失的这一层

Queue + Dedup 解决"**能不能跑**"。Coordination 解决"**跑完后能不能停、能不能改限速、能不能动态加种子、能不能知道哪个 Worker 挂了、能不能在 0 Worker 残留 shutdown 时 reset**"。

具体能力：

- **WorkerRegistry + HeartbeatDaemon**：总览命令 `crawlo cluster state` 才能显示有多少活 Worker、它们的 QPS
- **FailoverManager + DistributedLock**：120s 内回收崩溃 Worker 的任务，不丢一条
- **ClusterMessenger + DynamicConfig**：双通道配置——Pub/Sub 立即生效，Redis Key 持久化兜底（断连重连也不丢 shutdown 消息）
- **Leader 选举（仅协调退出）**：所有 Worker idle 时需要一个 Worker 决定"是不是大家都没事了，可以一起关了"。只有这里用到 Leader，其他场景一律无中心
- **`crawlo cluster reset`**：生产级兜底。空集群下 shutdown 状态遗留 → 0 Worker 能解除，CLI 直接一次 reset 即可救活

代码：[commands/cluster.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/cluster.py)（5 个子命令：state/reset/pause/resume/shutdown）。

---

## 4. 运行模式三段式：standalone / 协作 / distributed

很多框架只有"单机"和"分布式"两档。Crawlo 做了**三档渐进式**：

| RUN_MODE | 用户心智 | 典型场景 | 关键行为 |
|---|---|---|---|
| **standalone** | 我就是跑一下 | 本地开发 / 5k URL | 纯内存队列 + Python set() dedup；0 Redis 依赖 |
| **（隐含）协作模式** | 我有 Redis，但不想折腾集群 | 单 Worker + 持久化断点 / 多 Worker 共享 dedup | `QUEUE_TYPE=redis(老的Redis List队列)` / `redis_stream` + RUN_MODE 仍保持 standalone 或 auto；不启动 WorkerRegistry/FailoverManager |
| **distributed** | 我要严格的故障回收 + 扩缩容 | 生产深爬 / 多节点并行 | 激活 9 个集群组件；Worker 心跳 + Failover + 协调退出全部开启 |

"协作模式"是刻意留下的中间档。很多小团队的情况是：

- 一台机器够了，但希望"重启后接着抓"（Queue 持久化 + Dedup 共享）
- 不想要 Heartbeat、Failover 的日志噪音
- 不想处理 "shutdown 状态残留"之类的运维问题

这种情况下不需要跳级进入 `distributed`。

代码实现：`RUN_MODE` → [MODE_CONFIG_MAP](file:///Users/oscar/projects/Crawlo/crawlo/core/config/base.py#L33-L53)。

---

## 5. 关键设计权衡与取舍

| 决定 | 选择 | 放弃 | 理由 |
|---|---|---|---|
| **消息语义** | 至少一次 + dedup/唯一键幂等兜底 | 精确一次 | 精确一次在纯 Redis 下需要外部 2PC / 事务 DB，复杂度爆炸 |
| **队列模型** | 多消费者单 Stream + 优先级 2 条 Stream | 每个 Worker 专属队列 | 专属队列会导致热点 Worker 堆积、空闲 Worker 无任务可抓（历史 Scrapy-Redis 常见坑） |
| **去重位置** | enqueue 前做 + pipeline 内再做一次 | 只在其中一处 | enqueue 前防重放；pipeline 内兜底防 Worker ACK 前崩溃 |
| **故障回收触发** | 心跳 + suspect → failover（120s 最坏） | 仅依赖 Stream idle 自动回收 | 纯 Stream idle 在消费者心跳正常、但其实进程 OOM 的情况（GC 仍发心跳但业务停了）**永远不回收** |
| **控制通道** | Pub/Sub + Redis Key 双通道 | 纯 Pub/Sub 或 纯 Key | Pub/Sub 会丢消息；纯 Key 检查有延迟。结合才稳 |
| **Leader 选举使用范围** | 只在协调退出时临时用 | 全局 Master | Master 模式一挂就全挂；临时 Leader 失败不影响抓取主循环 |
| **Worker 命名** | `{host}-{pid}-{uuid[:8]}` | 自增 ID / 固定名 | pid 重启即变，避免新起同名 Worker 被当"老 Worker 复活"误判 |

---

## 6. 什么时候**不该**用分布式模式

- **<5k URL 的小任务**：standalone 就够。Redis + XREADGROUP 的 RTT 成本比内存队列高，小任务反而变慢
- **单机就能在 24h 内跑完**：除非你要断点续爬持久化（那用协作模式 `QUEUE_TYPE=redis_stream` 就够），否则分布式 + Heartbeat 日志噪音不值得
- **抓取目标极度不均衡（一个域名占 99% 请求）**：单 Worker 的 per-domain 节流会比 10 个 Worker 抢一个 token bucket 更稳定。这种情况下分布式的收益是"连接池数 × Worker 数"，但节流器复杂度陡增，建议先 standalone + 最大连接池开满
- **极度敏感的 cookie/session**：每个 Worker 都起一个 Playwright Context，登录态如果是**绑定 IP/User-Agent 的**，多 Worker 就会互相踢下线。这种场景要么单 Worker 渲染，要么做 Cookie 池 + IP 代理池配套

---

## 7. 总览：Crawlo 分布式 vs 经典方案对比

| 维度 | Crawlo distributed | Scrapy + Scrapy-Redis | Celery + Redis Broker | RQ |
|---|---|---|---|---|
| **依赖数** | **1（Redis 5.0+）** | 1（Redis） | 1~3（Broker+可选 Result Backend） | 1（Redis） |
| **不丢在途消息** | ✅ Stream PEL + XAUTOCLAIM | ❌ BRPOP 拿完就丢 | ✅ acks_late + reject_on_worker_lost | ❌ BRPOP |
| **种子只生成一次** | ✅ SETNX 种子生成器 + 续期 | ❌ / 各爬虫自己 start_requests → Redis dedup 后显 | ✅（任务只进一次队列） | ✅（同上） |
| **跨 Worker 去重** | ✅ 请求+Item 双层 Redis SET | ✅（SET） | ❌（无原生支持，业务写） | ❌ |
| **故障回收** | ✅ 两阶段心跳 + XAUTOCLAIM，最坏 120s | ❌ 无内置 | ✅ visibility timeout | ⚠️ worker 崩溃会留孤儿 key |
| **协调退出** | ✅ 自选举 Leader + 双通道（Pub/Sub + Key） | ❌ 手动 kill | ❌ 用 celery beat/flower 做 | ❌ |
| **动态限速** | ✅ Lua 令牌桶，全集群共享 | ❌ | ❌ 每个 worker 独立 | ❌ |
| **即插即用扩缩容** | ✅（启动直接加入 group） | ✅（启动就 BRPOP） | ✅ | ✅ |
| **内置 dead-letter** | ✅ stream:failed + CLI 重放 | ❌ | ✅（dead-letter-exchange 可选） | ❌ |
| **单 Worker 持久化队列** | ✅（协作模式 standalone + redis_stream） | ⚠️（Redis List 但不保证不丢） | ⚠️（函数粒度） | ⚠️（函数粒度） |
| **适合的负载** | 递归深爬 / 百万级 URL / 长期驻留 | 轻量批量 / 短期 | 函数调用 / 短任务队列 | 简单后台任务 |

---

## 8. 一句话记忆点

> **Crawlo 分布式 = 把单机版 Engine 对"正确性"的保证，原封不动搬到多 Worker 场景——用 Redis Stream PEL 代替内存 deque、用 Redis SET 代替 Python set、用 SETNX+心跳代替进程内事件、用 XAUTOCLAIM 保证 Worker 崩了也不丢一条。不是多了什么魔法，只是把单机里自然成立的不变量，变成 Redis 里面显式维护的状态。**
