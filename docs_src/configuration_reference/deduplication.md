# Deduplication Configuration

Crawlo framework supports automatic selection of appropriate deduplication pipelines based on the running mode. This document details how to configure and use deduplication features in different modes.

## 1. Default Configuration Behavior

The framework automatically selects the default deduplication pipeline based on the [RUN_MODE](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py#L56-L56) setting:

- **Standalone Mode** (`RUN_MODE = 'standalone'`): Defaults to [MemoryDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/memory_dedup_pipeline.py#L25-L115)
- **Distributed Mode** (`RUN_MODE = 'distributed'`): Defaults to [RedisDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/redis_dedup_pipeline.py#L33-L162)

## 2. Configuration File Explanation

In [crawlo/settings/default_settings.py](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py), we've added the following configuration logic:

```python
# Automatically select deduplication pipeline based on running mode
# Standalone mode defaults to memory deduplication pipeline
# Distributed mode defaults to Redis deduplication pipeline
if RUN_MODE == 'distributed':
    # Distributed mode defaults to Redis deduplication pipeline
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.RedisDedupPipeline'
else:
    # Standalone mode defaults to memory deduplication pipeline
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.MemoryDedupPipeline'

# ...

# Automatically configure default deduplication pipeline based on running mode
if RUN_MODE == 'distributed':
    # Add Redis deduplication pipeline in distributed mode
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
else:
    # Add memory deduplication pipeline in standalone mode
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
```

## 3. Custom Configuration

### 3.1 Changing Running Mode

Set the running mode in the project configuration file:

```python
# settings.py
RUN_MODE = 'distributed'  # or 'standalone'
```

### 3.2 Manually Specifying Deduplication Pipeline

If you need to use a specific deduplication pipeline, you can directly specify it in the [PIPELINES](file://d:/dowell/projects/Crawlo/crawlo/settings/default_settings.py#L152-L156) configuration:

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # Use Bloom Filter deduplication
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### 3.3 Configuring Deduplication Pipeline Parameters

Different deduplication pipelines support different configuration parameters:

#### MemoryDedupPipeline
```python
# settings.py
LOG_LEVEL = 'INFO'  # Log level
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

## 4. Running Mode Switching Examples

### 4.1 Standalone Mode Running
```python
# settings.py
RUN_MODE = 'standalone'
# Automatically uses MemoryDedupPipeline
```

### 4.2 Distributed Mode Running
```python
# settings.py
RUN_MODE = 'distributed'
# Automatically uses RedisDedupPipeline
```

### 4.3 Custom Deduplication Pipeline
```python
# settings.py
RUN_MODE = 'standalone'  # or 'distributed'
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # Override default deduplication pipeline
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

## 5. Best Practices

1. **Standalone Small-Scale Crawlers**: Use default configuration, automatically select memory deduplication
2. **Distributed Crawlers**: Set `RUN_MODE = 'distributed'`, automatically use Redis deduplication
3. **Large-Scale Data Collection**: Consider using Bloom Filter deduplication to save memory
4. **Long-Running Tasks**: Use database deduplication to support resumable crawling

Through this automated configuration approach, users can more conveniently use the most suitable deduplication solution in different scenarios without manually adjusting complex configurations.