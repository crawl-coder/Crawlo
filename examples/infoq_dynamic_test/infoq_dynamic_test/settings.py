# -*- coding: UTF-8 -*-
"""
InfoQ AI 快讯动态下载器测试项目配置文件
========================================
测试 HybridDownloader + CloakBrowser 对动态页面的解析。

测试场景：
1. 使用 HybridDownloader（协议: httpx，动态: CloakBrowser）
2. dynamic_actions 实现"加载更多"点击
3. XPath 提取 Vue/Nuxt 动态渲染内容
"""
from datetime import datetime
from crawlo.core.config import CrawloConfig

# 使用单机模式配置
config = CrawloConfig.standalone(
    project_name='infoq_dynamic_test',
    concurrency=2,
    download_delay=2.0,
    # CloakBrowser 设置（通过 CrawloConfig 传入确保生效）
    cloakbrowser_headless=True,
    cloakbrowser_humanize=False,
    cloakbrowser_geoip=False,
    cloakbrowser_timeout=60000,
    cloakbrowser_load_timeout=45000,
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

SPIDER_MODULES = ['infoq_dynamic_test.spiders']

# =================================== HybridDownloader 配置 ===================================

HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "httpx"       # 协议下载器
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "cloakbrowser"  # 动态下载器
HYBRID_DYNAMIC_DOMAINS = ["www.infoq.cn"]           # 域名匹配时动态渲染
HYBRID_VERBOSE_LOGGING = True

# =================================== 日志配置 ===================================

LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/infoq_dynamic_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
LOG_ENCODING = 'utf-8'

# =================================== 管道配置（使用 CrawloConfig 默认）===================================

# =================================== 重试配置 ===================================

RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# =================================== 定时任务 ===================================

SCHEDULER_ENABLED = False
