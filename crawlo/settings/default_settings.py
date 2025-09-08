#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
==================================
         Crawlo 项目配置文件
==================================
说明：
- 所有配置项均已按功能模块分类。
- 支持通过环境变量覆盖部分敏感配置（如 Redis、MySQL 密码等）。
- 可根据需求启用/禁用组件（如 MySQL、Redis、Proxy 等）。
"""
import os

# ============================== 核心信息 ==============================
PROJECT_NAME = 'crawlo'

# ============================== 网络请求配置 ==============================

# 下载器选择（支持三种方式）
# 方式1: 直接指定类路径
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
# DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"  # 支持浏览器指纹
# DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"    # 支持HTTP/2

# 方式2: 使用简化名称（推荐）
# DOWNLOADER_TYPE = 'aiohttp'     # 可选: aiohttp, httpx, curl_cffi, cffi

# 方式3: 在Spider中动态选择
# 可以在Spider类中设置 custom_settings = {'DOWNLOADER_TYPE': 'httpx'}

# 请求超时与安全
DOWNLOAD_TIMEOUT = 30          # 下载超时时间（秒）
VERIFY_SSL = True              # 是否验证 SSL 证书
USE_SESSION = True             # 是否使用持久化会话（aiohttp 特有）

# 请求延迟控制
DOWNLOAD_DELAY = 1.0          # 基础延迟（秒）
RANDOM_RANGE = (0.8, 1.2)    # 随机延迟系数范围
RANDOMNESS = True              # 是否启用随机延迟

# 重试策略
MAX_RETRY_TIMES = 3            # 最大重试次数
RETRY_PRIORITY = -1            # 重试请求的优先级调整
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]  # 触发重试的状态码
IGNORE_HTTP_CODES = [403, 404] # 直接标记成功、不重试的状态码
ALLOWED_CODES = []             # 允许的状态码（空表示不限制）

# 连接与响应大小限制
CONNECTION_POOL_LIMIT = 50    # 最大并发连接数（连接池大小）
CONNECTION_POOL_LIMIT_PER_HOST = 20  # 每个主机的连接池大小
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024   # 最大响应体大小（10MB）
DOWNLOAD_WARN_SIZE = 1024 * 1024      # 响应体警告阈值（1MB）
DOWNLOAD_RETRY_TIMES = MAX_RETRY_TIMES  # 下载器内部重试次数（复用全局）

# 下载统计配置
DOWNLOADER_STATS = True        # 是否启用下载器统计功能
DOWNLOAD_STATS = True          # 是否记录下载时间和大小统计

# ============================== 并发与调度 ==============================

CONCURRENCY = 8                # 单个爬虫的并发请求数
INTERVAL = 5                   # 日志统计输出间隔（秒）
DEPTH_PRIORITY = 1             # 深度优先策略优先级
MAX_RUNNING_SPIDERS = 3        # 最大同时运行的爬虫数

# ============================== 队列配置 ==============================

# 🎯 运行模式选择：'standalone'(单机), 'distributed'(分布式), 'auto'(自动检测)
RUN_MODE = 'standalone'         # 默认单机模式，简单易用

# 队列类型选择：'memory'(内存), 'redis'(分布式), 'auto'(自动选择)
QUEUE_TYPE = 'memory'           # 默认内存队列，无需外部依赖
SCHEDULER_MAX_QUEUE_SIZE = 2000  # 调度器队列最大容量
SCHEDULER_QUEUE_NAME = 'crawlo:requests'  # Redis 队列名称
QUEUE_MAX_RETRIES = 3          # 队列操作最大重试次数
QUEUE_TIMEOUT = 300            # 队列操作超时时间（秒）

# 大规模爬取优化配置
LARGE_SCALE_BATCH_SIZE = 1000   # 批处理大小
LARGE_SCALE_CHECKPOINT_INTERVAL = 5000  # 进度保存间隔
LARGE_SCALE_MAX_MEMORY_USAGE = 500  # 最大内存使用量（MB）

# ============================== 数据存储配置 ==============================

# --- MySQL 配置 ---
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'crawl'
MYSQL_TABLE = 'crawlo'
MYSQL_BATCH_SIZE = 100         # 批量插入条数

# MySQL 连接池
MYSQL_FLUSH_INTERVAL = 5       # 缓存刷新间隔（秒）
MYSQL_POOL_MIN = 5
MYSQL_POOL_MAX = 20
MYSQL_ECHO = False             # 是否打印 SQL 日志

# --- MongoDB 配置 ---
MONGO_URI = 'mongodb://user:password@host:27017'
MONGO_DATABASE = 'scrapy_data'
MONGO_COLLECTION = 'crawled_items'
MONGO_MAX_POOL_SIZE = 200
MONGO_MIN_POOL_SIZE = 20

# ============================== 去重过滤配置 ==============================

# 请求指纹存储目录（文件过滤器使用）
REQUEST_DIR = '.'

# 去重过滤器类（二选一）
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
# FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter' # 分布式去重

# --- Redis 过滤器配置 ---
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')  # 默认无密码
# 🔧 根据是否有密码生成不同的 URL 格式
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
REDIS_KEY = 'request_fingerprint'        # Redis 中存储指纹的键名
REDIS_TTL = 0                            # 指纹过期时间（0 表示永不过期）
CLEANUP_FP = 0                           # 程序结束时是否清理指纹（0=不清理）
FILTER_DEBUG = True                      # 是否开启去重调试日志
DECODE_RESPONSES = True                  # Redis 返回是否解码为字符串

# ============================== 中间件配置 ==============================

MIDDLEWARES = [
    # === 请求预处理阶段 ===
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',   # 1. 忽略无效请求
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',   # 2. 控制请求频率
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',   # 3. 添加默认请求头
    'crawlo.middleware.proxy.ProxyMiddleware',                    # 4. 设置代理

    # === 响应处理阶段 ===
    'crawlo.middleware.retry.RetryMiddleware',                    # 5. 失败请求重试
    'crawlo.middleware.response_code.ResponseCodeMiddleware',     # 6. 处理特殊状态码
    'crawlo.middleware.response_filter.ResponseFilterMiddleware', # 7. 响应内容过滤
]

# ============================== 扩展与管道 ==============================

# 数据处理管道（启用的存储方式）
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',          # 控制台输出
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',     # MySQL 存储（可选）
]

# 扩展组件（监控与日志）
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',         # 定时日志
    'crawlo.extension.log_stats.LogStats',                        # 统计信息
    'crawlo.extension.logging_extension.CustomLoggerExtension',   # 自定义日志
]

# ============================== 日志与监控 ==============================

LOG_LEVEL = 'INFO'                         # 日志级别: DEBUG/INFO/WARNING/ERROR
STATS_DUMP = True                          # 是否周期性输出统计信息
LOG_FILE = f'logs/{PROJECT_NAME}.log'      # 日志文件路径
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s： %(message)s'
LOG_ENCODING = 'utf-8'

# ============================== 代理配置 ==============================

PROXY_ENABLED = False                       # 是否启用代理
PROXY_API_URL = "https://api.proxyprovider.com/get"  # 代理获取接口（请替换为真实地址）

# 代理提取方式（支持字段路径或函数）
PROXY_EXTRACTOR = "proxy"                  # 如返回 {"proxy": "http://1.1.1.1:8080"}

# 代理刷新控制
PROXY_REFRESH_INTERVAL = 60                # 代理刷新间隔（秒）
PROXY_API_TIMEOUT = 10                     # 请求代理 API 超时时间

# ============================== Curl-Cffi 特有配置 ==============================

# 浏览器指纹模拟（仅 CurlCffi 下载器有效）
CURL_BROWSER_TYPE = "chrome"               # 可选: chrome, edge, safari, firefox 或版本如 chrome136

# 自定义浏览器版本映射（可覆盖默认行为）
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101", 
    "safari": "safari184",
    "firefox": "firefox135",
    # 示例：旧版本测试
    # "chrome_legacy": "chrome110",
}

# Curl-Cffi 优化配置
CURL_RANDOMIZE_DELAY = False     # 是否启用随机延迟
CURL_RETRY_BACKOFF = True        # 是否启用指数退避重试

# 默认请求头（可被 Spider 覆盖）
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

# ============================== 下载器优化配置 ==============================

# 下载器健康检查
DOWNLOADER_HEALTH_CHECK = True   # 是否启用下载器健康检查
HEALTH_CHECK_INTERVAL = 60       # 健康检查间隔（秒）

# 请求统计配置
REQUEST_STATS_ENABLED = True     # 是否启用请求统计
STATS_RESET_ON_START = False     # 启动时是否重置统计

# HttpX 下载器专用配置
HTTPX_HTTP2 = True               # 是否启用HTTP/2支持
HTTPX_FOLLOW_REDIRECTS = True    # 是否自动跟随重定向

# AioHttp 下载器专用配置
AIOHTTP_AUTO_DECOMPRESS = True   # 是否自动解压响应
AIOHTTP_FORCE_CLOSE = False      # 是否强制关闭连接

# 通用优化配置
CONNECTION_TTL_DNS_CACHE = 300   # DNS缓存TTL（秒）
CONNECTION_KEEPALIVE_TIMEOUT = 15 # Keep-Alive超时（秒）