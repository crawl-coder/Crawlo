# -*- coding: UTF-8 -*-
"""
不限速动态浏览器下载器配置
===========================
直接使用 CloakBrowser 下载器（绕过 HybridDownloader），
无下载延迟，最大化采集速度。

适用场景：对反爬不敏感或已配置代理的方案。
"""

from datetime import datetime
from crawlo.config import CrawloConfig

config = CrawloConfig.standalone(
    project_name='infoq_dynamic_test',
    concurrency=5,           # 高并发
    download_delay=0.0,      # 不限速
)
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================
SPIDER_MODULES = ['infoq_dynamic_test.spiders']

# =================================== 下载器：直接使用 CloakBrowser ===================================
DOWNLOADER = 'crawlo.downloader.cloakbrowser_downloader.CloakBrowserDownloader'

# =================================== 浏览器通用配置 ===================================
BROWSER_HEADLESS = True
BROWSER_TIMEOUT = 60000
BROWSER_LOAD_TIMEOUT = 30000
BROWSER_VIEWPORT_WIDTH = 1920
BROWSER_VIEWPORT_HEIGHT = 1080
BROWSER_MAX_PAGES = 8
BROWSER_BLOCK_RESOURCES = ["image", "font", "media", "stylesheet"]
BROWSER_AUTO_SCROLL = False
BROWSER_WAIT_STRATEGY = "domcontentloaded"
BROWSER_WAIT_TIMEOUT = 8000

# =================================== CloakBrowser 特有配置 ===================================
CLOAKBROWSER_HUMANIZE = False     # 关闭拟人化，提升速度
CLOAKBROWSER_GEOIP = True

# =================================== 禁用限速中间件 ===================================
MIDDLEWARES = {
    'crawlo.middleware.default_header.DefaultHeaderMiddleware': 300,
    'crawlo.middleware.retry.RetryMiddleware': 600,
    'crawlo.middleware.response_code.ResponseCodeMiddleware': 650,
    'crawlo.middleware.response_filter.ResponseFilterMiddleware': 700,
}
# 注意：移除了 DownloadDelayMiddleware、OffsiteMiddleware、DynamicRenderMiddleware

# =================================== 日志配置 ===================================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/infoq_dynamic_no_limit_{datetime.now():%Y%m%d_%H%M%S}.log'
LOG_ENCODING = 'utf-8'

# =================================== 数据库配置（禁用）===================================
MYSQL_HOST = None
REDIS_HOST = None

# =================================== 定时任务（禁用）===================================
SCHEDULER_ENABLED = False
