# -*- coding: UTF-8 -*-
"""简化版配置文件用于测试"""

PROJECT_NAME = 'ofweek_project'
VERSION = '1.0'

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
CONCURRENCY = 4  # 减少并发数以便测试
MAX_RUNNING_SPIDERS = 1

# ============================== 数据存储 ==============================
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'ofweek_project'
MYSQL_TABLE = 'crawled_data'

# ============================== 去重过滤 ==============================
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'  # 使用内存过滤器以便测试

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
LOG_LEVEL = 'DEBUG'  # 使用DEBUG级别以便查看详细日志
LOG_FILE = f'logs/{PROJECT_NAME}.log'