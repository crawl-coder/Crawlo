# -*- coding: utf-8 -*-

# Scrapy settings for ofweek_standalone project
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入Crawlo配置
from crawlo.config import CrawloConfig

# ==================== 项目基本信息 ====================
BOT_NAME = 'of_week'

SPIDER_MODULES = ['ofweek_standalone.spiders']
NEWSPIDER_MODULE = 'ofweek_standalone.spiders'

# ==================== Crawlo核心配置 ====================
# 使用自动模式，框架会自动检测Redis可用性并切换到分布式模式
CrawloConfig.auto()

# ==================== 自定义项目配置 ====================
# 项目名称（用于生成默认队列名称）
PROJECT_NAME = 'ofweek_standalone'

# 日志级别
LOG_LEVEL = 'INFO'

# 最大并发请求数
CONCURRENT_REQUESTS = 16

# 下载延迟（秒）
DOWNLOAD_DELAY = 1

# 是否启用随机下载延迟
RANDOMIZE_DOWNLOAD_DELAY = True

# ==================== Redis配置 ====================
# Redis连接信息
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
# REDIS_PASSWORD = 'your_password'  # 如果有密码请取消注释
REDIS_DB = 0

# 合并后的Redis数据清理参数
# 0 = 不清理数据（默认，支持断点续爬）
# 1 = 清理所有Redis数据
CLEANUP_REDIS_DATA = 0

# Redis键的TTL（0表示永不过期）
REDIS_TTL = 0

# ==================== 自定义配置 ====================
# 自定义请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 管道配置
ITEM_PIPELINES = {
    'ofweek_standalone.pipelines.ConsolePipeline': 300,
}

# 中间件配置
DOWNLOADER_MIDDLEWARES = {
    # 'ofweek_standalone.middlewares.OfweekStandaloneDownloaderMiddleware': 543,
}