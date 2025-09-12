# -*- coding: UTF-8 -*-
"""分布式模式配置文件"""

PROJECT_NAME = 'ofweek_project'
VERSION = '1.0'

# ============================== 运行模式配置 ==============================
RUN_MODE = 'distributed'  # 明确指定为分布式模式

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True
USE_SESSION = True

DOWNLOAD_DELAY = 0.5  # 分布式环境下可以设置更短的延迟
RANDOMNESS = True

MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

CONNECTION_POOL_LIMIT = 100

# ============================== 并发与调度 ==============================
CONCURRENCY = 16  # 分布式环境下可以设置更高的并发数
MAX_RUNNING_SPIDERS = 5

# ============================== 数据存储 ==============================
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'ofweek_project'
MYSQL_TABLE = 'crawled_data'

# ============================== Redis 配置 ==============================
# 分布式模式下的 Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''  # 如果没有密码则留空
REDIS_DB = 2  # Redis 数据库编号
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 去重过滤 ==============================
# 使用 Redis 过滤器实现分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# ============================== 队列配置 ==============================
# 使用 Redis 队列实现分布式调度
QUEUE_TYPE = 'redis'
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'

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
    # 可以添加 Redis 去重管道
    # 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
]

# ============================== 日志 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}_distributed.log'