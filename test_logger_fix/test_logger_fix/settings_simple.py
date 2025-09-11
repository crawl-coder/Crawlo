# -*- coding: UTF-8 -*-
"""
test_logger_fix 项目配置文件（简化版）
=============================
基于 Crawlo 框架的简化爬虫项目配置。
适合快速开始和小型项目。
"""

import os
from crawlo.config import CrawloConfig

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'test_logger_fix'
VERSION = '1.0.0'

# ============================== 基本配置 ==============================
# 使用配置工厂创建基本配置
CONFIG = CrawloConfig.standalone(
    concurrency=4,
    download_delay=1.0
)

# 获取配置
locals().update(CONFIG.to_dict())

# ============================== 网络请求配置 ==============================
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"
DOWNLOAD_TIMEOUT = 30
VERIFY_SSL = True

# ============================== 并发配置 ==============================
CONCURRENCY = 4
DOWNLOAD_DELAY = 1.0

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

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/test_logger_fix.log'
STATS_DUMP = True

# ============================== 自定义配置 ==============================
# 在此处添加项目特定的配置项