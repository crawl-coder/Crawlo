# -*- coding: UTF-8 -*-
"""
telecom_licenses_distributed.settings
=====================================
电信设备许可证采集项目配置文件（分布式版）
基于 Crawlo 框架的分布式爬虫项目配置。

分布式特性：
- Redis 分布式队列和去重
- 高并发处理
- 多节点协同采集
"""

PROJECT_NAME = 'telecom_licenses_distributed'
VERSION = '1.0'

# ============================== 运行模式配置 ==============================
# 分布式模式配置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True
USE_SESSION = True

# 分布式环境下可以适当降低延迟
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True

MAX_RETRY_TIMES = 5  # 分布式环境增加重试次数
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

CONNECTION_POOL_LIMIT = 100

# ============================== 并发与调度 ==============================
CONCURRENCY = 16  # 分布式模式支持更高并发
MAX_RUNNING_SPIDERS = 5

# 调度器配置
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
SCHEDULER_MAX_QUEUE_SIZE = 5000
SCHEDULER_QUEUE_NAME = 'crawlo:telecom_licenses_distributed:queue:requests'  # 使用统一命名规范

# ============================== 数据存储 ==============================
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'telecom_licenses_distributed'
MYSQL_TABLE = 'crawled_data'

# ============================== 分布式去重配置 ==============================
# 使用 Redis 进行分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # 如果没有密码则留空
REDIS_DB = 2  # Redis 数据库编号，默认为 0
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Redis key配置已移至AioRedisFilter中，使用统一的命名规范
# crawlo:{PROJECT_NAME}:filter:fingerprint

REDIS_TTL = 0  # 指纹永不过期
CLEANUP_FP = 0  # 程序结束时不清理指纹
FILTER_DEBUG = True
DECODE_RESPONSES = True

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
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # 可选：数据库存储
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'
STATS_DUMP = True

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]