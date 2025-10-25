# Crawlo 配置模式完全指南

> 本文档详细介绍 Crawlo 框架的三种配置模式（Standalone、Distributed、Auto）及其运行机制。

## 快速导航

- [三种模式对比](#三种模式对比)
- [Standalone 模式](#standalone-模式)
- [Distributed 模式](#distributed-模式)
- [Auto 模式](#auto-模式)
- [配置更新机制](#配置更新机制)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 三种模式对比

### 核心区别一览表

| 配置项 | Standalone | Distributed | Auto |
|--------|-----------|-------------|------|
| **RUN_MODE** | `standalone` | `distributed` | `auto` |
| **QUEUE_TYPE（配置阶段）** | `memory` | `redis` | `auto` |
| **QUEUE_TYPE（运行时）** | 固定 `memory` | 必须 `redis` | 自动检测 |
| **Redis 检测** | ❌ 不检测 | ✅ 检测（必须可用） | ✅ 检测并回退 |
| **Redis 不可用时** | N/A | 🚫 **报错退出** | 降级到 Memory |
| **配置自动更新** | ❌ 否 | ❌ 否 | ✅ 是 |
| **过滤器** | 固定 Memory | 固定 Redis | Redis/Memory |
| **去重管道** | 固定 Memory | 固定 Redis | Redis/Memory |
| **适用场景** | 开发测试 | 多节点部署 | 生产环境 |
| **并发数默认值** | 8 | 16 | 12 |
| **最大爬虫数** | 1 | 10 | 1 |

### 关键发现

**⚠️ Distributed 模式的严格要求**：
- 🚫 必须使用 Redis，**不允许降级**到 Memory 模式
- ✅ 启动时会验证 Redis 连接
- 🚫 Redis 不可用时会**抛出 `RuntimeError` 并退出**
- 🛡️ 这确保了多节点部署时的一致性和数据安全性

**✨ Auto 模式的智能性**：
- 配置阶段不依赖 Redis
- 运行时才检测 Redis 可用性
- 根据检测结果动态选择最佳配置
- Redis 不可用时自动降级，保证系统可用性

---

## Standalone 模式

单机模式，最简单直接，适合开发测试和中小规模爬取。

### 配置示例

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.standalone(
    project_name='my_project',
    concurrency=8,
    download_delay=1.0
)

locals().update(config.to_dict())
```

### 生成的配置

```python
{
    'RUN_MODE': 'standalone',
    'QUEUE_TYPE': 'memory',  # 固定为内存队列
    'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
    'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    'PROJECT_NAME': 'my_project',
    'CONCURRENCY': 8,
    'MAX_RUNNING_SPIDERS': 1,
    'DOWNLOAD_DELAY': 1.0,
}
```

### 运行时行为

- ✅ **队列**: 始终使用 `MemoryQueue`
- ✅ **过滤器**: 始终使用 `MemoryFilter`
- ✅ **去重管道**: 始终使用 `MemoryDedupPipeline`
- ❌ **Redis 检测**: 不进行检测
- ❌ **配置更新**: 不会更新

### 适用场景

- 本地开发调试
- 学习框架特性
- 中小规模数据采集（< 10万条）
- 无需分布式部署

---

## Distributed 模式

分布式模式，严格要求 Redis 可用，适合多节点协同工作。

### 配置示例

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.distributed(
    project_name='my_distributed_project',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    redis_db=0,
    concurrency=16,
    download_delay=1.0
)

locals().update(config.to_dict())
```

### 生成的配置

```python
{
    'RUN_MODE': 'distributed',
    'QUEUE_TYPE': 'redis',  # 必须使用 Redis
    'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
    'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
    'REDIS_HOST': 'redis.example.com',
    'REDIS_PORT': 6379,
    'REDIS_PASSWORD': 'your_password',
    'REDIS_DB': 0,
    'REDIS_URL': 'redis://:your_password@redis.example.com:6379/0',
    'PROJECT_NAME': 'my_distributed_project',
    'SCHEDULER_QUEUE_NAME': 'crawlo:my_distributed_project:queue:requests',
    'CONCURRENCY': 16,
    'MAX_RUNNING_SPIDERS': 10,
    'DOWNLOAD_DELAY': 1.0,
}
```

### 运行时行为

- ✅ **Redis 检测**: 启动时强制检查 Redis 连接
- 🚫 **不允许降级**: Redis 不可用时抛出 `RuntimeError` 并退出
- ✅ **队列**: 必须使用 `RedisPriorityQueue`
- ✅ **过滤器**: 必须使用 `AioRedisFilter`
- ✅ **去重管道**: 必须使用 `RedisDedupPipeline`

### Redis 不可用时的错误信息

```bash
$ crawlo run my_spider

2025-10-25 22:00:00 - [queue_manager] - ERROR: Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
错误信息: Connection refused
Redis URL: redis://127.0.0.1:6379/0
请检查：
  1. Redis 服务是否正在运行
  2. Redis 连接配置是否正确
  3. 网络连接是否正常

RuntimeError: Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
```

### 为什么要严格要求 Redis？

1. **数据一致性**: 防止不同节点使用不同的队列类型
2. **去重有效性**: 确保多节点间的去重功能正常工作
3. **任务分配**: 防止任务被重复执行
4. **问题早发现**: 启动失败比运行时失败更容易发现和修复
5. **明确的意图**: 分布式模式就应该是分布式的，不应该静默降级

### 适用场景

- 多服务器协同采集
- 大规模数据采集（> 百万条）
- 需要严格保证分布式一致性
- 生产环境多节点部署

---

## Auto 模式

自动检测模式，智能选择最佳运行方式，推荐用于生产环境。

### 配置示例

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='my_auto_project',
    concurrency=12,
    download_delay=1.0
)

locals().update(config.to_dict())

# 可选：配置 Redis（如果可用会自动使用）
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_URL = 'redis://127.0.0.1:6379/0'
```

### 初始配置

```python
{
    'RUN_MODE': 'auto',
    'QUEUE_TYPE': 'auto',  # 运行时自动检测
    'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',  # 默认值
    'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    'PROJECT_NAME': 'my_auto_project',
    'CONCURRENCY': 12,
    'MAX_RUNNING_SPIDERS': 1,
    'DOWNLOAD_DELAY': 1.0,
}
```

### 运行时检测逻辑

```
Scheduler 初始化时
  └─ 检查 REDIS_URL 是否配置
      │
      ├─ [已配置 Redis] → 尝试连接
      │   │
      │   ├─ [连接成功] ✓
      │   │   ├─ 使用 RedisPriorityQueue
      │   │   ├─ 更新为 AioRedisFilter
      │   │   ├─ 更新为 RedisDedupPipeline
      │   │   └─ 配置自动更新
      │   │
      │   └─ [连接失败] ✗
      │       ├─ 使用 MemoryQueue
      │       ├─ 使用 MemoryFilter
      │       └─ 使用 MemoryDedupPipeline
      │
      └─ [未配置 Redis]
          ├─ 使用 MemoryQueue
          ├─ 使用 MemoryFilter
          └─ 使用 MemoryDedupPipeline
```

### 运行示例

**场景 1: Redis 可用**

```bash
$ crawlo run my_spider

2025-10-25 22:00:00 - [crawlo.framework] - INFO: Run mode: auto
2025-10-25 22:00:00 - [queue_manager] - DEBUG: Auto-detection: Redis available, using distributed queue
2025-10-25 22:00:00 - [scheduler] - INFO: enabled filters: 
  crawlo.filters.aioredis_filter.AioRedisFilter
```

**场景 2: Redis 不可用**

```bash
$ crawlo run my_spider

2025-10-25 22:00:00 - [crawlo.framework] - INFO: Run mode: auto
2025-10-25 22:00:00 - [queue_manager] - DEBUG: Auto-detection: Redis not configured, using memory queue
2025-10-25 22:00:00 - [scheduler] - INFO: enabled filters: 
  crawlo.filters.memory_filter.MemoryFilter
```

### 适用场景

- 生产环境单节点部署
- 需要容错性的场景
- 开发和生产环境共用配置
- 不确定 Redis 可用性的场景

---

## 配置更新机制

### 更新时机

配置更新发生在 Scheduler 初始化阶段：

```python
# crawlo/core/scheduler.py
async def open(self, spider):
    """打开调度器"""
    self.spider = spider
    
    # 初始化队列管理器（可能触发 Redis 检测）
    needs_config_update = await self.queue_manager.initialize()
    
    # 如果检测到 Redis 可用，更新相关配置
    if needs_config_update:
        updated_configs = self._check_filter_config()
        await self._process_filter_updates(needs_config_update, updated_configs)
```

### 更新内容

当从 Memory 切换到 Redis 时，会自动更新：

1. **FILTER_CLASS**: `MemoryFilter` → `AioRedisFilter`
2. **DEFAULT_DEDUP_PIPELINE**: `MemoryDedupPipeline` → `RedisDedupPipeline`
3. **PIPELINES**: 自动替换去重管道

### 哪些模式会触发配置更新？

- ✅ **Auto 模式**: 检测到 Redis 可用时会更新
- ❌ **Standalone 模式**: 不会更新
- ❌ **Distributed 模式**: 不会更新（配置已确定）

---

## 最佳实践

### 开发环境

```python
# 使用 standalone 模式，简单快速
config = CrawloConfig.standalone(
    project_name='dev_project',
    concurrency=4,
    download_delay=2.0
)
```

**优点**：
- 无需安装 Redis
- 启动速度快
- 调试方便

### 测试环境

```python
# 使用 auto 模式，可以测试两种场景
config = CrawloConfig.auto(
    project_name='test_project',
    concurrency=8,
    download_delay=1.5
)

# 可选：配置 Redis 用于测试分布式场景
REDIS_URL = 'redis://127.0.0.1:6379/1'  # 使用不同的 DB
```

**优点**：
- 可以测试 Redis 和 Memory 两种场景
- 配置灵活
- 接近生产环境

### 生产环境（单节点）

```python
# 使用 auto 模式，享受 Redis 性能提升
# 同时保证 Redis 故障时能够降级运行
config = CrawloConfig.auto(
    project_name='prod_project',
    concurrency=16,
    download_delay=1.0
)

# 配置 Redis
REDIS_HOST = 'redis.internal.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_password'
REDIS_DB = 0
```

**优点**：
- 自动使用 Redis 提升性能
- Redis 故障时自动降级
- 容错性好

### 生产环境（多节点）

```python
# 使用 distributed 模式，明确声明分布式部署
config = CrawloConfig.distributed(
    project_name='prod_distributed',
    redis_host='redis-cluster.internal.com',
    redis_port=6379,
    redis_password='your_password',
    redis_db=0,
    concurrency=32,
    download_delay=0.5
)
```

**优点**：
- 严格保证分布式一致性
- 多节点协同工作
- 问题早发现
- 数据安全性高

---

## 常见问题

### Q1: Auto 模式下，如何确保一定使用 Redis？

**A**: Auto 模式会优先使用 Redis（如果可用），但如果需要确保使用 Redis，建议：

1. 使用 `distributed` 模式（Redis 不可用时会报错）
2. 在启动前检查 Redis 连接（`crawlo run` 会自动检查）
3. 监控日志中的 "Queue type: redis" 信息

### Q2: Distributed 模式下 Redis 不可用会怎样？

**A**: Distributed 模式下 Redis 必须可用：
- 🚫 不会降级到 Memory 模式
- 🚫 会抛出 `RuntimeError` 并退出
- ✅ 错误信息会提示具体的检查步骤
- 🎯 这确保了多节点部署时的一致性

### Q3: 配置更新会影响哪些组件？

**A**: 配置更新主要影响：
1. **过滤器（Filter）**: MemoryFilter ↔ AioRedisFilter
2. **去重管道（Dedup Pipeline）**: MemoryDedupPipeline ↔ RedisDedupPipeline
3. **其他使用这些配置的组件**

队列（Queue）本身在初始化时就已经确定，不会在运行中切换。

### Q4: 如何在代码中判断当前使用的是哪种模式？

**A**: 可以通过以下方式判断：

```python
# 在爬虫中
run_mode = self.crawler.settings.get('RUN_MODE')
queue_type = self.crawler.settings.get('QUEUE_TYPE')

# 通过队列管理器获取实际使用的类型
status = self.crawler.engine.scheduler.queue_manager.get_status()
actual_queue_type = status['type']  # 'memory' 或 'redis'
print(f"实际队列类型: {actual_queue_type}")
print(f"健康状态: {status['health']}")
```

### Q5: 为什么 Distributed 模式要严格要求 Redis 可用？

**A**: 严格要求的原因：
1. **数据一致性**: 防止不同节点使用不同的队列类型
2. **去重有效性**: 确保多节点间的去重功能正常工作
3. **任务分配**: 防止任务被重复执行
4. **问题早发现**: 启动失败比运行时失败更容易发现和修复
5. **明确的意图**: 分布式模式就应该是分布式的，不应该静默降级

如果需要容错性，应该使用 `auto` 模式而非 `distributed` 模式。

---

## 快速命令参考

```bash
# 查看爬虫列表（会显示运行模式）
crawlo list

# 运行爬虫（会自动检测 Redis）
crawlo run my_spider

# 查看实际使用的队列类型（观察日志）
crawlo run my_spider | grep "Queue type"
```

---

## 推荐使用场景总结

| 场景 | 推荐模式 | 理由 |
|------|---------|------|
| 本地开发 | `standalone` | 简单快速，无需 Redis |
| CI/CD 测试 | `auto` | 可测试两种场景 |
| 生产单节点 | `auto` | 智能选择，容错性好 |
| 生产多节点 | `distributed` | 严格保证一致性 |

---

## 相关文档

- [分布式爬虫教程](./distributed_crawling.md)
- [第一个爬虫](./first_spider.md)

---

**文档版本**: 1.0  
**更新时间**: 2025-10-25  
**适用版本**: Crawlo 1.4.7+
