# -*- coding: UTF-8 -*-
"""自动创建的 settings.py 文件"""

PROJECT_NAME = 'ofweek_project'
VERSION = '1.0'

# ============================== 运行模式配置 ==============================
# 根据运行模式自动选择配置
# RUN_MODE 可以是 'standalone' 或 'distributed'

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True
USE_SESSION = True

DOWNLOAD_DELAY = 1.0
RANDOMNESS = True

MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

CONNECTION_POOL_LIMIT = 100

# ============================== 并发与调度 ==============================
CONCURRENCY = 8
MAX_RUNNING_SPIDERS = 3

# ============================== 数据存储 ==============================
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'ofweek_project'
MYSQL_TABLE = 'crawled_data'

# ============================== 去重过滤 ==============================
# 根据运行模式自动选择去重过滤器
# standalone 模式使用内存过滤器
# distributed 模式使用 Redis 过滤器

# Redis 配置（distributed 模式使用）
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # 如果没有密码则留空
REDIS_DB = 2  # Redis 数据库编号，默认为 0
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 中间件 & 管道 ==============================
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]

# ============================== 日志 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'

# ============================== 运行模式特定配置 ==============================
# 这些配置会根据运行模式自动应用

# standalone 模式配置
STANDALONE_CONFIG = {
    'CONCURRENCY': 8,
    'DOWNLOAD_DELAY': 1.0,
    'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
    'SCHEDULER': 'crawlo.core.scheduler.Scheduler',
}

# distributed 模式配置
DISTRIBUTED_CONFIG = {
    'CONCURRENCY': 16,
    'DOWNLOAD_DELAY': 0.5,
    'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
    'SCHEDULER': 'crawlo.core.scheduler.Scheduler',
}