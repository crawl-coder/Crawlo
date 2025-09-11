# 内置管道

Crawlo提供了几个内置管道组件来处理常见的数据处理和存储任务。这些管道组件可以通过配置启用或禁用。

## 概述

内置管道为数据处理提供基本功能：

- 数据输出和存储
- 数据项去重
- 数据转换
- 验证和清理

## ConsolePipeline

将数据项输出到控制台用于调试和开发。

### 特性

- 简单的数据项显示
- JSON格式化
- 彩色输出
- 可配置的详细程度

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]

# 控制台管道设置
CONSOLE_PIPELINE_ENABLED = True
CONSOLE_PIPELINE_FORMAT = 'json'  # 或 'pretty'
```

## JsonPipeline

将数据项保存到JSON文件用于持久化存储。

### 特性

- JSON文件输出
- 可配置的文件命名
- 追加或覆盖模式
- 美化打印支持

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]

# JSON管道设置
JSON_PIPELINE_ENABLED = True
JSON_PIPELINE_FILENAME = 'items.json'
JSON_PIPELINE_MODE = 'append'  # 或 'overwrite'
JSON_PIPELINE_INDENT = 2
```

## CsvPipeline

将数据项保存到CSV文件用于电子表格兼容性。

### 特性

- CSV文件输出
- 自动字段检测
- 自定义字段映射
- 编码支持

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.csv_pipeline.CsvPipeline',
]

# CSV管道设置
CSV_PIPELINE_ENABLED = True
CSV_PIPELINE_FILENAME = 'items.csv'
CSV_PIPELINE_ENCODING = 'utf-8'
CSV_PIPELINE_DELIMITER = ','
```

## MemoryDedupPipeline

使用内存存储对数据项去重。

### 特性

- 快速的内存去重
- 可配置的指纹识别
- 内存高效存储
- 适用于独立模式

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
]

# 内存去重管道设置
MEMORY_DEDUP_ENABLED = True
MEMORY_DEDUP_FIELD = None  # 使用整个数据项，或指定字段
```

## RedisDedupPipeline

使用Redis存储进行分布式去重。

### 特性

- 分布式去重
- 持久化存储
- 可配置的TTL
- 节点间共享

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
]

# Redis去重管道设置
REDIS_DEDUP_ENABLED = True
REDIS_DEDUP_KEY = 'crawlo:dedup:items'
REDIS_DEDUP_TTL = 86400  # 24小时
REDIS_URL = 'redis://localhost:6379'
```

## BloomDedupPipeline

使用布隆过滤器进行内存高效去重。

### 特性

- 内存高效去重
- 概率数据结构
- 可配置的错误率
- 高性能

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.bloom_dedup_pipeline.BloomDedupPipeline',
]

# 布隆去重管道设置
BLOOM_DEDUP_ENABLED = True
BLOOM_DEDUP_CAPACITY = 1000000
BLOOM_DEDUP_ERROR_RATE = 0.001
```

## AsyncmyMySQLPipeline

使用asyncmy驱动将数据项存储到MySQL数据库。

### 特性

- 异步MySQL操作
- 连接池
- 批量插入
- 事务支持

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# MySQL管道设置
MYSQL_PIPELINE_ENABLED = True
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'database'
MYSQL_TABLE = 'items'
MYSQL_BATCH_SIZE = 100
```

## MongoPipeline

将数据项存储到MongoDB数据库。

### 特性

- 异步MongoDB操作
- 连接池
- 批量插入
- 灵活的文档结构

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',
]

# MongoDB管道设置
MONGO_PIPELINE_ENABLED = True
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'database'
MONGO_COLLECTION = 'items'
MONGO_BATCH_SIZE = 100
```

## DatabaseDedupPipeline

使用数据库存储对数据项去重。

### 特性

- 基于数据库的去重
- 多数据库支持
- 可配置的指纹识别
- 持久化存储

### 配置

```python
# 在settings.py中
PIPELINES = [
    'crawlo.pipelines.database_dedup_pipeline.DatabaseDedupPipeline',
]

# 数据库去重管道设置
DATABASE_DEDUP_ENABLED = True
DATABASE_DEDUP_TABLE = 'dedup_fingerprints'
DATABASE_DEDUP_FIELD = 'fingerprint'
```

## 使用示例

要启用多个内置管道：

```python
# 在settings.py中
PIPELINES = [
    # 去重（通常在最前面）
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    
    # 调试输出
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    
    # 文件存储
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    
    # 数据库存储（通常在最后）
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

## 管道顺序考虑

管道顺序对正确功能很重要：

1. **去重管道**通常应该在最前面
2. **处理管道**在中间
3. **存储管道**通常应该在最后

推荐的顺序示例：
```python
PIPELINES = [
    # 1. 去重
    'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    
    # 2. 数据处理
    'crawlo.pipelines.validation_pipeline.ValidationPipeline',
    'crawlo.pipelines.cleaning_pipeline.CleaningPipeline',
    
    # 3. 输出和存储
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

## 性能考虑

- 将轻量级管道放在前面以早期过滤
- 禁用未使用的管道以减少开销
- 对数据库管道使用批处理
- 监控管道处理时间以识别瓶颈
- 考虑为您的规模使用适当的去重方法