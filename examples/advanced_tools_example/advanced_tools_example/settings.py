# -*- coding: UTF-8 -*-
"""
advanced_tools_example 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。
"""

# =================================== 基础配置 ===================================

# 项目基本信息
PROJECT_NAME = 'advanced_tools_example'

# 运行模式
# 可选值: 'standalone', 'distributed', 'auto'
RUN_MODE = 'standalone'

# 并发配置
CONCURRENCY = 8
MAX_RUNNING_SPIDERS = 1
DOWNLOAD_DELAY = 1.0

# 下载器配置
# 可选下载器:
# DOWNLOADER = 'crawlo.downloader.cffi_downloader.CurlCffiDownloader'
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# 队列配置
# 队列类型: 'memory', 'redis', 'auto'
QUEUE_TYPE = 'memory'
# 当使用Redis队列时，可自定义队列名称
# 队列名称遵循统一命名规范: crawlo:{PROJECT_NAME}:queue:requests
# SCHEDULER_QUEUE_NAME = f'crawlo:{PROJECT_NAME}:queue:requests'

# 去重过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# 默认去重管道
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'

# =================================== 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['advanced_tools_example.spiders']

# 默认请求头配置
# 为DefaultHeaderMiddleware配置默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
# 为OffsiteMiddleware配置允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
# PIPELINES = [
#     'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL 存储（使用asyncmy异步库）
#     # 'advanced_tools_example.pipelines.CustomPipeline',  # 用户自定义管道示例
# ]

# =================================== 系统配置 ===================================

# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'advanced_tools_example.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
# MIDDLEWARES = [
#     # 'advanced_tools_example.middlewares.CustomMiddleware',  # 用户自定义中间件示例
# ]

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/advanced_tools_example.log'
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
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'advanced_tools_example'
MYSQL_TABLE = 'advanced_tools_example_data'
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# MongoDB配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'advanced_tools_example_db'
MONGO_COLLECTION = 'advanced_tools_example_items'
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
# PROXY_API_URL = "http://your-proxy-api.com/get-proxy"

# 浏览器指纹模拟（仅 CurlCffi 下载器有效）
CURL_BROWSER_TYPE = "chrome"  # 可选: chrome, edge, safari, firefox 或版本如 chrome136

# 自定义浏览器版本映射（可覆盖默认行为）
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101",
    "safari": "safari184",
    "firefox": "firefox135",
}

# 下载器优化配置
# 下载器健康检查
DOWNLOADER_HEALTH_CHECK = True  # 是否启用下载器健康检查
HEALTH_CHECK_INTERVAL = 60  # 健康检查间隔（秒）

# 请求统计配置
REQUEST_STATS_ENABLED = True  # 是否启用请求统计
STATS_RESET_ON_START = False  # 启动时是否重置统计

# HttpX 下载器专用配置
HTTPX_HTTP2 = True  # 是否启用HTTP/2支持
HTTPX_FOLLOW_REDIRECTS = True  # 是否自动跟随重定向

# AioHttp 下载器专用配置
AIOHTTP_AUTO_DECOMPRESS = True  # 是否自动解压响应
AIOHTTP_FORCE_CLOSE = False  # 是否强制关闭连接

# 通用优化配置
CONNECTION_TTL_DNS_CACHE = 300  # DNS缓存TTL（秒）
CONNECTION_KEEPALIVE_TIMEOUT = 15  # Keep-Alive超时（秒）

# 内存监控配置
# 内存监控扩展默认不启用，如需使用请在项目配置文件中启用
MEMORY_MONITOR_ENABLED = False  # 是否启用内存监控
MEMORY_MONITOR_INTERVAL = 60  # 内存监控检查间隔（秒）
MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用率警告阈值（百分比）
MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用率严重阈值（百分比）