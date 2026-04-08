# -*- coding: UTF-8 -*-
"""
InfoQ 动态下载器测试项目配置文件
====================================
测试 DynamicRenderMiddleware 和 PlaywrightDownloader 的使用

测试场景：
1. protocol - 默认使用协议下载器
2. dynamic_domain - 通过域名配置启用动态下载器
3. dynamic_meta - 通过请求标记启用动态下载器
"""
import os
from datetime import datetime
from crawlo.config import CrawloConfig

# 使用单机模式配置
config = CrawloConfig.standalone(
    project_name='infoq_dynamic_test',
    concurrency=1,
    download_delay=2.0,
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

SPIDER_MODULES = ['infoq_dynamic_test.spiders']

# =================================== DynamicRenderMiddleware 配置 ===================================

# DynamicRenderMiddleware 配置
# 默认不使用动态下载器，需要用户显式配置
DYNAMIC_RENDER_DEFAULT_DYNAMIC = False
DYNAMIC_RENDER_DOMAINS = ['www.infoq.cn']  # 为 infoq.cn 启用动态下载器
DYNAMIC_RENDER_URL_PATTERNS = []


# =================================== DrissionPage 配置 ===================================

DRISSIONPAGE_HEADLESS = False  # 设置为 False 显示浏览器窗口（有头模式），True 为无头模式
DRISSIONPAGE_TIMEOUT = 30  # 超时时间（秒）
DRISSIONPAGE_BROWSER_PATH = None  # 浏览器路径（None 表示自动检测）
DRISSIONPAGE_USER_DATA_PATH = None  # 用户数据目录
DRISSIONPAGE_PROXY = None  # 代理设置
DRISSIONPAGE_LOAD_IMAGES = True  # 是否加载图片
DRISSIONPAGE_AUTO_SCROLL = False  # 是否自动滚动加载懒加载内容
DRISSIONPAGE_SCROLL_DELAY = 1  # 滚动延迟（秒）
DRISSIONPAGE_MAX_PAGES = 10  # 最大页面数（标签页复用池大小）

# =================================== Playwright 配置 ===================================

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_HEADLESS = False  # 设置为 False 显示浏览器窗口（有头模式），True 为无头模式
PLAYWRIGHT_TIMEOUT = 30000

# 浏览器窗口大小
PLAYWRIGHT_VIEWPORT_WIDTH = 1280   # 窗口宽度（像素）
PLAYWRIGHT_VIEWPORT_HEIGHT = 720   # 窗口高度（像素）

# 智能等待配置
PLAYWRIGHT_WAIT_STRATEGY = "auto"
PLAYWRIGHT_WAIT_TIMEOUT = 10000

# 资源屏蔽（提升性能）
PLAYWRIGHT_BLOCK_RESOURCES = ["image", "font", "media"]
PLAYWRIGHT_BLOCK_ADS = True

# 反检测
PLAYWRIGHT_STEALTH_MODE = True

# 自动滚动
PLAYWRIGHT_AUTO_SCROLL = True
PLAYWRIGHT_SCROLL_DELAY = 500
PLAYWRIGHT_MAX_NO_CONTENT = 2  # 连续2次无新内容认为到底部

# 动态交互示例（在spider中使用）：
# 方式1：滚动加载（已自动启用）
#   yield Request(url, meta={'playwright_auto_scroll': True})
#
# 方式2：点击翻页
#   yield Request(url, meta={
#       'playwright_actions': [
#           {
#               'type': 'click_and_wait',
#               'params': {
#                   'selector': '.next-page-button',  # 下一页按钮选择器
#                   'wait_timeout': 2000,  # 等待超时
#                   'wait_for': 'networkidle'  # 等待策略
#               }
#           }
#       ]
#   })

# =================================== HybridDownloader 配置 ===================================

HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "aiohttp"
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "drissionpage"  # 使用 DrissionPage 下载器
HYBRID_VERBOSE_LOGGING = True  # 启用详细日志，方便调试

# =================================== 日志配置 ===================================

LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/infoq_dynamic_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
LOG_ENCODING = 'utf-8'

# =================================== 管道配置 ===================================

# PIPELINES = {
#     'infoq_dynamic_test.pipelines.ConsolePipeline': 100,
# }

# =================================== 数据库配置（禁用）===================================

# 不使用数据库存储
MYSQL_HOST = None
REDIS_HOST = None

# =================================== 代理配置 ===================================

# 不使用代理
PROXY_LIST = []
PROXY_API_URL = ""

# =================================== 定时任务（禁用）===================================

SCHEDULER_ENABLED = False
