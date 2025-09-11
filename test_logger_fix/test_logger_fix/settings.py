# -*- coding: UTF-8 -*-
"""
test_logger_fix 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

🎯 快速开始：

# 方式1：使用默认单机模式（推荐）
from crawlo.crawler import CrawlerProcess
process = CrawlerProcess()  # 无需任何配置

# 方式2：使用配置工厂
from crawlo.config import CrawloConfig
config = CrawloConfig.standalone()  # 单机模式
config = CrawloConfig.distributed(redis_host='192.168.1.100')  # 分布式模式
process = CrawlerProcess(settings=config.to_dict())

# 方式3：使用环境变量
from crawlo.config import CrawloConfig
config = CrawloConfig.from_env()  # 从环境变量读取
"""
import os
from crawlo.config import CrawloConfig

# ============================== 项目基本信息 ==============================
PROJECT_NAME = 'test_logger_fix'
VERSION = '1.0.0'

# ============================== 运行模式选择 ==============================

# 🎯 选择一种配置方式：

# 方式1：使用配置工厂（推荐）
# 单机模式（默认）
CONFIG = CrawloConfig.standalone(
    concurrency=8,
    download_delay=1.0
)

# 分布式模式（去掉注释并修改 Redis 地址）
# CONFIG = CrawloConfig.distributed(
#     redis_host='127.0.0.1',
#     redis_password='your_password',  # 如果有密码
#     project_name='test_logger_fix',
#     concurrency=16,
#     download_delay=1.0
# )

# 自动检测模式
# CONFIG = CrawloConfig.auto(concurrency=12)

# 方式2：从环境变量读取（适合部署）
# CONFIG = CrawloConfig.from_env()

# 方式3：使用预设配置
# from crawlo.config import Presets
# CONFIG = Presets.development()  # 开发环境
# CONFIG = Presets.production()   # 生产环境

# 获取最终配置
locals().update(CONFIG.to_dict())

# ============================== 网络请求配置 ==============================

# 下载器选择（推荐使用 CurlCffi，支持浏览器指纹模拟）
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"     # HTTP/2 支持
# DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"  # 支持浏览器指纹
# DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"  # 轻量级选择

# 请求超时与安全
DOWNLOAD_TIMEOUT = 30
VERIFY_SSL = True
USE_SESSION = True

# 请求延迟控制（防反爬）
DOWNLOAD_DELAY = 1.0
RANDOM_RANGE = (0.8, 1.2)
RANDOMNESS = True

# 重试策略
MAX_RETRY_TIMES = 3
RETRY_PRIORITY = -1
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]
ALLOWED_CODES = []

# 连接池配置
CONNECTION_POOL_LIMIT = 50
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024    # 10MB
DOWNLOAD_WARN_SIZE = 1024 * 1024       # 1MB
DOWNLOAD_RETRY_TIMES = MAX_RETRY_TIMES  # 下载器内部重试次数（复用全局）

# 下载统计配置
DOWNLOADER_STATS = True  # 是否启用下载器统计功能
DOWNLOAD_STATS = True  # 是否记录下载时间和大小统计

# ============================== 并发与调度配置 ==============================

CONCURRENCY = 8
INTERVAL = 5
DEPTH_PRIORITY = 1
MAX_RUNNING_SPIDERS = 3

# 运行模式选择：'standalone'(单机), 'distributed'(分布式), 'auto'(自动检测)
RUN_MODE = 'standalone'  # 默认单机模式，简单易用

# ============================== 队列配置（支持分布式） ==============================

# 队列类型：'auto'（自动选择）, 'memory'（内存队列）, 'redis'（分布式队列）
QUEUE_TYPE = 'auto'
SCHEDULER_MAX_QUEUE_SIZE = 2000
SCHEDULER_QUEUE_NAME = f'crawlo:test_logger_fix:queue:requests'  # 使用统一命名规范
QUEUE_MAX_RETRIES = 3
QUEUE_TIMEOUT = 300

# 大规模爬取优化
LARGE_SCALE_BATCH_SIZE = 1000  # 批处理大小
LARGE_SCALE_CHECKPOINT_INTERVAL = 5000  # 进度保存间隔
LARGE_SCALE_MAX_MEMORY_USAGE = 500  # 最大内存使用量（MB）

# ============================== 数据存储配置 ==============================

# --- MySQL 配置 ---
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
MYSQL_DB = os.getenv('MYSQL_DB', 'test_logger_fix')
MYSQL_TABLE = 'test_logger_fix_data'
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# --- MongoDB 配置 ---
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DATABASE = 'test_logger_fix_db'
MONGO_COLLECTION = 'test_logger_fix_items'
MONGO_MAX_POOL_SIZE = 200
MONGO_MIN_POOL_SIZE = 20
MONGO_BATCH_SIZE = 100  # 批量插入条数
MONGO_USE_BATCH = False  # 是否启用批量插入

