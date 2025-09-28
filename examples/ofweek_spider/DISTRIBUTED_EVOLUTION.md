# 从单机爬虫到分布式爬虫的演进之路

本文档详细说明了如何将一个单机爬虫逐步演进为分布式爬虫，以 OfweekSpider 为例。

## 演进阶段概述

```
阶段1: 基础单机模式
   ↓
阶段2: 单机模式增强
   ↓
阶段3: 分布式模式
   ↓
阶段4: 分布式模式优化
```

## 阶段1：基础单机模式

### 特点
- 使用内存队列和内存去重过滤器
- 适合开发测试和小规模数据采集
- 配置简单，无需额外依赖

### 配置示例
```python
# settings_standalone.py
PROJECT_NAME = 'ofweek_spider_standalone'
RUN_MODE = 'standalone'
CONCURRENCY = 4
DOWNLOAD_DELAY = 1.0
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
QUEUE_TYPE = 'memory'
```

### 优点
1. 部署简单，无需额外服务
2. 开发调试方便
3. 资源消耗少

### 缺点
1. 无法多节点协同
2. 数据量大时内存占用高
3. 无法持久化任务状态

## 阶段2：单机模式增强

### 改进点
- 增加持久化去重机制
- 优化内存使用
- 处理大数据量

### 实现方式
1. 使用文件存储代替内存去重
2. 实现断点续传功能
3. 优化数据存储结构

### 配置示例
```python
# 可以在 settings.py 中添加
FILTER_CLASS = 'crawlo.filters.file_filter.FileFilter'  # 使用文件去重
REQUEST_DIR = './requests/'  # 请求存储目录
```

### 优点
1. 支持断点续传
2. 减少内存占用
3. 数据持久化

### 缺点
1. 仍然无法多节点协同
2. 文件系统I/O可能成为瓶颈

## 阶段3：分布式模式

### 改进点
- 使用 Redis 队列和去重过滤器
- 支持多节点协同工作
- 需要 Redis 环境支持

### 实现方式
1. 配置 Redis 连接
2. 更改队列类型为 Redis
3. 更改过滤器为 Redis 过滤器

### 配置示例
```python
# settings_distributed.py
PROJECT_NAME = 'ofweek_spider_distributed'
RUN_MODE = 'distributed'
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
QUEUE_TYPE = 'redis'
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'
```

### 优点
1. 支持多节点协同
2. 高并发处理能力
3. 任务状态持久化
4. 去重信息共享

### 缺点
1. 需要维护 Redis 服务
2. 网络延迟可能影响性能
3. 配置复杂度增加

## 阶段4：分布式模式优化

### 改进点
- 配置 Redis 连接池
- 优化去重性能
- 增加监控和故障恢复机制

### 实现方式
1. 配置 Redis 连接池参数
2. 优化 Redis key 设计
3. 增加健康检查和重试机制

### 配置示例
```python
# settings_distributed.py (优化版)
# Redis 连接池配置
REDIS_CONNECTION_POOL_SIZE = 20
REDIS_HEALTH_CHECK_INTERVAL = 30

# 队列优化
SCHEDULER_MAX_QUEUE_SIZE = 10000
QUEUE_TIMEOUT = 600

# 监控配置
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.health_check.HealthCheckExtension',
]
```

### 优点
1. 更高的性能和稳定性
2. 更好的资源利用
3. 完善的监控和故障恢复

### 缺点
1. 配置和维护复杂度进一步增加
2. 需要专业的运维知识

## 模式切换方法

### 1. 修改配置文件
```bash
# 切换到单机模式
cp crawlo_standalone.cfg crawlo.cfg

# 切换到分布式模式
cp crawlo_distributed.cfg crawlo.cfg
```

### 2. 使用环境变量
```bash
# 启用分布式模式
export CRAWLO_RUN_MODE=distributed
export REDIS_HOST=your.redis.host
export REDIS_PORT=6379
```

### 3. 使用运行脚本
```bash
# 运行单机模式
python run_standalone.py

# 运行分布式模式
# 使用 crawlo run 命令运行分布式模式
crawlo run of_week
```

## 复杂性分析

### 配置复杂性
| 模式 | 配置文件数量 | 配置项数量 | 依赖服务 |
|------|-------------|-----------|----------|
| 单机模式 | 1 | 10-20 | 无 |
| 分布式模式 | 2-3 | 30-50 | Redis |

### 运维复杂性
| 模式 | 部署难度 | 监控需求 | 故障排查难度 |
|------|---------|---------|-------------|
| 单机模式 | 简单 | 低 | 简单 |
| 分布式模式 | 中等 | 高 | 中等 |

### 性能对比
| 指标 | 单机模式 | 分布式模式 |
|------|---------|-----------|
| 最大并发数 | 10-20 | 100+ |
| 内存占用 | 低 | 中等 |
| 数据去重 | 内存级 | Redis级 |
| 扩展性 | 差 | 好 |

## 注意事项

1. **数据一致性**：分布式模式下需要考虑数据一致性问题
2. **网络延迟**：Redis 网络延迟可能影响爬虫性能
3. **资源竞争**：多节点可能竞争同一资源
4. **故障恢复**：需要设计合理的故障恢复机制

## 最佳实践

1. **渐进式演进**：按照阶段逐步演进，不要一步到位
2. **充分测试**：每一步演进后都要充分测试
3. **监控告警**：分布式模式下必须建立完善的监控告警机制
4. **文档记录**：详细记录配置变更和问题解决方案