# -*- coding: utf-8 -*-
"""
books_distributed.settings
=====================================
Books scraping project configuration (Distributed version)
Based on Crawlo framework's distributed crawler configuration.

Distributed features:
- Redis distributed queue and deduplication
- High concurrency processing
- Multi-node collaborative crawling
"""

PROJECT_NAME = 'books_distributed'
VERSION = '1.0'

# ============================== Runtime mode configuration ==============================
# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# ============================== Network request configuration ==============================
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True
USE_SESSION = True

# In distributed environment, delay can be appropriately reduced
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True

MAX_RETRY_TIMES = 5  # Increase retry count in distributed environment
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

CONNECTION_POOL_LIMIT = 100

# ============================== Concurrency and scheduling ==============================
CONCURRENCY = 16  # Distributed mode supports higher concurrency
MAX_RUNNING_SPIDERS = 5

# Scheduler configuration
SCHEDULER = 'crawlo.core.scheduler.Scheduler'
SCHEDULER_MAX_QUEUE_SIZE = 5000
SCHEDULER_QUEUE_NAME = 'books:requests'

# ============================== Data storage ==============================
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'books_distributed'
MYSQL_TABLE = 'crawled_data'

# ============================== Distributed deduplication configuration ==============================
# Use Redis for distributed deduplication
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'


# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # Leave empty if no password
REDIS_DB = 4  # Redis database number
# If Redis requires authentication, set REDIS_URL with password
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
# REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
REDIS_KEY = 'books:fingerprint'
REDIS_TTL = 0  # Fingerprints never expire
CLEANUP_FP = 0  # Do not clean fingerprints when program ends
FILTER_DEBUG = True
DECODE_RESPONSES = True

# ============================== Middleware & Pipelines ==============================
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
    'books_distributed.pipelines.URLLoggingPipeline',  # URL logging pipeline
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # Console output
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # Optional: database storage
]

# ============================== Logging configuration ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'
STATS_DUMP = True

# ============================== Extension components ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]