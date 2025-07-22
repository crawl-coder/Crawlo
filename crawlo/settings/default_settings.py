#!/usr/bin/python
# -*- coding:UTF-8 -*-
# 默认项目名称
import os

PROJECT_NAME = 'crawlo'
VERSION = 1.0
# 并发数
CONCURRENCY = 8

# 下载超时时长
DOWNLOAD_TIMEOUT = 60

INTERVAL = 5

# --------------------------------------------------- delay ------------------------------------------------------------
# 下载延迟，默认关闭
DOWNLOAD_DELAY = 0
# 下载延迟范围
RANDOM_RANGE = (0.75, 1.25)
# 是否需要随机
RANDOMNESS = True

# --------------------------------------------------- retry ------------------------------------------------------------
MAX_RETRY_TIMES = 2
IGNORE_HTTP_CODES = [403, 404]
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
# 允许通过的状态码
ALLOWED_CODES = []
# 请求优先级设置
RETRY_PRIORITY = -1
#
DEPTH_PRIORITY = 1

STATS_DUMP = True
# ssl 验证
VERIFY_SSL = True
# 是否使用同一个session
USE_SESSION = True
# 日志级别
LOG_LEVEL = 'DEBUG'
# 选择下载器
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"  # HttpXDownloader

# --------------------------------------------------- 公共MySQL配置 -----------------------------------------------------
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'scrapy_user'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'scrapy_data'
MYSQL_TABLE = 'crawled_data'

# asyncmy专属配置
MYSQL_POOL_MIN = 5  # 连接池最小连接数
MYSQL_POOL_MAX = 20  # 连接池最大连接数
MYSQL_ECHO = False

# 批量插入大小
MYSQL_BATCH_SIZE = 100

# --------------------------------------------------- MongoDB 基础配置 -----------------------------------------------------
MONGO_URI = 'mongodb://user:password@host:27017'
MONGO_DATABASE = 'scrapy_data'
MONGO_COLLECTION = 'crawled_items'  # 可选，默认使用spider名称

# 连接池优化配置（仅方案二需要）
MONGO_MAX_POOL_SIZE = 200  # 最大连接数
MONGO_MIN_POOL_SIZE = 20  # 最小保持连接数

# 启用管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]


EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats'
]

# filter
REQUEST_DIR = '.'
FILTER_DEBUG = True
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# redis filter
CLEANUP_FP = False
DECODE_RESPONSES = True
REDIS_KEY = 'request_fingerprint'
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'oscar&0503')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:{REDIS_PORT}/0'
