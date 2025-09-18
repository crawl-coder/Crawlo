# -*- coding: UTF-8 -*-
"""
Playwright 和 Selenium 下载器示例项目配置文件
"""

# 项目名称
PROJECT_NAME = 'playwright_selenium_example'

# 运行模式
RUN_MODE = 'standalone'

# 并发配置
CONCURRENCY = 1
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 1

# 下载器配置 - 可以根据需要切换
# DOWNLOADER = 'crawlo.downloader.selenium_downloader.SeleniumDownloader'
# DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'  # 默认使用aiohttp
DOWNLOADER = 'crawlo.downloader.playwright_downloader.PlaywrightDownloader'  # 使用Playwright

# Playwright 配置
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_TIMEOUT = 30000
PLAYWRIGHT_LOAD_TIMEOUT = 10000
PLAYWRIGHT_VIEWPORT_WIDTH = 1920
PLAYWRIGHT_VIEWPORT_HEIGHT = 1080

# Selenium 配置
SELENIUM_BROWSER_TYPE = "chrome"
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 30
SELENIUM_LOAD_TIMEOUT = 10
SELENIUM_WINDOW_WIDTH = 1920
SELENIUM_WINDOW_HEIGHT = 1080

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 队列配置
QUEUE_TYPE = 'memory'
SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'

# 去重过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# 爬虫模块配置
SPIDER_MODULES = ['playwright_selenium_example.spiders']

# 中间件
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# 数据管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]

# 扩展组件
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
]

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'
STATS_DUMP = True

# 输出配置
OUTPUT_DIR = 'output'