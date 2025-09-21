# -*- coding: UTF-8 -*-
"""
ofweek_spider 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。
"""

import os

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_spider'
# ============================== 运行模式 ==============================
RUN_MODE = 'standalone'

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# ============================== Redis配置 ==============================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0

# 根据是否有密码生成 URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 并发配置 ==============================
CONCURRENCY = 24
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 1.0

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'memory'

# ============================== 去重过滤器 ==============================
# 使用auto模式，让框架根据Redis可用性自动选择过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# ============================== 默认去重管道 ==============================
# 使用auto模式，让框架根据Redis可用性自动选择去重管道
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_spider.spiders']

# ============================== 中间件 ==============================
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# ============================== 数据管道 ==============================
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    # 注意：去重管道会自动添加到列表开头，无需在这里显式声明
]

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/ofweek_spider.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'