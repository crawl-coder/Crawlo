# Data Deduplication Pipeline Usage Guide

Crawlo framework provides multiple data deduplication pipelines suitable for different use cases and requirements. This document will detail the characteristics, configuration methods, and usage recommendations for each deduplication pipeline.

## 1. Memory Deduplication Pipeline (MemoryDedupPipeline)

### Characteristics
- **High Performance**: Uses memory sets for fast lookups
- **Easy to Use**: No external dependencies required
- **Lightweight**: Suitable for small-scale data collection
- **Low Latency**: Memory operations without network overhead

### Applicable Scenarios
- Standalone crawlers
- Small-scale data collection (under ten thousand items)
- Temporary data collection tasks

### Configuration Method
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MemoryDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### Limitations
- Deduplication state is lost after restart
- Memory usage grows with data volume
- Does not support distributed environments

## 2. Redis Deduplication Pipeline (RedisDedupPipeline)

### Characteristics
- **Distributed Support**: Multiple nodes share deduplication data
- **High Performance**: Uses Redis sets for fast lookups
- **Configurable**: Supports custom Redis connection parameters
- **Fault-Tolerant Design**: Network exceptions won't lose data

### Applicable Scenarios
- Distributed crawler systems
- Medium to large-scale data collection
- Scenarios requiring persistent deduplication state

### Configuration Method
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Redis configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_DEDUP_KEY = 'crawlo:item_fingerprints'
```

### Limitations
- Requires deployment and maintenance of Redis service
- Network latency affects performance

## 3. Bloom Filter Deduplication Pipeline (BloomDedupPipeline)

### Characteristics
- **High Memory Efficiency**: Saves significant memory compared to traditional sets
- **High Performance**: Fast insertion and lookup operations
- **Scalable**: Supports custom capacity and error rate
- **Wide Applicability**: Especially suitable for large-scale data collection

### Applicable Scenarios
- Large-scale data collection (millions of items)
- Memory resource-constrained environments
- Scenarios where a small number of false positives are acceptable

### Configuration Method
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Bloom Filter configuration
BLOOM_FILTER_CAPACITY = 1000000
BLOOM_FILTER_ERROR_RATE = 0.001
```

### Notes
- Bloom Filter has a false positive rate, which may incorrectly discard some unseen data items
- Requires installing `pybloom_live` library: `pip install pybloom-live`

## 4. Database Deduplication Pipeline (DatabaseDedupPipeline)

### Characteristics
- **Persistent Storage**: Maintains deduplication state after crawler restart
- **High Reliability**: Database transactions ensure consistency
- **Wide Applicability**: Supports multiple database backends
- **Scalable**: Supports custom table structures and fields

### Applicable Scenarios
- Long-running crawlers
- Resumable crawling requirements
- Scenarios with extremely high data integrity requirements

### Configuration Method
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.DatabaseDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Database configuration
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'crawlo'
DB_DEDUP_TABLE = 'item_fingerprints'
```

### Limitations
- Database I/O operations affect performance
- Requires additional database resources

## 5. Selection Recommendations

Choose the appropriate deduplication pipeline based on different requirements:

| Scenario | Recommended Solution | Reason |
|----------|----------------------|--------|
| Small-scale standalone crawler | MemoryDedupPipeline | Simple and efficient, no external dependencies |
| Distributed crawler | RedisDedupPipeline | Supports multi-node shared state |
| Large-scale data collection | BloomDedupPipeline | Low memory usage, good performance |
| Long-running tasks | DatabaseDedupPipeline | Supports resumable crawling |

## 6. Performance Comparison

| Solution | Memory Usage | Performance | Persistence | Distributed Support | False Positive Rate |
|----------|--------------|-------------|-------------|---------------------|---------------------|
| Memory | High | Highest | No | No | None |
| Redis | Low | High | Yes | Yes | None |
| Bloom Filter | Lowest | High | No | No | Yes |
| Database | Low | Medium | Yes | No | None |

## 7. Usage Examples

### Basic Usage
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### Combined Usage
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # Preliminary filtering
    'crawlo.pipelines.RedisDedupPipeline': 200,  # Precise deduplication
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

### Custom Configuration
```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MemoryDedupPipeline': 100,
    'crawlo.pipelines.ConsolePipeline': 300,
}

# Custom memory deduplication pipeline configuration
DEDUP_LOG_LEVEL = 'DEBUG'
```

By properly selecting and configuring deduplication pipelines, you can effectively improve the data quality and collection efficiency of your crawlers.