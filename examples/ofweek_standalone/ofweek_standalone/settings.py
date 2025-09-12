# -*- coding: UTF-8 -*-
"""
ofweek_standalone 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。
"""

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_standalone'
VERSION = 1.0

# ============================== 运行模式 ==============================
RUN_MODE = 'standalone'

# ============================== 并发配置 ==============================
CONCURRENCY = 4
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 1.0

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'auto'

# ============================== 去重过滤器 ==============================
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_standalone.spiders']

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

# ============================== 扩展组件 ==============================
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/ofweek_standalone.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'