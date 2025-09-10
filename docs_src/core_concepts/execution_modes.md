# Execution Modes

Crawlo supports three execution modes to accommodate different crawling scenarios:

## 1. Standalone Mode (Default)

Standalone mode is the default execution mode, suitable for development and small-scale crawling tasks. In this mode:

- Uses in-memory queues and filters
- No external dependencies required
- Single-node operation
- Lower resource consumption

### Configuration

```python
# settings.py
RUN_MODE = 'standalone'
QUEUE_TYPE = 'memory'
```

## 2. Distributed Mode

Distributed mode is designed for large-scale crawling tasks that require multiple nodes working together. In this mode:

- Uses Redis-based queues and filters
- Supports horizontal scaling
- Shared task queue across nodes
- Distributed deduplication

### Configuration

```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Distributed scheduler and filter
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
```

## 3. Auto Mode

Auto mode automatically detects the best execution mode based on the environment and configuration. It:

- Checks for Redis availability
- Falls back to standalone mode if Redis is not available
- Provides seamless switching between modes

### Configuration

```python
# settings.py
RUN_MODE = 'auto'
QUEUE_TYPE = 'auto'
```

## Mode Selection Guidelines

| Scenario | Recommended Mode | Reason |
|----------|------------------|--------|
| Development | Standalone | Simple setup, no external dependencies |
| Small-scale crawling | Standalone | Lower resource consumption |
| Large-scale crawling | Distributed | Horizontal scaling, better performance |
| Production deployment | Distributed | Fault tolerance, shared state |
| Uncertain environment | Auto | Automatic detection and fallback |

## Switching Between Modes

To switch between modes, simply change the `RUN_MODE` setting in your `settings.py` file and adjust the related configurations accordingly. Crawlo will automatically handle the rest.