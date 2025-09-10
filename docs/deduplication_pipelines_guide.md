# 数据去重管道使用指南

Crawlo框架提供了多种数据去重管道，适用于不同的使用场景和需求。本文档将详细介绍每种去重管道的特点、配置方法和使用建议。

## 1. 内存去重管道 (MemoryDedupPipeline)

### 特点
- **高性能**: 使用内存集合进行快速查找
- **简单易用**: 无需外部依赖
- **轻量级**: 适用于小规模数据采集
- **低延迟**: 内存操作无网络开销

### 适用场景
- 单机爬虫
- 小规模数据采集（万级以下）
- 临时性数据采集任务

### 配置方法
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MemoryDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### 限制
- 重启后去重状态丢失
- 内存占用随数据量增长
- 不支持分布式环境

## 2. Redis去重管道 (RedisDedupPipeline)

### 特点
- **分布式支持**: 多节点共享去重数据
- **高性能**: 使用Redis集合进行快速查找
- **可配置**: 支持自定义Redis连接参数
- **容错设计**: 网络异常时不会丢失数据

### 适用场景
- 分布式爬虫系统
- 中大规模数据采集
- 需要持久化去重状态的场景

### 配置方法
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Redis配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_DEDUP_KEY = 'crawlo:item_fingerprints'
```

### 限制
- 需要部署和维护Redis服务
- 网络延迟影响性能

## 3. Bloom Filter去重管道 (BloomDedupPipeline)

### 特点
- **内存效率高**: 相比传统集合节省大量内存
- **高性能**: 快速的插入和查找操作
- **可扩展**: 支持自定义容量和误判率
- **适用性广**: 特别适合大规模数据采集

### 适用场景
- 大规模数据采集（百万级以上）
- 内存资源受限的环境
- 可以接受少量误判的场景

### 配置方法
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Bloom Filter配置
BLOOM_FILTER_CAPACITY = 1000000
BLOOM_FILTER_ERROR_RATE = 0.001
```

### 注意事项
- Bloom Filter有误判率，可能会错误地丢弃一些未见过的数据项
- 需要安装`pybloom_live`库：`pip install pybloom-live`

## 4. 数据库去重管道 (DatabaseDedupPipeline)

### 特点
- **持久化存储**: 重启爬虫后仍能保持去重状态
- **可靠性高**: 数据库事务保证一致性
- **适用性广**: 支持多种数据库后端
- **可扩展**: 支持自定义表结构和字段

### 适用场景
- 需要长期运行的爬虫
- 断点续爬需求
- 对数据完整性要求极高的场景

### 配置方法
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.DatabaseDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'crawlo'
DB_DEDUP_TABLE = 'item_fingerprints'
```

### 限制
- 数据库I/O操作影响性能
- 需要额外的数据库资源

## 5. 选择建议

根据不同的需求场景，选择合适的去重管道：

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 小规模单机爬虫 | MemoryDedupPipeline | 简单高效，无外部依赖 |
| 分布式爬虫 | RedisDedupPipeline | 支持多节点共享状态 |
| 大规模数据采集 | BloomDedupPipeline | 内存占用少，性能好 |
| 长期运行任务 | DatabaseDedupPipeline | 支持断点续爬 |

## 6. 性能对比

| 方案 | 内存占用 | 性能 | 持久化 | 分布式支持 | 误判率 |
|------|----------|------|--------|------------|--------|
| 内存 | 高 | 最高 | 否 | 否 | 无 |
| Redis | 低 | 高 | 是 | 是 | 无 |
| Bloom Filter | 最低 | 高 | 否 | 否 | 有 |
| 数据库 | 低 | 中 | 是 | 否 | 无 |

## 7. 使用示例

### 基本使用
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### 组合使用
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # 初步过滤
    'crawlo.pipelines.RedisDedupPipeline': 200,  # 精确去重
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### 自定义配置
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MemoryDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# 自定义内存去重管道配置
DEDUP_LOG_LEVEL = 'DEBUG'
```

通过合理选择和配置去重管道，可以有效提高爬虫的数据质量和采集效率。