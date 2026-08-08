"""errback_examples 项目配置"""

# 爬虫模块
SPIDER_MODULES = ['errback_examples.spiders']

# 基本配置
LOG_LEVEL = 'INFO'
CONCURRENCY = 2
DOWNLOAD_DELAY = 1

# 重试配置
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
