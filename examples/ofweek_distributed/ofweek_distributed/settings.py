# -*- coding: UTF-8 -*-
"""
ofweek_distributed 项目配置文件
=============================
基于 Crawlo 框架的分布式爬虫项目配置。
适合大规模数据采集和多节点部署。
"""

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_distributed'

# ============================== 运行模式 ==============================
RUN_MODE = 'distributed'

# ============================== 并发配置 ==============================
CONCURRENCY = 16
MAX_RUNNING_SPIDERS = 5
DOWNLOAD_DELAY = 0.5

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== Redis 配置 ==============================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'redis'
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'

# ============================== 去重过滤器 ==============================
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# ============================== 默认去重管道 ==============================
# 明确指定分布式模式下使用Redis去重管道
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_distributed.spiders']

# ============================== 中间件 ==============================
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# ============================== 数据管道 ==============================
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',  # Redis去重管道
]

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/ofweek_distributed.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'