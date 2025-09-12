# -*- coding: UTF-8 -*-
"""
ofweek_spider 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。
支持单机和分布式模式切换。
"""

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_spider'
VERSION = '1.0.0'

# ============================== 运行模式 ==============================
# 可以通过环境变量切换模式:
# export CRAWLO_MODE=standalone  # 单机模式
# export CRAWLO_MODE=distributed  # 分布式模式
import os
RUN_MODE = os.getenv('CRAWLO_MODE', 'standalone')

# ============================== 并发配置 ==============================
CONCURRENCY = 8 if RUN_MODE == 'distributed' else 4
MAX_RUNNING_SPIDERS = 5 if RUN_MODE == 'distributed' else 1
DOWNLOAD_DELAY = 0.5 if RUN_MODE == 'distributed' else 1.0

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== Redis 配置 ==============================
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'redis' if RUN_MODE == 'distributed' else 'memory'
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'

# ============================== 去重过滤器 ==============================
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter' if RUN_MODE == 'distributed' else 'crawlo.filters.memory_filter.MemoryFilter'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_spider.spiders']

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
]

# 分布式模式下添加 Redis 去重管道
if RUN_MODE == 'distributed':
    PIPELINES.insert(0, 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'

# ============================== 代理配置 ==============================

# ============================== 浏览器指纹配置 ==============================

# ============================== 下载器优化配置 ==============================

# ============================== 开发与调试 ==============================

# ============================== 自定义配置区域 ==============================
# 在此处添加项目特定的配置项

# 示例：目标网站特定配置
# TARGET_DOMAIN = '{{domain}}'
# MAX_PAGES_PER_DOMAIN = 10000
# CUSTOM_RATE_LIMIT = 1.5