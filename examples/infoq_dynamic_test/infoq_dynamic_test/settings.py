# -*- coding: UTF-8 -*-
"""
InfoQ 动态下载器测试项目配置文件
====================================
测试 CloakBrowserDownloader 的使用

测试场景：
1. 使用 CloakBrowser 下载器 + 代理API
2. humanize 类人行为模拟
3. GeoIP 自动时区匹配
"""
import os
from datetime import datetime
from crawlo.config import CrawloConfig

# 使用单机模式配置
config = CrawloConfig.standalone(
    project_name='infoq_dynamic_test',
    concurrency=2,  # 降低并发：5 → 2（避免触发百度百科反爬）
    download_delay=2.0,  # 增加延迟：0.5 → 2.0（防止被限流）
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

SPIDER_MODULES = ['infoq_dynamic_test.spiders']

# =================================== DynamicRenderMiddleware 配置 ===================================

# DynamicRenderMiddleware 配置
DYNAMIC_RENDER_DEFAULT_DYNAMIC = True  # 默认使用动态下载器
DYNAMIC_RENDER_DOMAINS = ['www.infoq.cn']
DYNAMIC_RENDER_URL_PATTERNS = []

# =================================== CloakBrowser 配置 ===================================

CLOAKBROWSER_HEADLESS = True  # 无头模式，提升性能
CLOAKBROWSER_HUMANIZE = False  # 禁用类人行为，提升并发速度
CLOAKBROWSER_GEOIP = True  # 启用 GeoIP 自动时区匹配
CLOAKBROWSER_TIMEOUT = 60000  # 60秒总超时（30 → 60，适应慢页面）
CLOAKBROWSER_LOAD_TIMEOUT = 45000  # 45秒页面加载超时（25 → 45，减少超时失败）

# 视口大小
CLOAKBROWSER_VIEWPORT_WIDTH = 1920
CLOAKBROWSER_VIEWPORT_HEIGHT = 1080

# 智能等待
CLOAKBROWSER_WAIT_STRATEGY = "auto"
CLOAKBROWSER_WAIT_TIMEOUT = 10000

# 资源屏蔽（提升性能）
CLOAKBROWSER_BLOCK_RESOURCES = ["image", "font", "media", "stylesheet"]

# 自动滚动（按需开启）
CLOAKBROWSER_AUTO_SCROLL = False  # 百度百科不需要滚动加载
CLOAKBROWSER_SCROLL_DELAY = 500

# 最大标签页数
CLOAKBROWSER_MAX_PAGES = 5

# =================================== HybridDownloader 配置 ===================================

HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "aiohttp"
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "cloakbrowser"  # 使用 CloakBrowser 下载器
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

MYSQL_HOST = None
REDIS_HOST = None

# =================================== 代理配置 ===================================

# 使用代理 API（CloakBrowser 启动时自动获取）
PROXY_API_URL = 'http://123.56.42.142:5000/proxy/getitem/'

# =================================== 重试配置 ===================================

# 启用重试机制（超时请求自动重试）
RETRY_ENABLED = True
RETRY_TIMES = 2  # 最多重试 2 次
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]  # 需要重试的 HTTP 状态码

# =================================== 定时任务（禁用）===================================

SCHEDULER_ENABLED = False
