#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os

# ============================== 核心配置 ==============================
PROJECT_NAME = 'crawlo'
VERSION = 1.0

# ============================== 网络请求配置 (通用) ==============================
# 指定使用的下载器
# DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
# DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"  # 使用 curl-cffi 下载器
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# 下载超时时间 (秒)
DOWNLOAD_TIMEOUT = 60

# 是否验证 SSL 证书
VERIFY_SSL = True

# 是否使用持久化会话 (aiohttp 特有)
USE_SESSION = True

# --- 请求延迟 ---
# 固定请求延迟 (秒)
DOWNLOAD_DELAY = 0.5
# 随机延迟范围系数 (例如 0.75-1.25 倍基础延迟)
RANDOM_RANGE = (0.75, 1.25)
# 是否启用随机化延迟
RANDOMNESS = True  # aiohttp 使用, curl-cffi 也兼容

# --- 重试策略 ---
# 最大重试次数
MAX_RETRY_TIMES = 3
# 重试请求的优先级调整
RETRY_PRIORITY = -1
# 需要重试的 HTTP 状态码
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
# 忽略并直接标记成功的状态码 (不重试)
IGNORE_HTTP_CODES = [403, 404]
# 允许通过的状态码 (空列表表示不限制)
ALLOWED_CODES = []

# --- 连接与数据大小 ---
# 最大并发客户端数 (连接池大小)
CONNECTION_POOL_LIMIT = 100

# 最大允许的响应体大小 (字节)，超过则抛出异常
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024  # 10MB

# 响应体大小警告阈值 (字节)，超过则记录警告日志
DOWNLOAD_WARN_SIZE = 1024 * 1024  # 1MB

# 下载失败时的重试次数 (下载器局部重试)
DOWNLOAD_RETRY_TIMES = MAX_RETRY_TIMES  # 复用全局重试次数

# ============================== 并发与调度配置 ==============================
# 单个爬虫内部的并发请求数 (由 Engine 控制)
CONCURRENCY = 8

# 请求间隔 (秒，用于日志等)
INTERVAL = 5

# 深度优先策略优先级
DEPTH_PRIORITY = 1

# 最多同时运行的爬虫实例数量 (由 CrawlerProcess 调度控制)
MAX_RUNNING_SPIDERS = 3

# ============================== 数据存储配置 ==============================
# --- MySQL ---
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'crawl'
MYSQL_TABLE = 'crawled_data'
MYSQL_BATCH_SIZE = 100

# MySQL连接池配置
MYSQL_FLUSH_INTERVAL = 5
MYSQL_POOL_MIN = 5
MYSQL_POOL_MAX = 20
MYSQL_ECHO = False

# --- MongoDB ---
MONGO_URI = 'mongodb://user:password@host:27017'
MONGO_DATABASE = 'scrapy_data'
MONGO_COLLECTION = 'crawled_items'
MONGO_MAX_POOL_SIZE = 200
MONGO_MIN_POOL_SIZE = 20

# ============================== 去重过滤配置 ==============================
# 请求指纹保存目录 (文件过滤器使用)
REQUEST_DIR = '.'

# 指定使用的去重过滤器类
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
# FILTER_CLASS = 'crawlo.filters.redis_filter.AioRedisFilter' # 可切换为 Redis 过滤器

# --- Redis 过滤器配置 ---
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'oscar&0503')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:{REDIS_PORT}/0'
REDIS_KEY = 'request_fingerprint'
# 0 or None 表示持久化，>0表示过期时间(秒)
REDIS_TTL = 0
# 程序结束时是否删除 Redis 中的指纹
CLEANUP_FP = 0
FILTER_DEBUG = True
# Redis 读取时是否解码为字符串
DECODE_RESPONSES = True

# ============================== 中间件配置 ==============================
MIDDLEWARES = [
    # --- 请求预处理阶段 ---
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',  # 1. 优先忽略无效请求
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',  # 2. 下载延迟（控制频率）
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',  # 3. 设置默认请求头
    'crawlo.middleware.proxy.ProxyMiddleware',  # 4. 设置代理（在发送前）

    # --- 响应处理阶段 ---
    'crawlo.middleware.retry.RetryMiddleware',  # 5. 重试失败请求（可换代理）
    'crawlo.middleware.response_code.ResponseCodeMiddleware',  # 6. 处理状态码（如 404、500）
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',  # 7. 响应内容过滤（最后处理）
]

# ============================== 扩展组件配置 ==============================
# 启用的数据处理管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline', # 可选：存入 MySQL
]

# 启用的扩展组件
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats'
]

# ============================== 监控日志配置 ==============================
# 日志级别
LOG_LEVEL = 'DEBUG'
# 是否周期性输出统计信息
STATS_DUMP = True

# ============================== IP 代理配置 ==============================
PROXY_ENABLED = True

# 代理API的URL地址（必填）
PROXY_API_URL = "https://api.proxyprovider.com/get"

# 代理提取方式：支持字符串路径（如 'proxy' 或 'data.proxy.http'）或自定义函数
# 如果返回的是嵌套结构，例如 {"proxy": {"http": "...", "https": "..."}}
PROXY_EXTRACTOR = "proxy"  # 可改为其他字段路径，如 "data.result.proxy"

# 代理刷新间隔（秒），避免频繁请求API
PROXY_REFRESH_INTERVAL = 60

# 请求代理API的超时时间（秒）
PROXY_API_TIMEOUT = 10



# ============================== Curl-Cffi 下载器特有配置 ==============================
# 浏览器指纹模拟类型
# 可选值: "chrome", "edge", "safari", "firefox" 或具体版本如 "chrome136"
CURL_BROWSER_TYPE = "chrome"

# 自定义浏览器版本映射 (可选，用于覆盖默认映射或添加新映射)
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101",
    "safari": "safari184",
    "firefox": "firefox135",
    # 示例：使用较旧的版本进行测试
    # "chrome_legacy": "chrome110",
    # 示例：如果 curl-cffi 更新了，可以直接在这里更新映射
    # "chrome": "chrome140",
}

# 默认请求头 (可被 Spider 或中间件覆盖)
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}
