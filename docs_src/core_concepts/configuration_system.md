# Configuration System

Crawlo provides a flexible and powerful configuration system that allows you to customize every aspect of your crawling projects.

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

## Configuration Hierarchy

Crawlo follows a specific hierarchy for configuration precedence:

1. **Command-line arguments** - Highest precedence
2. **Custom settings in spider** - Spider-specific settings
3. **Project settings.py** - Project-level settings
4. **Environment variables** - Environment-based settings
5. **Default settings** - Framework defaults

## Core Configuration Options

### Project Settings

```python
PROJECT_NAME = 'myproject'          # Project identifier
VERSION = 1.0                       # Framework version
RUN_MODE = 'standalone'             # Execution mode: standalone/distributed/auto
CONCURRENCY = 16                    # Concurrent requests
DOWNLOAD_DELAY = 1.0                # Delay between requests (seconds)
```

### Queue Configuration

```python
QUEUE_TYPE = 'memory'               # Queue type: memory/redis/auto
SCHEDULER = 'crawlo.scheduler.Scheduler'  # Scheduler class
SCHEDULER_MAX_QUEUE_SIZE = 1000     # Maximum queue size
SCHEDULER_QUEUE_NAME = 'crawlo:myproject:queue:requests'  # Queue name
```

### Downloader Configuration

```python
DOWNLOADER_TYPE = 'aiohttp'         # Downloader type: aiohttp/httpx/curl_cffi
DOWNLOAD_TIMEOUT = 30               # Request timeout (seconds)
VERIFY_SSL = True                   # SSL verification
USE_SESSION = False                 # Use session for requests
```

### Filter Configuration

```python
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'  # Filter class
FILTER_DEBUG = False                # Filter debug mode
REDIS_TTL = 0                       # Redis key TTL (0 = never expire)
CLEANUP_FP = False                  # Cleanup fingerprints on shutdown
```

### Pipeline Configuration

```python
PIPELINES = [                       # Pipeline classes
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

### Middleware Configuration

```python
MIDDLEWARES = [                     # Middleware classes
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
]
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
```

## Configuration Validation

Crawlo provides a configuration validation tool to ensure your settings are correct:

```python
from crawlo.config_validator import ConfigValidator

# Create configuration validator
validator = ConfigValidator()

# Validate configuration
config = {
    'PROJECT_NAME': 'test_project',
    'QUEUE_TYPE': 'redis',
    'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379
}

is_valid, errors, warnings = validator.validate(config)
if not is_valid:
    print("Configuration validation failed:")
    for error in errors:
        print(f"  - {error}")
```

## Best Practices

1. **Use environment variables for sensitive data** like passwords and API keys
2. **Separate configurations for different environments** (dev, test, prod)
3. **Document your custom settings** with comments
4. **Validate configurations** before deployment
5. **Use the configuration factory** for complex setups
6. **Follow naming conventions** for consistency