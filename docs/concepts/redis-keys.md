# 分布式系统 — Redis Key 说明

分布式模式（`RUN_MODE='distributed'`，`QUEUE_TYPE='redis_stream'`）下，Crawlo 使用以下 Redis Key 实现任务调度、节点管理、故障转移等功能。

> `{project}` 和 `{spider}` 由配置中的 `PROJECT_NAME` 和爬虫 `name` 决定。

## 任务队列

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:stream:tasks` | Stream | **任务队列** — 所有待消费的 Request 消息 | `RedisStreamQueue` |
| `crawlo:{project}:{spider}:stream:failed` | Stream | **死信队列** — 投递次数超限的消息 | `RedisStreamQueue` |
| `crawlo:{project}:{spider}:group:workers` | Consumer Group | **消费组** — 所有 Worker 加入此组，XREADGROUP 分配任务 | `RedisStreamQueue` |

**消息格式**（Stream 中每条消息的字段）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | bytes | 序列化的 Request 对象 |
| `priority` | int | 优先级（数值越小越优先） |
| `enqueued_at` | float | 入队时间戳 |
| `retry_count` | int | 已重试次数（超过 `STREAM_DELIVERY_COUNT_LIMIT` 进死信） |

## 节点管理

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:registry:workers` | HASH | **Worker 注册表** — 存储每个 Worker 的详细信息（host/pid/status/任务计数等） | `WorkerRegistry` |
| `crawlo:{project}:{spider}:registry:heartbeats` | ZSET | **心跳记录** — score=时间戳，用于检测崩溃 Worker | `WorkerRegistry` |

**注册表结构**（HASH 的每条 field 对应一个 Worker）：

```json
// HASH field: worker:{id}
{
  "id": "worker-abc123",
  "host": "192.168.1.10",
  "pid": 12345,
  "status": "running",           // running / idle / suspect / stopping
  "tasks_completed": 1000,
  "tasks_processing": 5,
  "last_heartbeat": 1716800000.0
}
```

## 分布式锁

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:lock:failover` | String + TTL | **故障检测锁** — 确保同一时间只有一个 Worker 执行故障检测 | `FailoverManager` |
| `crawlo:{project}:{spider}:lock:init` | String + TTL | **初始化锁** — 防止多 Worker 同时创建 Consumer Group 等 | `DistributedLock` |

## 进度与监控

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:progress:stats` | HASH | **全局统计** — 总入队数/已完成数/失败数 | `ProgressAggregator` |
| `crawlo:{project}:{spider}:progress:items` | HASH | **各 Worker 产出** — 每个 Worker 的 Item 产出统计 | `ProgressAggregator` |

## 动态配置

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:control:state` | String | **控制状态** — `running` / `paused` / `shutdown`（持久化兜底） | `DynamicConfig` |
| `crawlo:{project}:{spider}:config:rate_limits` | HASH | **限速配置** — 域名级速率覆盖 | `DynamicConfig` |
| `crawlo:{project}:{spider}:config:seed_urls` | LIST | **动态种子 URL** — 运行时添加的种子 URL | `DynamicConfig` |

## 分布式限流

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:rate:{domain}` | String | **令牌计数** — 当前可用令牌数 | `DistributedRateLimiter` |
| `crawlo:{project}:{spider}:rate:{domain}:ts` | String | **时间戳** — 上次补充令牌的时间 | `DistributedRateLimiter` |

## 去重过滤器

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:filter:fingerprint` | SET | **请求去重** — 已发送过的 Request 指纹（SISMEMBER 判重） | `AioRedisFilter` |
| `crawlo:{project}:{spider}:item:fingerprint` | SET | **数据项去重** — 已处理过的 Item 指纹 | `RedisDedupPipeline` |

## 协调退出

| Key | 类型 | 用途 | 所属模块 |
|-----|------|------|---------|
| `crawlo:{project}:{spider}:cluster:leader` | String + TTL | **Leader 锁** — 记录当前 Leader Worker（SETNX 选举，过期自动重选） | `Engine` |

---

## Key 命名总览

```
crawlo:{project}:{spider}:stream:tasks              Stream    任务队列
crawlo:{project}:{spider}:stream:failed             Stream    死信队列
crawlo:{project}:{spider}:group:workers             CG        消费组
crawlo:{project}:{spider}:registry:workers          HASH      Worker 注册表
crawlo:{project}:{spider}:registry:heartbeats       ZSET      心跳记录
crawlo:{project}:{spider}:lock:failover             String    故障检测锁
crawlo:{project}:{spider}:lock:init                 String    初始化锁
crawlo:{project}:{spider}:progress:stats            HASH      全局统计
crawlo:{project}:{spider}:progress:items            HASH      各 Worker 产出
crawlo:{project}:{spider}:control:state             String    控制状态
crawlo:{project}:{spider}:config:rate_limits        HASH      限速配置
crawlo:{project}:{spider}:config:seed_urls          LIST      动态种子 URL
crawlo:{project}:{spider}:rate:{domain}             String    令牌计数
crawlo:{project}:{spider}:filter:fingerprint        SET       请求去重
crawlo:{project}:{spider}:item:fingerprint          SET       数据项去重
crawlo:{project}:{spider}:cluster:leader            String    Leader 选举锁
```
