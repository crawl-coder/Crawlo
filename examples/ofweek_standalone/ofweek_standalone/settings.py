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
RUN_MODE = 'standalone'  # 改为分布式模式以测试Redis队列

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
CONCURRENCY = 8  # 从32降低到8以减少Redis连接数
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 0.05  # 从0.1减少到0.05秒

# ============================== 下载器配置 ==============================
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'memory'  # 使用Redis队列
# 队列名称遵循统一命名规范: crawlo:{PROJECT_NAME}:queue:requests
# 当需要自定义队列名称时，取消注释并修改下面这行
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'
SCHEDULER_MAX_QUEUE_SIZE = 200  # 从100增加到200

# ============================== 背压控制配置 ==============================
BACKPRESSURE_RATIO = 0.9  # 从0.8增加到0.9

# ============================== 去重过滤器 ==============================
# 使用Redis过滤器
# FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'


# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['ofweek_standalone.spiders']

# ============================== 中间件 ==============================
# MIDDLEWARES = [
#     'crawlo.middleware.simple_proxy.SimpleProxyMiddleware',
# ]

# ============================== 默认请求头配置 ==============================
# 为DefaultHeaderMiddleware配置默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
}

# ============================== 允许的域名 ==============================
# 为OffsiteMiddleware配置允许的域名
ALLOWED_DOMAINS = ['ee.ofweek.com']

# ============================== MySQL数据库配置 ==============================
MYSQL_HOST = "43.139.14.225"
MYSQL_PORT = 3306
MYSQL_USER = 'picker'
MYSQL_PASSWORD = 'kmcNbbz6TbSihttZ'  # 已设置的MySQL密码
MYSQL_DB = 'stock_share'  # 请根据实际情况修改数据库名
MYSQL_TABLE = 'news_items'  # 默认表名，会被Spider的custom_settings覆盖

# ============================== 数据管道 ==============================
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',     # MySQL 存储（使用asyncmy异步库）
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
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
# 禁用日志轮转以避免并发问题
LOG_MAX_BYTES = 0  # 设置为0禁用日志轮转
LOG_BACKUP_COUNT = 0  # 设置为0禁用日志轮转
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'