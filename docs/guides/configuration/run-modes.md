# 运行模式详解

Crawlo 提供三种运行模式，每种模式适用于不同的场景。正确选择模式对爬虫的性能和可靠性至关重要。

---

## 📊 三种模式对比

| 特性 | Standalone | Distributed | Auto ⭐ |
|------|-----------|-------------|---------|
| **RUN_MODE** | `standalone` | `distributed` | `auto` |
| **队列类型** | MemoryQueue | RedisPriorityQueue | 自动检测 |
| **过滤器** | MemoryFilter | AioRedisFilter | 自动选择 |
| **去重管道** | MemoryDedupPipeline | RedisDedupPipeline | 自动选择 |
| **Redis 要求** | ❌ 不需要 | ✅ 必需 | ⚠️ 可选 |
| **Redis 不可用** | N/A | 🚫 报错退出 | ✅ 降级到内存 |
| **配置自动更新** | ❌ 否 | ❌ 否 | ✅ 是 |
| **并发数默认值** | 8 | 16 | 12 |
| **适用场景** | 开发测试 | 多节点部署 | 生产环境 |
| **推荐指数** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 1. Standalone 模式（单机模式）

### 适用场景

- ✅ 本地开发调试
- ✅ 学习框架特性
- ✅ 中小规模数据采集（< 10万条）
- ✅ 单机运行的简单爬虫
- ✅ 不想安装 Redis

### 配置方式

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8,
    download_delay=1.0
)

locals().update(config.to_dict())
```

### 运行机制

**固定组件**：
- 队列：`MemoryQueue`（内存队列）
- 过滤器：`MemoryFilter`（内存过滤器）
- 去重：`MemoryDedupPipeline`（内存去重）

**特点**：
- ❌ 不进行 Redis 检测
- ❌ 配置不会自动更新
- ❌ 重启后队列数据丢失
- ❌ 不支持分布式部署

### 优势

- ✅ 无需任何外部依赖
- ✅ 启动速度快
- ✅ 适合快速开发调试
- ✅ 配置简单

### 限制

- ❌ 不支持分布式部署
- ❌ 重启后数据丢失
- ❌ 不适合大规模数据采集
- ❌ 内存占用随队列增长

### 示例配置

```python
# settings.py
RUN_MODE = 'standalone'

# 队列配置
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000  # 队列最大大小

# 过滤器配置
MEMORY_FILTER_MAX_SIZE = 100000  # 过滤器最大大小

# 并发控制
CONCURRENCY = 8
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True
```

---

## 2. Distributed 模式（分布式模式）

### 适用场景

- ✅ 多节点协同爬取
- ✅ 大规模数据采集（> 100万条）
- ✅ 需要断点续爬
- ✅ 生产环境部署
- ✅ 需要任务持久化

### 配置方式

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    redis_db=0,
    concurrency=16,
    download_delay=0.5
)

locals().update(config.to_dict())
```

### 运行机制

**固定组件**：
- 队列：`RedisPriorityQueue`（Redis 优先队列）
- 过滤器：`AioRedisFilter`（Redis 过滤器）
- 去重：`RedisDedupPipeline`（Redis 去重）

**特点**：
- ✅ 强制检查 Redis 连接
- ✅ 任务持久化（重启不丢失）
- ✅ 支持多节点协同
- 🚫 **Redis 不可用时抛出 `RuntimeError` 并退出**

### 为什么严格要求 Redis？

1. **数据一致性**：防止不同节点使用不同的队列类型
2. **去重有效性**：确保多节点间的去重功能正常工作
3. **任务分配**：防止任务被重复执行
4. **状态同步**：共享爬虫运行状态

### 优势

- ✅ 支持分布式部署
- ✅ 任务持久化
- ✅ 全局去重
- ✅ 支持断点续爬

### 限制

- ❌ 必须安装 Redis
- ❌ Redis 故障时爬虫退出
- ❌ 配置复杂度较高

### 示例配置

```python
# settings.py
RUN_MODE = 'distributed'

# Redis 配置
REDIS_HOST = 'redis.example.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_password'
REDIS_DB = 0

# 队列配置
REDIS_SCHEDULER_MAX_QUEUE_SIZE = 20000  # Redis 队列最大大小

# 并发控制
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5

# 断点续爬
CHECKPOINT_ENABLED = True
CHECKPOINT_INTERVAL = 300  # 每 5 分钟保存一次
```

### 多节点部署示例

**节点 1**：
```bash
# 启动第一个爬虫实例
crawlo run myspider
```

**节点 2**：
```bash
# 启动第二个爬虫实例（共享 Redis）
crawlo run myspider
```

两个节点会自动协同工作，不会重复爬取相同的 URL。

---

## 3. Auto 模式（智能检测模式）⭐ 推荐

### 适用场景

- ✅ **生产环境部署（首选）**
- ✅ 需要在多种环境运行的项目
- ✅ 希望系统具备容错能力
- ✅ 不确定是否有 Redis
- ✅ 开发测试和生产使用同一份代码

### 配置方式

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='myproject',
    redis_host='localhost',  # 可选，如果有的话
    redis_port=6379,
    concurrency=12,
    download_delay=1.0
)

locals().update(config.to_dict())
```

### 运行机制

**智能检测流程**：

```
1. 配置阶段
   ↓
   不依赖 Redis，正常初始化
   ↓
