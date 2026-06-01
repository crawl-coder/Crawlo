# 从单机到 10 台机器：Crawlo 分布式爬虫实战

> 一台机器不够？加机器。代码？不用改。

---

## 什么时候需要分布式？

| 场景 | 单机够吗 | 解决方案 |
|------|---------|---------|
| 爬 1 万页 | ✅ 够 | standalone |
| 爬 100 万页 | ⚠️ 勉强 | auto（Redis 加速） |
| 爬 1 亿页 | ❌ 不够 | distributed |
| 要求 24 小时内完成 | ❌ 不够 | distributed |
| 数据不能丢 | ❌ | distributed |

---

## 三种部署模式

Crawlo 提供三种模式，**代码零修改，只改配置**：

### 模式一：单机开发

```python
# settings.py
from crawlo.config import CrawloConfig

settings = CrawloConfig.standalone()
```

- 内存队列，无需 Redis
- 适合开发和调试

### 模式二：多机协作

```python
settings = CrawloConfig.auto()
```
- 自动检测 Redis 可用性
- Redis 队列 + 去重
- 多台机器竞争消费（BZPOPMIN）
- 适合多机并发，可接受极少量任务丢失

### 模式三：生产级分布式

```python
settings = CrawloConfig.distributed(
    redis_host='10.0.0.1',
    redis_port=6379,
    worker_concurrency=32,
)
```

- Redis Stream + Consumer Group
- ACK 语义 + 故障转移 + 死信队列
- 心跳守护 + 动态配置
- 适合生产环境，任务可靠性高

---

## 架构图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Worker 1   │     │   Worker 2   │     │   Worker 3   │
│  (32 并发)    │     │  (32 并发)    │     │  (16 并发)    │
│              │     │              │     │              │
│ Engine       │     │ Engine       │     │ Engine       │
│ Scheduler    │     │ Scheduler    │     │ Scheduler    │
│ Downloader   │     │ Downloader   │     │ Downloader   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │     ┌──────────────▼──────────────────────▼──┐
       │     │              Redis                      │
       └────►│  Stream (任务队列)                       │
             │  HASH   (Worker 注册表)                  │
             │  ZSET   (心跳时间戳)                     │
             │  SET    (去重过滤器)                     │
             │  HASH   (全局统计)                       │
             │  Pub/Sub (控制消息)                      │
             └────────────────────────────────────────┘
```

---

## 实战部署

### 1. 准备 Redis

```bash
# Docker 方式
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 验证
redis-cli ping  # PONG
```

### 2. 配置爬虫

```python
# settings.py
from crawlo.config import CrawloConfig

settings = CrawloConfig.distributed(
    redis_host='10.0.0.1',    # Redis 地址
    redis_port=6379,
    redis_password='your_password',
    worker_concurrency=32,    # 每个 Worker 的并发数
)
```

### 3. 在多台机器上启动

```bash
# 机器 A（4 核 8G）
crawlo run myspider

# 机器 B（8 核 16G）
crawlo run myspider

# 机器 C（2 核 4G，笔记本也行）
crawlo run myspider
```

**每个 Worker 自动：**
- 向 Redis 注册（Worker ID = hostname-pid-uuid）
- 开始心跳（15 秒间隔 + ±20% jitter）
- 从 Redis Stream 拉取任务
- 完成后 XACK 确认

---

## 核心机制详解

### Worker 心跳

```
Worker 1: ♥ 15.2s  (正常运行)
Worker 2: ♥ 14.8s  (正常运行)
Worker 3: ♥ 16.1s  (正常运行)
Worker 4: ♥ 75.3s  ⚠️ 心跳超时！
```

心跳超时 → 进入 suspect 状态 → 30 秒后二次确认 → 正式判定故障

### 故障转移（两阶段确认）

```
                ┌─────────────┐
                │ Worker 4 崩溃 │
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ 第一阶段：suspect │ ← 心跳超时，标记为疑似故障
                └──────┬──────┘
                       │ 30 秒后
                ┌──────▼──────┐
                │ 第二阶段：confirm │ ← 仍未心跳，确认为故障
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ 任务回收      │ ← XCLAIM 转移未完成任务
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ 其他 Worker  │ ← 接管任务，继续执行
                └─────────────┘
```

**为什么两阶段？** 防止网络抖动导致误回收——短暂断连不会导致任务被重复执行。

### 死信队列

超过最大投递次数（默认 3 次）的任务进入死信队列：

```
Task → 投递 1 次 → Worker 崩溃 → 回收
     → 投递 2 次 → Worker 崩溃 → 回收
     → 投递 3 次 → Worker 崩溃 → 进入死信队列
```

手动重试死信：

```python
# 在 Redis CLI 中
XLEN crawlo:stream:dead_letter   # 查看死信数量

# 或在代码中
from crawlo.cluster.failover import FailoverManager
await failover.retry_dead_letters()
```

### Leader 协调退出

当所有任务完成时，Crawlo 自动检测并协调退出：

1. SETNX 选举 Leader
2. Leader 检测：种子全部生成 + 队列为空 + 所有 Worker 空闲
3. 二次确认（2 秒后再检查）
4. 广播 shutdown 消息
5. 所有 Worker 优雅退出

---

## 动态配置

运行时调整集群行为，无需重启：

```python
from crawlo.cluster.dynamic_config import DynamicConfig

# 暂停爬虫
await dynamic_config.pause()

# 恢复爬虫
await dynamic_config.resume()

# 动态调整限速
await dynamic_config.set_rate_limit(10)  # 10 req/s

# 动态添加种子 URL
await dynamic_config.add_seed_url('https://example.com/new-page')

# 动态调整并发
await dynamic_config.set_concurrency(64)
```

---

## 监控

```python
from crawlo.cluster.monitor import ClusterMonitor

# 集群状态总览
status = await monitor.get_cluster_status()
# {
#   'workers': {'total': 3, 'active': 3, 'idle': 1},
#   'queue': {'pending': 1200, 'processing': 45},
#   'stats': {'completed': 50000, 'failed': 3},
#   'eta': '2 hours 15 minutes'
# }
```

---

## 与 Scrapy-Redis 对比

| 特性 | Crawlo 分布式 | Scrapy-Redis |
|------|-------------|--------------|
| 维护状态 | 活跃开发 | 社区维护 |
| ACK 语义 | ✅ XACK 确认 | ⚠️ 无 |
| 故障转移 | ✅ 两阶段确认 | ⚠️ 无 |
| 死信队列 | ✅ 自动 + 手动重试 | ⚠️ 无 |
| 心跳守护 | ✅ 15s + jitter | ⚠️ 无 |
| 动态配置 | ✅ 运行时调整 | ⚠️ 无 |
| Leader 选举 | ✅ SETNX | ⚠️ 无 |
| 优雅退出 | ✅ Leader 协调 | ⚠️ 无 |

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
