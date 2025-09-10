# 运行模式

Crawlo 支持三种运行模式，以适应不同的爬取场景：

## 1. 单机模式（默认）

单机模式是默认的执行模式，适用于开发和小规模爬取任务。在此模式下：

- 使用内存队列和过滤器
- 无需外部依赖
- 单节点操作
- 资源消耗较低

### 配置

```python
# settings.py
RUN_MODE = 'standalone'
QUEUE_TYPE = 'memory'
```

## 2. 分布式模式

分布式模式专为需要多个节点协同工作的大规模爬取任务而设计。在此模式下：

- 使用基于 Redis 的队列和过滤器
- 支持水平扩展
- 节点间共享任务队列
- 分布式去重

### 配置

```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 分布式调度器和过滤器
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
```

## 3. 自动模式

自动模式根据环境和配置自动检测最佳执行模式。它：

- 检查 Redis 可用性
- 如果 Redis 不可用则回退到单机模式
- 在模式间无缝切换

### 配置

```python
# settings.py
RUN_MODE = 'auto'
QUEUE_TYPE = 'auto'
```

## 模式选择指南

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 开发 | 单机模式 | 设置简单，无外部依赖 |
| 小规模爬取 | 单机模式 | 资源消耗较低 |
| 大规模爬取 | 分布式模式 | 水平扩展，性能更好 |
| 生产部署 | 分布式模式 | 容错性，共享状态 |
| 不确定环境 | 自动模式 | 自动检测和回退 |

## 在模式间切换

要在模式间切换，只需在 `settings.py` 文件中更改 `RUN_MODE` 设置并相应调整相关配置。Crawlo 将自动处理其余部分。