2. 运行时检测
   ↓
   尝试连接 Redis
   ↓
   ├─ Redis 可用
   │   ↓
   │   使用 RedisPriorityQueue + AioRedisFilter
   │   ↓
   │   性能最佳，支持分布式
   │
   └─ Redis 不可用
       ↓
       降级到 MemoryQueue + MemoryFilter
       ↓
       性能稍低，单机运行
```

**自动更新的配置**：
- `QUEUE_TYPE`: `memory` 或 `redis`
- `FILTER_CLASS`: `MemoryFilter` 或 `AioRedisFilter`
- `DEFAULT_DEDUP_PIPELINE`: `MemoryDedupPipeline` 或 `RedisDedupPipeline`

### 优势

- ✅ **开发环境无需配置 Redis，直接启动**
- ✅ **生产环境 Redis 故障时自动降级，保证系统可用性**
- ✅ **同一份代码可在不同环境运行，无需修改配置**
- ✅ **最佳的灵活性和可靠性**
- ✅ 有 Redis 时支持分布式
- ✅ 无 Redis 时降级到单机

### 限制

- ⚠️ Redis 不可用时失去分布式能力
- ⚠️ 运行时才知道使用哪种模式

### 示例配置

```python
# settings.py
RUN_MODE = 'auto'

# Redis 配置（可选）
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0

# 队列配置（两种模式都适用）
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 8000  # 内存队列
REDIS_SCHEDULER_MAX_QUEUE_SIZE = 20000  # Redis 队列

# 并发控制
CONCURRENCY = 12
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True

# 背压系统（推荐启用）
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.8
```

### 检测逻辑

```python
# Crawlo 内部实现（伪代码）
def detect_and_configure():
    try:
        # 尝试连接 Redis
        redis_client = await aioredis.create_redis_pool(
            f"redis://{REDIS_HOST}:{REDIS_PORT}"
        )
        await redis_client.ping()
        
        # Redis 可用，使用分布式组件
        return {
            'QUEUE_TYPE': 'redis',
            'FILTER_CLASS': 'AioRedisFilter',
            'DEFAULT_DEDUP_PIPELINE': 'RedisDedupPipeline',
        }
    except Exception:
        # Redis 不可用，降级到内存组件
        return {
            'QUEUE_TYPE': 'memory',
            'FILTER_CLASS': 'MemoryFilter',
            'DEFAULT_DEDUP_PIPELINE': 'MemoryDedupPipeline',
        }
```

---

## 🎯 如何选择？

### 决策树

```
你的场景是什么？
│
├─ 本地开发调试
│   └─> 使用 Standalone 模式
│
├─ 多节点分布式部署
│   └─> 使用 Distributed 模式
│
└─ 生产环境（或不确定）
    └─> 使用 Auto 模式 ⭐
```

### 快速选择表

| 你的情况 | 推荐模式 |
|---------|---------|
| 第一次学习 Crawlo | Standalone |
| 本地开发测试 | Standalone |
| 有 Redis，要分布式 | Distributed |
| 有 Redis，生产环境 | Auto ⭐ |
| 不确定有没有 Redis | Auto ⭐ |
| 需要容错能力 | Auto ⭐ |
| 开发和生产用同一份代码 | Auto ⭐ |

---

## 💡 最佳实践

### 1. 开发环境使用 Standalone

```python
# settings_dev.py
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=4,  # 低并发
    download_delay=1.0
)
```

### 2. 生产环境使用 Auto

```python
# settings_prod.py
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=16,  # 高并发
    download_delay=0.5
)
```

### 3. 使用环境变量切换

```python
import os

RUN_MODE = os.getenv('CRAWLO_RUN_MODE', 'auto')

if RUN_MODE == 'standalone':
    config = CrawloConfig.standalone(...)
elif RUN_MODE == 'distributed':
    config = CrawloConfig.distributed(...)
else:  # auto
    config = CrawloConfig.auto(...)
```

运行方式：
```bash
# 开发环境
CRAWLO_RUN_MODE=standalone crawlo run myspider

# 生产环境
CRAWLO_RUN_MODE=auto crawlo run myspider
```

---

## 🔍 验证当前模式

在爬虫中查看当前使用的模式：

```python
class MySpider(Spider):
    async def parse(self, response):
        # 查看队列类型
        queue_type = self.crawler.settings.get('QUEUE_TYPE')
        self.logger.info(f"当前队列类型: {queue_type}")
        
        # 查看运行模式
        run_mode = self.crawler.settings.get('RUN_MODE')
        self.logger.info(f"当前运行模式: {run_mode}")
```

---

## ❓ 常见问题

### Q: 可以在运行中切换模式吗？

A: **不可以**。模式在启动时确定，运行中不能切换。需要重启爬虫。

### Q: Auto 模式检测到 Redis 后，Redis 突然故障怎么办？

A: **不会自动降级**。一旦确定使用 Redis，就会持续使用。如果 Redis 故障，会抛出异常。

### Q: Standalone 模式可以连接 Redis 吗？

A: **可以**。即使使用 Standalone 模式，仍然可以配置 Redis 用于数据存储（如 MongoDB Pipeline），只是队列和过滤器使用内存。

### Q: 哪种模式性能最好？

A: **Distributed 模式**（有 Redis 时）性能最好，因为：
- Redis 队列支持优先级
- 全局去重更高效
- 支持分布式扩展

---

**需要了解配置详情？** 查看 [配置指南](index.md)。
