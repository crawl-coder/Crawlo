# 去重配置说明

Crawlo框架支持根据运行模式自动选择合适的去重管道。本文档详细说明了如何配置和使用不同模式下的去重功能。

## 1. 默认配置行为

框架会根据 [RUN_MODE](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py#L56-L56) 设置自动选择默认的去重管道：

- **单机模式** (`RUN_MODE = 'standalone'`): 默认使用 [MemoryDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/memory_dedup_pipeline.py#L25-L115)
- **分布式模式** (`RUN_MODE = 'distributed'`): 默认使用 [RedisDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/redis_dedup_pipeline.py#L33-L162)

## 2. 配置文件说明

在 [crawlo/settings/default_settings.py](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py) 中，我们添加了以下配置逻辑：

```python
# 根据运行模式自动选择去重管道
# 单机模式默认使用内存去重管道
# 分布式模式默认使用Redis去重管道
if RUN_MODE == 'distributed':
    # 分布式模式下默认使用Redis去重管道
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.RedisDedupPipeline'
else:
    # 单机模式下默认使用内存去重管道
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.MemoryDedupPipeline'

# ...

# 根据运行模式自动配置默认去重管道
if RUN_MODE == 'distributed':
    # 分布式模式下添加Redis去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
else:
    # 单机模式下添加内存去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
```

## 3. 自定义配置

### 3.1 修改运行模式

在项目配置文件中设置运行模式：

```python
# settings.py
RUN_MODE = 'distributed'  # 或 'standalone'
```

### 3.2 手动指定去重管道

如果需要使用特定的去重管道，可以直接在 [PIPELINES](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py#L152-L156) 配置中指定：

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # 使用Bloom Filter去重
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### 3.3 配置去重管道参数

不同去重管道支持不同的配置参数：

#### MemoryDedupPipeline
```python
# settings.py
LOG_LEVEL = 'INFO'  # 日志级别
```

#### RedisDedupPipeline
```python
# settings.py
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_DEDUP_KEY = 'crawlo:item_fingerprints'
LOG_LEVEL = 'INFO'
```

#### BloomDedupPipeline
```python
# settings.py
BLOOM_FILTER_CAPACITY = 1000000
BLOOM_FILTER_ERROR_RATE = 0.001
LOG_LEVEL = 'INFO'
```

#### DatabaseDedupPipeline
```python
# settings.py
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'crawlo'
DB_DEDUP_TABLE = 'item_fingerprints'
LOG_LEVEL = 'INFO'
```

## 4. 运行模式切换示例

### 4.1 单机模式运行
```python
# settings.py
RUN_MODE = 'standalone'
# 自动使用 MemoryDedupPipeline
```

### 4.2 分布式模式运行
```python
# settings.py
RUN_MODE = 'distributed'
# 自动使用 RedisDedupPipeline
```

### 4.3 自定义去重管道
```python
# settings.py
RUN_MODE = 'standalone'  # 或 'distributed'
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # 覆盖默认去重管道
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

## 5. 最佳实践

1. **单机小规模爬虫**: 使用默认配置，自动选择内存去重
2. **分布式爬虫**: 设置 `RUN_MODE = 'distributed'`，自动使用Redis去重
3. **大规模数据采集**: 考虑使用Bloom Filter去重以节省内存
4. **长期运行任务**: 使用数据库去重以支持断点续爬

通过这种自动化的配置方式，用户可以更方便地在不同场景下使用最适合的去重方案，而无需手动调整复杂的配置。