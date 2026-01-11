"""
定时任务配置示例
"""

# 定时任务配置
SCHEDULER_ENABLED = True  # 启用定时任务

SCHEDULER_JOBS = [
    {
        'spider': 'of_week',           # 爬虫名称（对应spider的name属性）
        'cron': '0 */2 * * *',       # 每2小时执行一次
        'enabled': True,              # 任务启用状态
        'args': {},                   # 传递给爬虫的参数
        'priority': 10                # 任务优先级
    },
    {
        'spider': 'of_week',           # 爬虫名称
        'interval': {'minutes': 30},   # 每30分钟执行一次
        'enabled': False,             # 任务禁用状态
        'args': {},
        'priority': 5
    }
]

# 定时任务高级配置（可选）
SCHEDULER_CHECK_INTERVAL = 1      # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3      # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600      # 单个任务超时时间（秒）

# 其他 Crawlo 配置
BOT_NAME = 'ofweek_standalone'

SPIDER_MODULES = ['ofweek_standalone.spiders']
NEWSPIDER_MODULE = 'ofweek_standalone.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure item pipelines
ITEM_PIPELINES = {
    'crawlo.pipelines.ConsolePipeline': 300,
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline': 800,
    # 'crawlo.pipelines.MongoDBPipeline': 800,
}

# Configure database
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'crawlo'
MYSQL_TABLE = 'ofweek_items'
MYSQL_USE_BATCH = True
MYSQL_BATCH_SIZE = 100

MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'crawlo'
MONGO_COLLECTION = 'ofweek_items'

# Other settings
LOG_LEVEL = 'INFO'
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_DELAY = 1

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'ofweek_standalone.middlewares.OfweekStandaloneSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'crawlo.downloader.middlewares.RandomUserAgentMiddleware': 400,
    'crawlo.downloader.middlewares.RetryMiddleware': 500,
}