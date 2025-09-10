# 配置最佳实践

本指南提供了为不同环境和用例配置 Crawlo 项目的建议。

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

### 大规模环境

```python
# settings.py
PROJECT_NAME = 'myproject_large'
CONCURRENCY = 64
DOWNLOAD_DELAY = 0.1
LOG_LEVEL = 'WARNING'

# 分布式设置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis 配置
REDIS_HOST = 'redis-cluster.internal'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_KEY = 'myproject_large:fingerprint'

# 性能优化
CONNECTION_POOL_LIMIT = 200
CONNECTION_POOL_LIMIT_PER_HOST = 50
```

## 下载器选择

### aiohttp（默认）

适用于具有高性能的一般用途爬取：

```python
DOWNLOADER_TYPE = 'aiohttp'
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 20
```

### httpx

当您需要 HTTP/2 支持时最佳：

```python
DOWNLOADER_TYPE = 'httpx'
HTTPX_HTTP2 = True
```

### curl-cffi

适用于需要浏览器指纹的反爬虫场景：

```python
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'  # 或 'firefox130', 'safari17'
```

## 管道配置

### 开发管道

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

### 生产管道

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # 用于监控
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # 用于存储
    'crawlo.pipelines.json_pipeline.JsonPipeline',  # 用于备份
]
```

### 高容量管道

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # 用于监控
    'crawlo.pipelines.mongo_pipeline.MongoPoolPipeline',  # 用于高容量存储
]
```

## 中间件配置

### 基本中间件

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
]
```

### 高级中间件

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
REDIS_KEY = 'myproject:fingerprint'
```

### 生产分布式设置

```python
# 分布式模式配置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# 生产环境的高并发
CONCURRENCY = 64
DOWNLOAD_DELAY = 0.1

# 调度器配置
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
SCHEDULER_MAX_QUEUE_SIZE = 10000
SCHEDULER_QUEUE_NAME = 'myproject:requests'

# 生产环境的 Redis 配置
REDIS_HOST = 'redis-cluster.internal'
REDIS_PORT = 6379
REDIS_PASSWORD = 'secure_password'
REDIS_DB = 2
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 带 TTL 的分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'
REDIS_TTL = 86400  # 24 小时
CLEANUP_FP = False  # 关闭后保留指纹

# 性能设置
CONNECTION_POOL_LIMIT = 200
MAX_RETRY_TIMES = 5
```

## 性能调优

### 连接池设置

```python
# 全局连接池
CONNECTION_POOL_LIMIT = 100

# 每个主机的连接池
CONNECTION_POOL_LIMIT_PER_HOST = 20

# 下载超时
DOWNLOAD_TIMEOUT = 30
```

### 并发设置

```python
# 并发请求数
CONCURRENCY = 16

# 请求之间的下载延迟
DOWNLOAD_DELAY = 1.0

# 延迟中的随机性
RANDOMNESS = True
```

### 重试设置

```python
# 最大重试次数
MAX_RETRY_TIMES = 3

# 要重试的 HTTP 代码
RETRY_HTTP_CODES = [500, 502, 503, 504]

# 要忽略的 HTTP 代码
IGNORE_HTTP_CODES = [403, 404]
```

## 监控和日志

### 基本日志

```python
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/crawlo.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
```

### 详细日志

```python
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'logs/crawlo_detailed.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s - %(filename)s:%(lineno)d: %(message)s'

# 启用详细统计
DOWNLOADER_STATS = True
DOWNLOAD_STATS = True
DOWNLOADER_HEALTH_CHECK = True
REQUEST_STATS_ENABLED = True
```

## 安全配置

### 代理设置

```python
# 启用代理中间件
MIDDLEWARES = [
    # ... 其他中间件
    'crawlo.middleware.proxy.ProxyMiddleware',
]

# 代理配置
PROXY_ENABLED = True
PROXY_LIST = [
    'http://proxy1:8080',
    'http://proxy2:8080',
    'http://proxy3:8080',
]
```

### User-Agent 轮换

```python
# 自定义头部中间件
MIDDLEWARES = [
    # ... 其他中间件
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# User-Agent 列表
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]
```

## 最佳实践总结

1. **从简单开始**：从基本配置开始，逐步增加复杂性
2. **环境分离**：为开发、测试和生产使用不同的配置
3. **性能监控**：在生产环境中启用统计和监控
4. **安全考虑**：对敏感目标使用代理和 User-Agent 轮换
5. **资源管理**：根据系统资源调整并发和连接池
6. **错误处理**：配置适当的重试设置和错误处理
7. **数据一致性**：在分布式环境中使用适当的去重
8. **可扩展性**：设计可以随爬取需求扩展的配置

通过遵循这些配置最佳实践，您可以确保 Crawlo 项目针对其特定用例和环境进行了优化。