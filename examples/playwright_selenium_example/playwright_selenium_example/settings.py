# -*- coding: UTF-8 -*-
"""
playwright_selenium_example 项目配置文件
=====================================
基于 Crawlo 框架的 Playwright/Selenium 下载器示例项目配置。
"""

import os

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'playwright_selenium_example'

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# ============================== 运行模式 ==============================
RUN_MODE = 'standalone'

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
CONCURRENCY = 2
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 2.0

# ============================== 下载器配置 ==============================
# 使用 Playwright 下载器
DOWNLOADER = 'crawlo.downloader.playwright_downloader.PlaywrightDownloader'
# 或使用 Selenium 下载器
# DOWNLOADER = 'crawlo.downloader.selenium_downloader.SeleniumDownloader'

# ============================== 队列配置 ==============================
QUEUE_TYPE = 'memory'

# ============================== 去重过滤器 ==============================
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# ============================== 默认去重管道 ==============================
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'

# ============================== 爬虫模块配置 ==============================
SPIDER_MODULES = ['playwright_selenium_example.spiders']

# ============================== 用户自定义中间件 ==============================
# 注意：框架默认中间件已自动加载，此处可添加或覆盖默认中间件

# 中间件列表（框架默认中间件 + 用户自定义中间件）
MIDDLEWARES = [
    # 'playwright_selenium_example.middlewares.CustomMiddleware',  # 示例自定义中间件
]

# ============================== 用户自定义数据管道 ==============================
# 注意：框架默认管道已自动加载，此处可添加或覆盖默认管道

# 数据处理管道列表（框架默认管道 + 用户自定义管道）
PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]

# ============================== 用户自定义扩展组件 ==============================
# 注意：框架默认扩展已自动加载，此处可添加或覆盖默认扩展

# 扩展组件列表（框架默认扩展 + 用户自定义扩展）
EXTENSIONS = [
    # 'crawlo.extension.memory_monitor.MemoryMonitorExtension',  # 内存监控
]

# ============================== 日志配置 ==============================
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/{PROJECT_NAME}.log'
STATS_DUMP = True

# ============================== 输出配置 ==============================
OUTPUT_DIR = 'output'

# ============================== Playwright 配置 ==============================
PLAYWRIGHT_BROWSER_TYPE = "chromium"  # 浏览器类型: chromium, firefox, webkit
PLAYWRIGHT_HEADLESS = False  # 是否无头模式（示例中设置为False以便观察）
PLAYWRIGHT_TIMEOUT = 30000  # 超时时间（毫秒）
PLAYWRIGHT_LOAD_TIMEOUT = 10000  # 页面加载超时时间（毫秒）
PLAYWRIGHT_VIEWPORT_WIDTH = 1920  # 视口宽度
PLAYWRIGHT_VIEWPORT_HEIGHT = 1080  # 视口高度
PLAYWRIGHT_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器
PLAYWRIGHT_PROXY = None  # 代理设置
PLAYWRIGHT_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 5  # 单浏览器最大页面数量

# ============================== Selenium 配置 ==============================
SELENIUM_BROWSER_TYPE = "chrome"  # 浏览器类型: chrome, firefox, edge
SELENIUM_HEADLESS = False  # 是否无头模式（示例中设置为False以便观察）
SELENIUM_TIMEOUT = 30  # 超时时间（秒）
SELENIUM_LOAD_TIMEOUT = 10  # 页面加载超时时间（秒）
SELENIUM_WINDOW_WIDTH = 1920  # 窗口宽度
SELENIUM_WINDOW_HEIGHT = 1080  # 窗口高度
SELENIUM_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器
SELENIUM_ENABLE_JS = True  # 是否启用JavaScript
SELENIUM_PROXY = None  # 代理设置
SELENIUM_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
SELENIUM_MAX_TABS_PER_BROWSER = 5  # 单浏览器最大标签页数量