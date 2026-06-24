# 分布式系统 — Redis Key 说明

分布式模式（`RUN_MODE='distributed'`，`QUEUE_TYPE='redis_stream'`）下，Crawlo 使用以下 Redis Key 实现任务调度、节点管理、故障转移等功能。

> `{project}` 和 `{spider}` 由配置中的 `PROJECT_NAME` 和爬虫 `name` 决定。

## Key 命名总览

| 分类 | Key | 类型 | 用途 |
|------|-----|------|------|
| **任务队列** | `crawlo:{p}:{s}:stream:tasks` | Stream | 任务队列 |
| | `crawlo:{p}:{s}:stream:tasks:high` | Stream | 高优先级任务队列 |
| | `crawlo:{p}:{s}:stream:failed` | Stream | 死信队列 |
| | `crawlo:{p}:{s}:group:workers` | Consumer Group | 消费组 |
| **节点管理** | `crawlo:{p}:{s}:registry:workers` | HASH | Worker 注册表 |
| | `crawlo:{p}:{s}:registry:heartbeats` | ZSET | 心跳记录 |
| **分布式锁** | `crawlo:{p}:{s}:lock:failover` | String+TTL | 故障检测锁 |
| | `crawlo:{p}:{s}:lock:init` | String+TTL | 初始化锁 |
| | `crawlo:{p}:{s}:lock:leader` | String+TTL | Leader 选举锁 |
| **控制与配置** | `crawlo:{p}:{s}:control:state` | String | 控制状态（running/paused/shutdown） |
| | `crawlo:{p}:{s}:config:rate_limits` | HASH | 域名级限速 |
| | `crawlo:{p}:{s}:config:seed_urls` | LIST | 动态种子 URL |
| **去重** | `crawlo:{p}:{s}:dedup:request` | SET | 请求去重 |
| | `crawlo:{p}:{s}:dedup:item` | SET | 数据项去重 |

> `{p}` = project_name, `{s}` = spider_name

---

## 详细说明

每个 Key 的数据结构、消息格式、所属模块、生命周期等详细信息，请阅读：

- [分布式架构设计文档 — 第 2 章：Redis Key 命名空间](../distributed_architecture.md#2-redis-key-命名空间)

该章节包含：
- 每个 Key 的完整字段说明
- Stream 消息格式（data / priority / enqueued_at / retry_count）
- Worker 注册表结构（JSON 示例）
- Key 清理策略（哪些 Key 在运行结束后保留，哪些必须清理）
