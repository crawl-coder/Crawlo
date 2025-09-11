# -*- coding: UTF-8 -*-
"""
动态模式配置文件
可以通过环境变量或参数来切换运行模式
"""

import os

PROJECT_NAME = 'ofweek_project'
VERSION = '1.0'

# ============================== 运行模式选择 ==============================
# 通过环境变量选择运行模式
RUN_MODE = os.getenv('CRAWLO_RUN_MODE', 'standalone')  # 'standalone' 或 'distributed'

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True
USE_SESSION = True

# ============================== 并发与调度 ==============================
# 根据运行模式设置不同的并发配置
if RUN_MODE == 'distributed':
    CONCURRENCY = int(os.getenv('CRAWLO_CONCURRENCY', 16))
    DOWNLOAD_DELAY = float(os.getenv('CRAWLO_DOWNLOAD_DELAY', 0.5))
    MAX_RUNNING_SPIDERS = 5
else:  # standalone
    CONCURRENCY = int(os.getenv('CRAWLO_CONCURRENCY', 8))
    DOWNLOAD_DELAY = float(os.getenv('CRAWLO_DOWNLOAD_DELAY', 1.0))
    MAX_RUNNING_SPIDERS = 3

RANDOMNESS = True

# ============================== 重试配置 ==============================
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

CONNECTION_POOL_LIMIT = 100

# ============================== 数据存储 ==============================
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
MYSQL_DB = os.getenv('MYSQL_DB', 'ofweek_project')
MYSQL_TABLE = 'crawled_data'

# ============================== Redis 配置 ==============================
# 分布式模式下使用
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', 2))
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 去重过滤 ==============================
# 根据运行模式自动选择过滤器
if RUN_MODE == 'distributed':
    FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
else:
    FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

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