# Configuration Best Practices

This guide provides recommendations for configuring Crawlo projects for different environments and use cases.

## Configuration Methods

Crawlo supports multiple ways to configure your projects:

### 1. Settings File (`settings.py`)

The traditional method using a Python file:

```python
# settings.py
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
```

### 2. Smart Configuration Factory

A more flexible approach using the configuration factory:

```python
from crawlo.config import CrawloConfig

# Standalone mode
config = CrawloConfig.standalone().set_concurrency(16)

# Distributed mode
config = CrawloConfig.distributed(redis_host='192.168.1.100')

# Preset configurations
config = CrawloConfig.presets().production()

# Chainable calls
config = (CrawloConfig.standalone()
    .set_concurrency(20)
    .set_delay(1.5)
    .enable_debug()
    .enable_mysql())
```

### 3. Environment Variables

Configuration through environment variables:

```bash
export PROJECT_NAME=myproject
export CONCURRENCY=16
export DOWNLOAD_DELAY=1.0
```

## Environment-Specific Configurations

### Development Environment

```python
# settings.py
PROJECT_NAME = 'myproject_dev'
CONCURRENCY = 4
DOWNLOAD_DELAY = 2.0
LOG_LEVEL = 'DEBUG'
DUPEFILTER_DEBUG = True
FILTER_DEBUG = True

# Use console pipeline for immediate feedback
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]
```

### Production Environment

```python
# settings.py
PROJECT_NAME = 'myproject_prod'
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.5
LOG_LEVEL = 'INFO'

# Use robust pipelines for production
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# Enhanced retry settings for production
MAX_RETRY_TIMES = 5
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]
```

### Large-Scale Environment

```python
# settings.py
PROJECT_NAME = 'myproject_large'
CONCURRENCY = 64
DOWNLOAD_DELAY = 0.1
LOG_LEVEL = 'WARNING'

# Distributed settings
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis configuration
REDIS_HOST = 'redis-cluster.internal'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_KEY = 'myproject_large:fingerprint'

# Performance optimizations
CONNECTION_POOL_LIMIT = 200
CONNECTION_POOL_LIMIT_PER_HOST = 50
```

## Downloader Selection

### aiohttp (Default)

Best for general purpose crawling with high performance:

```python
DOWNLOADER_TYPE = 'aiohttp'
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 20
```

### httpx

Best when you need HTTP/2 support:

```python
DOWNLOADER_TYPE = 'httpx'
HTTPX_HTTP2 = True
```

### curl-cffi

Best for anti-scraping scenarios requiring browser fingerprinting:

```python
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'  # or 'firefox130', 'safari17'
```

## Pipeline Configuration

### Development Pipeline

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

### Production Pipeline

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # For monitoring
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # For storage
    'crawlo.pipelines.json_pipeline.JsonPipeline',  # For backup
]
```

### High-Volume Pipeline

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # For monitoring
    'crawlo.pipelines.mongo_pipeline.MongoPoolPipeline',  # For high-volume storage
]
```

## Middleware Configuration

### Basic Middleware

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
]
```

### Advanced Middleware

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]
```

## Distributed Configuration

### Basic Distributed Setup

```python
# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# Concurrency settings
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# Scheduler configuration
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Distributed deduplication
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'
```

### Production Distributed Setup

```python
# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# High concurrency for production
CONCURRENCY = 64
DOWNLOAD_DELAY = 0.1

# Scheduler configuration
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
SCHEDULER_MAX_QUEUE_SIZE = 10000
SCHEDULER_QUEUE_NAME = 'myproject:requests'

# Redis configuration for production
REDIS_HOST = 'redis-cluster.internal'
REDIS_PORT = 6379
REDIS_PASSWORD = 'secure_password'
REDIS_DB = 2
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Distributed deduplication with TTL
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'
REDIS_TTL = 86400  # 24 hours
CLEANUP_FP = False  # Keep fingerprints after shutdown

# Performance settings
CONNECTION_POOL_LIMIT = 200
MAX_RETRY_TIMES = 5
```

## Performance Tuning

### Connection Pool Settings

```python
# Global connection pool
CONNECTION_POOL_LIMIT = 100

# Per-host connection pool
CONNECTION_POOL_LIMIT_PER_HOST = 20

# Download timeout
DOWNLOAD_TIMEOUT = 30
```

### Concurrency Settings

```python
# Number of concurrent requests
CONCURRENCY = 16

# Download delay between requests
DOWNLOAD_DELAY = 1.0

# Randomness in delays
RANDOMNESS = True
```

### Retry Settings

```python
# Maximum retry attempts
MAX_RETRY_TIMES = 3

# HTTP codes to retry
RETRY_HTTP_CODES = [500, 502, 503, 504]

# HTTP codes to ignore
IGNORE_HTTP_CODES = [403, 404]
```

## Monitoring and Logging

### Basic Logging

```python
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/crawlo.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
```

### Detailed Logging

```python
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'logs/crawlo_detailed.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s - %(filename)s:%(lineno)d: %(message)s'

# Enable detailed statistics
DOWNLOADER_STATS = True
DOWNLOAD_STATS = True
DOWNLOADER_HEALTH_CHECK = True
REQUEST_STATS_ENABLED = True
```

## Security Configuration

### Proxy Settings

```python
# Enable proxy middleware
MIDDLEWARES = [
    # ... other middleware
    'crawlo.middleware.proxy.ProxyMiddleware',
]

# Proxy configuration
PROXY_ENABLED = True
PROXY_LIST = [
    'http://proxy1:8080',
    'http://proxy2:8080',
    'http://proxy3:8080',
]
```

### User-Agent Rotation

```python
# Custom headers middleware
MIDDLEWARES = [
    # ... other middleware
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# User-Agent list
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]
```

## Best Practices Summary

1. **Start Simple**: Begin with basic configurations and gradually add complexity
2. **Environment Separation**: Use different configurations for development, testing, and production
3. **Performance Monitoring**: Enable statistics and monitoring in production
4. **Security Considerations**: Use proxies and user-agent rotation for sensitive targets
5. **Resource Management**: Adjust concurrency and connection pools based on system resources
6. **Error Handling**: Configure appropriate retry settings and error handling
7. **Data Consistency**: Use proper deduplication in distributed environments
8. **Scalability**: Design configurations that can scale with your crawling needs

By following these configuration best practices, you can ensure that your Crawlo projects are optimized for their specific use cases and environments.