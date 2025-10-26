# -*- coding: UTF-8 -*-
"""
scrapy_ofweek 项目配置文件
==========================
Scrapy 框架爬虫项目配置。

为确保与 Crawlo 的公平对比，使用相同的配置参数：
- 并发数：8
- 下载延迟：1.0秒
- 日志级别：INFO
"""

BOT_NAME = 'scrapy_ofweek'

SPIDER_MODULES = ['scrapy_ofweek.spiders']
NEWSPIDER_MODULE = 'scrapy_ofweek.spiders'

# 遵守 robots.txt 规则（与 Crawlo 保持一致）
ROBOTSTXT_OBEY = False

# 配置最大并发数（与 Crawlo 的 CONCURRENCY=8 保持一致）
CONCURRENT_REQUESTS = 8

# 配置下载延迟（与 Crawlo 的 DOWNLOAD_DELAY=1.0 保持一致）
DOWNLOAD_DELAY = 1.0

# 禁用 cookies（除非爬虫特别指定）
COOKIES_ENABLED = True

# 配置默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 启用或禁用扩展
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# 配置 Item Pipelines
ITEM_PIPELINES = {
    'scrapy_ofweek.pipelines.JsonWriterPipeline': 300,
}

# 启用和配置 AutoThrottle 扩展（与 Crawlo 的自动限速对齐）
AUTOTHROTTLE_ENABLED = False

# 配置日志
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy_ofweek.log'
LOG_ENCODING = 'utf-8'

# 设置请求优先级
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
