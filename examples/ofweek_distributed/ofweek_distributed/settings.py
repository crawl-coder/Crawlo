# -*- coding: UTF-8 -*-
"""
ofweek_distributed 项目配置文件
==============================
基于 Crawlo 框架的分布式爬虫项目配置。
"""

import os

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_distributed'

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# ============================== 分布式运行模式 ==============================
RUN_MODE = 'distributed'

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
CONCURRENCY = 16
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 1.0

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'redis'

# ============================== 去重过滤器 ==============================
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# ============================== 默认去重管道 ==============================
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_distributed.spiders']

# ============================== 用户自定义中间件 ==============================
# 注意：框架默认中间件已自动加载，此处可添加或覆盖默认中间件

# 中间件列表（框架默认中间件 + 用户自定义中间件）
MIDDLEWARES = [
    # 'ofweek_distributed.middlewares.CustomMiddleware',  # 示例自定义中间件
]

# ============================== 用户自定义数据管道 ==============================
# 注意：框架默认管道已自动加载，此处可添加或覆盖默认管道

# 数据处理管道列表（框架默认管道 + 用户自定义管道）
PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    # 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',  # Redis去重管道（已默认加载）
]

# ============================== 用户自定义扩展组件 ==============================
# 注意：框架默认扩展已自动加载，此处可添加或覆盖默认扩展

# 扩展组件列表（框架默认扩展 + 用户自定义扩展）
EXTENSIONS = [
    # 'crawlo.extension.memory_monitor.MemoryMonitorExtension',  # 内存监控
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/ofweek_distributed.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'