# ============================== 去重过滤配置 ==============================

REQUEST_DIR = '.'

# 根据运行模式自动选择去重管道
# 单机模式默认使用内存去重管道
# 分布式模式默认使用Redis去重管道
if RUN_MODE == 'distributed':
    # 分布式模式下默认使用Redis去重管道
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.RedisDedupPipeline'
else:
    # 单机模式下默认使用内存去重管道
    DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.MemoryDedupPipeline'

# 去重过滤器（推荐分布式项目使用 Redis 过滤器）
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
# FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'  # 分布式去重

# --- Redis 配置（用于分布式去重和队列） ---
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# 根据是否有密码生成 URL
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

# Redis key配置已移至各组件中，使用统一的命名规范
# crawlo:{project_name}:filter:fingerprint (请求去重)
# crawlo:{project_name}:item:fingerprint (数据项去重)
# crawlo:{project_name}:queue:requests (请求队列)
# crawlo:{project_name}:queue:processing (处理中队列)
# crawlo:{project_name}:queue:failed (失败队列)

REDIS_TTL = 0
CLEANUP_FP = 0
FILTER_DEBUG = True
DECODE_RESPONSES = True

# ============================== 中间件配置 ==============================

MIDDLEWARES = [
    # === 请求预处理阶段 ===
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    
    # === 响应处理阶段 ===
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# ============================== 数据管道配置 ==============================

# 数据处理管道（启用的存储方式）
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    # 'test_logger_fix.pipelines.DatabasePipeline',        # 自定义数据库管道
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL 存储
    # 'crawlo.pipelines.mongo_pipeline.MongoPipeline',      # MongoDB 存储
]

# 根据运行模式自动配置默认去重管道
if RUN_MODE == 'distributed':
    # 分布式模式下添加Redis去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
else:
    # 单机模式下添加内存去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)

# ============================== 扩展组件 ==============================

EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
    # 'crawlo.extension.memory_monitor.MemoryMonitorExtension',  # 内存监控
    # 'crawlo.extension.request_recorder.RequestRecorderExtension',  # 请求记录
    # 'crawlo.extension.performance_profiler.PerformanceProfilerExtension',  # 性能分析
    # 'crawlo.extension.health_check.HealthCheckExtension',  # 健康检查
]

# ============================== 扩展配置 ==============================

# 内存监控扩展配置
# MEMORY_MONITOR_ENABLED = True  # 是否启用内存监控
# MEMORY_MONITOR_INTERVAL = 60  # 内存检查间隔（秒）
# MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用警告阈值（百分比）
# MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用严重阈值（百分比）

# 请求记录扩展配置
# REQUEST_RECORDER_ENABLED = True  # 是否启用请求记录
# REQUEST_RECORDER_OUTPUT_DIR = 'requests_log'  # 请求记录输出目录
# REQUEST_RECORDER_MAX_FILE_SIZE = 10 * 1024 * 1024  # 单个记录文件最大大小（字节）

# 性能分析扩展配置
# PERFORMANCE_PROFILER_ENABLED = True  # 是否启用性能分析
# PERFORMANCE_PROFILER_OUTPUT_DIR = 'profiling'  # 性能分析输出目录
# PERFORMANCE_PROFILER_INTERVAL = 300  # 定期保存分析结果间隔（秒）

# 健康检查扩展配置
# HEALTH_CHECK_ENABLED = True  # 是否启用健康检查
# HEALTH_CHECK_INTERVAL = 60  # 健康检查间隔（秒）

# ============================== 日志配置 ==============================

LOG_LEVEL = 'INFO'
STATS_DUMP = True
LOG_FILE = f'logs/test_logger_fix.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s： %(message)s'
LOG_ENCODING = 'utf-8'

# ============================== 代理配置 ==============================

PROXY_ENABLED = False
PROXY_API_URL = ""  # 请填入真实的代理API地址
PROXY_EXTRACTOR = "proxy"
PROXY_REFRESH_INTERVAL = 60
PROXY_API_TIMEOUT = 10

# ============================== 浏览器指纹配置 ==============================

# CurlCffi 下载器专用配置
CURL_BROWSER_TYPE = "chrome"
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101",
    "safari": "safari184",
    "firefox": "firefox135",
}

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ============================== 下载器优化配置 ==============================

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

# ============================== 开发与调试 ==============================

# 开发模式配置
DEBUG = False
TESTING = False

# 性能监控
ENABLE_PERFORMANCE_MONITORING = True
MEMORY_USAGE_WARNING_THRESHOLD = 500  # MB

# ============================== 自定义配置区域 ==============================
# 在此处添加项目特定的配置项

# 示例：目标网站特定配置
# TARGET_DOMAIN = '{{domain}}'
# MAX_PAGES_PER_DOMAIN = 10000
# CUSTOM_RATE_LIMIT = 1.5