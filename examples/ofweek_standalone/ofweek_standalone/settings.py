# -*- coding: UTF-8 -*-
"""
ofweek_standalone 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。
"""

import os

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'ofweek_standalone'
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

# ============================== 用户自定义中间件 ==============================
# 注意：框架默认中间件已自动加载，此处可添加或覆盖默认中间件

# 中间件列表（框架默认中间件 + 用户自定义中间件）
MIDDLEWARES = [
    # 'ofweek_standalone.middlewares.CustomMiddleware',  # 示例自定义中间件
]

# ============================== 用户自定义数据管道 ==============================
# 注意：框架默认管道已自动加载，此处可添加或覆盖默认管道

# 数据处理管道列表（框架默认管道 + 用户自定义管道）
PIPELINES = [
    # 'crawlo.pipelines.json_pipeline.JsonPipeline',
]

# ============================== 用户自定义扩展组件 ==============================
# 注意：框架默认扩展已自动加载，此处可添加或覆盖默认扩展

# 扩展组件列表（框架默认扩展 + 用户自定义扩展）
EXTENSIONS = [
    # 'crawlo.extension.memory_monitor.MemoryMonitorExtension',  # 内存监控
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'DEBUG'
# LOG_CONSOLE_LEVEL = 'DEBUG'  # 添加控制台日志级别配置
LOG_FILE = 'logs/ofweek_standalone.log'
# 启用日志轮转功能
LOG_USE_ROTATION = True
LOG_ROTATION_TYPE = 'size'  # 或者使用 'time'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
# 时间轮转时的文件后缀格式（可选）
# LOG_ROTATION_SUFFIX = '%Y-%m-%d_%H-%M-%S'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'