# 配置系统

Crawlo 提供了一个灵活而强大的配置系统，允许您自定义爬虫项目的每个方面。

## 配置方法

Crawlo 支持多种配置项目的方法：

### 1. 设置文件（`settings.py`）

使用 Python 文件的传统方法：

```python
# settings.py
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
```

### 2. 智能配置工厂

使用配置工厂的更灵活方法：

```python
from crawlo.config import CrawloConfig

# 单机模式
config = CrawloConfig.standalone().set_concurrency(16)

# 分布式模式
config = CrawloConfig.distributed(redis_host='192.168.1.100')

# 预设配置
config = CrawloConfig.presets().production()

# 链式调用
config = (CrawloConfig.standalone()
    .set_concurrency(20)
    .set_delay(1.5)
    .enable_debug()
    .enable_mysql())
```

### 3. 环境变量

通过环境变量进行配置：

```bash
export PROJECT_NAME=myproject
export CONCURRENCY=16
export DOWNLOAD_DELAY=1.0
```

## 配置层次结构

Crawlo 遵循特定的配置优先级层次结构：

1. **命令行参数** - 最高优先级
2. **爬虫中的自定义设置** - 爬虫特定设置
3. **项目 settings.py** - 项目级设置
4. **环境变量** - 基于环境的设置
5. **默认设置** - 框架默认值

## 核心配置选项

### 项目设置

```python
PROJECT_NAME = 'myproject'          # 项目标识符
VERSION = 1.0                       # 框架版本
RUN_MODE = 'standalone'             # 执行模式：standalone/distributed/auto
CONCURRENCY = 16                    # 并发请求数
DOWNLOAD_DELAY = 1.0                # 请求间延迟（秒）
```

### 队列配置

```python
QUEUE_TYPE = 'memory'               # 队列类型：memory/redis/auto
SCHEDULER = 'crawlo.scheduler.Scheduler'  # 调度器类
SCHEDULER_MAX_QUEUE_SIZE = 1000     # 最大队列大小
SCHEDULER_QUEUE_NAME = 'crawlo:myproject:queue:requests'  # 队列名称
```

### 下载器配置

```python
DOWNLOADER_TYPE = 'aiohttp'         # 下载器类型：aiohttp/httpx/curl_cffi
DOWNLOAD_TIMEOUT = 30               # 请求超时（秒）
VERIFY_SSL = True                   # SSL 验证
USE_SESSION = False                 # 使用会话进行请求
```

### 过滤器配置

```python
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'  # 过滤器类
FILTER_DEBUG = False                # 过滤器调试模式
REDIS_TTL = 0                       # Redis 键 TTL（0 = 永不过期）
CLEANUP_FP = False                  # 关闭时清理指纹
```

### 管道配置

```python
PIPELINES = [                       # 管道类
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

### 中间件配置

```python
MIDDLEWARES = [                     # 中间件类
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
]
```

## 环境特定配置

### 开发环境

```python
# settings.py
PROJECT_NAME = 'myproject_dev'
CONCURRENCY = 4
DOWNLOAD_DELAY = 2.0
LOG_LEVEL = 'DEBUG'
DUPEFILTER_DEBUG = True
FILTER_DEBUG = True

# 使用控制台管道以获得即时反馈
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]
```

### 生产环境

```python
# settings.py
PROJECT_NAME = 'myproject_prod'
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.5
LOG_LEVEL = 'INFO'

# 使用生产级管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# 生产环境的增强重试设置
MAX_RETRY_TIMES = 5
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]
```

## 分布式配置

### 基本分布式设置

```python
# 分布式模式配置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# 并发设置
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# 调度器配置
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
```

## 配置验证

Crawlo 提供了一个配置验证工具，以确保您的设置正确：

```python
from crawlo.config_validator import ConfigValidator

# 创建配置验证器
validator = ConfigValidator()

# 验证配置
config = {
    'PROJECT_NAME': 'test_project',
    'QUEUE_TYPE': 'redis',
    'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379
}

is_valid, errors, warnings = validator.validate(config)
if not is_valid:
    print("配置验证失败:")
    for error in errors:
        print(f"  - {error}")
```

## 最佳实践

1. **对敏感数据使用环境变量**，如密码和 API 密钥
2. **为不同环境分离配置**（开发、测试、生产）
3. **用注释记录您的自定义设置**
4. **在部署前验证配置**
5. **对复杂设置使用配置工厂**
6. **遵循命名约定以保持一致性**