# -*- coding: UTF-8 -*-
"""
ofweek_standalone 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

此配置使用 CrawloConfig.standalone() 工厂方法创建单机模式配置，
适用于开发测试和中小规模数据采集任务。
"""

from crawlo.config import CrawloConfig

# 使用单机模式配置工厂创建配置
config = CrawloConfig.standalone(
    project_name='ofweek_standalone',
    concurrency=8,
    download_delay=1.0
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

# 下载器配置
# 使用HttpX下载器（默认）
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# 使用CurlCffi下载器（可选，需要安装 curl-cffi 库）
# DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# 爬虫模块配置
SPIDER_MODULES = ['ofweek_standalone.spiders']

# 默认请求头配置
# 为DefaultHeaderMiddleware配置默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
# 为OffsiteMiddleware配置允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL 存储（使用asyncmy异步库）
    # 'ofweek_standalone.pipelines.CustomPipeline',  # 用户自定义管道示例
]

# =================================== 系统配置 ===================================

# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'ofweek_standalone.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
# MIDDLEWARES = [
#     'crawlo.middleware.proxy.ProxyMiddleware',  # 代理中间件
# ]

# 日志配置
LOG_LEVEL = 'INFO'  # 设置为 INFO、DEBUG 以便观察代理相关信息
LOG_FILE = 'logs/ofweek_standalone.log'
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
STATS_DUMP = True

# 输出配置
OUTPUT_DIR = 'output'

# =================================== 数据库配置 ===================================

# Redis配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0

# 根据是否有密码生成 URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'


# MySQL配置
# 数据库地址
MYSQL_HOST = "127.0.0.1"
# 数据库端口
MYSQL_PORT = 3306
# 数据库用户名
MYSQL_USER = "root"
# 数据库密码
MYSQL_PASSWORD = ""
# 数据库名
MYSQL_DB = "crawlo"
# 数据库表名
MYSQL_TABLE = "news_items"
# 批量插入配置
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# MySQL SQL生成行为控制配置
MYSQL_AUTO_UPDATE = False  # 是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = True  # 是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_UPDATE_COLUMNS = ()  # 冲突时需更新的列名；指定后 MYSQL_AUTO_UPDATE 失效

# MongoDB配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'ofweek_standalone_db'
MONGO_COLLECTION = 'ofweek_standalone_items'
MONGO_MAX_POOL_SIZE = 200
MONGO_MIN_POOL_SIZE = 20
MONGO_BATCH_SIZE = 100  # 批量插入条数
MONGO_USE_BATCH = False  # 是否启用批量插入

# =================================== 网络配置 ===================================

# 代理配置
# 代理配置（适用于ProxyMiddleware）
# 只要配置了代理列表，中间件就会自动启用
# PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]

# 高级代理配置（适用于ProxyMiddleware）
# 只要配置了代理API URL，中间件就会自动启用
# 使用宇哥虚拟的代理API
# PROXY_API_URL = "http://www.proxy.com"
# 代理失败处理配置
PROXY_MAX_FAILED_ATTEMPTS = 3  # 代理最大失败尝试次数，超过此次数将标记为失效

# 浏览器指纹模拟（仅 CurlCffi 下载器有效）
# BROWSER_FINGERPRINT = True