# -*- coding: UTF-8 -*-
"""
test_logger_fix 项目配置文件（温和版）
=============================
基于 Crawlo 框架的温和爬虫项目配置。
适合对目标网站友好的低负载爬取。
"""

import os
from crawlo.config import CrawloConfig

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'test_logger_fix'
VERSION = '1.0.0'

# ============================== 温和模式配置 ==============================
# 使用配置工厂创建温和模式配置
CONFIG = CrawloConfig.presets().gentle()

# 获取配置
locals().update(CONFIG.to_dict())

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"
DOWNLOAD_TIMEOUT = 60
VERIFY_SSL = True

# ============================== 低并发配置 ==============================
CONCURRENCY = 2
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 3.0
RANDOMNESS = True
RANDOM_RANGE = (2.0, 5.0)

# ============================== 连接池配置 ==============================
CONNECTION_POOL_LIMIT = 10
CONNECTION_POOL_LIMIT_PER_HOST = 5

# ============================== 重试配置 ==============================
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]

# ============================== 队列配置 ==============================
SCHEDULER_MAX_QUEUE_SIZE = 1000
QUEUE_MAX_RETRIES = 3
QUEUE_TIMEOUT = 300

# ============================== 数据存储配置 ==============================
# MySQL 配置
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
MYSQL_DB = os.getenv('MYSQL_DB', 'test_logger_fix')
MYSQL_TABLE = 'test_logger_fix_data'

# MongoDB 配置
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DATABASE = 'test_logger_fix_db'
MONGO_COLLECTION = 'test_logger_fix_items'

# ============================== 去重配置 ==============================
REDIS_TTL = 0
CLEANUP_FP = 0
FILTER_DEBUG = True

# ============================== 中间件与管道 ==============================
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
]

PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    # 'test_logger_fix.pipelines.DatabasePipeline',
]

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/test_logger_fix.log'
STATS_DUMP = True

# ============================== 自定义配置 ==============================
# 在此处添加项目特定的配置项