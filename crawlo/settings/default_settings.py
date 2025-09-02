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

# 下载器选择（三选一）
# DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"  # 支持浏览器指纹
# DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

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
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024   # 最大响应体大小（10MB）
DOWNLOAD_WARN_SIZE = 1024 * 1024      # 响应体警告阈值（1MB）
DOWNLOAD_RETRY_TIMES = MAX_RETRY_TIMES  # 下载器内部重试次数（复用全局）

# ============================== 并发与调度 ==============================

CONCURRENCY = 8                # 单个爬虫的并发请求数
INTERVAL = 5                   # 日志统计输出间隔（秒）
DEPTH_PRIORITY = 1             # 深度优先策略优先级
MAX_RUNNING_SPIDERS = 3        # 最大同时运行的爬虫数

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
# FILTER_CLASS = 'crawlo.filters.redis_filter.AioRedisFilter'  # 分布式去重

# --- Redis 过滤器配置 ---
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'oscar&0503')
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:{REDIS_PORT}/0'
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

# 默认请求头（可被 Spider 覆盖）
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}