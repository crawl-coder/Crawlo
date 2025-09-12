#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
默认配置文件
包含 Crawlo 框架的所有默认设置项
"""
import os

# 添加环境变量配置工具导入
from crawlo.utils.env_config import get_redis_config, get_runtime_config

# ============================== 项目基础配置 ==============================

# 项目名称（用于日志、Redis Key 等标识）
PROJECT_NAME = get_runtime_config()['PROJECT_NAME']

# 框架版本
VERSION = 1.0

# 运行模式：standalone/distributed/auto
RUN_MODE = get_runtime_config()['CRAWLO_MODE']

# 并发数配置
CONCURRENCY = get_runtime_config()['CONCURRENCY']

# ============================== 爬虫核心配置 ==============================

# 默认下载器
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'

# 请求延迟（秒）
DOWNLOAD_DELAY = 1

# 随机延迟配置
RANDOMNESS = False  # 是否启用随机延迟
RANDOM_RANGE = [0.5, 1.5]  # 随机延迟范围因子，实际延迟 = DOWNLOAD_DELAY * RANDOM_RANGE[0] 到 DOWNLOAD_DELAY * RANDOM_RANGE[1]

# 深度优先级（负数表示深度优先，正数表示广度优先）
DEPTH_PRIORITY = 1

# 调度器队列最大大小
SCHEDULER_MAX_QUEUE_SIZE = 1000

# 调度器队列名称（遵循统一命名规范）
SCHEDULER_QUEUE_NAME = f"crawlo:{PROJECT_NAME}:queue:requests"

# 队列类型：memory/redis/auto
QUEUE_TYPE = 'auto'

# 默认去重管道（根据运行模式自动选择）
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'

# 请求去重过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
# FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter' # 分布式去重

# --- Redis 过滤器配置 ---
# 使用环境变量配置工具获取 Redis 配置
redis_config = get_redis_config()
REDIS_HOST = redis_config['REDIS_HOST']
REDIS_PORT = redis_config['REDIS_PORT']
REDIS_PASSWORD = redis_config['REDIS_PASSWORD']
REDIS_DB = redis_config['REDIS_DB']

# 🔧 根据是否有密码生成不同的 URL 格式
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 统一的Redis key命名规范配置
# REDIS_KEY_PREFIX 已移至各组件中，使用统一的命名规范
# crawlo:{PROJECT_NAME}:filter:fingerprint (请求去重)
# crawlo:{PROJECT_NAME}:item:fingerprint (数据项去重)
# crawlo:{PROJECT_NAME}:queue:requests (请求队列)
# crawlo:{PROJECT_NAME}:queue:processing (处理中队列)
# crawlo:{PROJECT_NAME}:queue:failed (失败队列)

REDIS_TTL = 0  # 指纹过期时间（0 表示永不过期）
CLEANUP_FP = 0  # 程序结束时是否清理指纹（0=不清理）
FILTER_DEBUG = True  # 是否开启去重调试日志
DECODE_RESPONSES = True  # Redis 返回是否解码为字符串

# ============================== 中间件配置 ==============================

MIDDLEWARES = [
    # === 请求预处理阶段 ===
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',  # 1. 忽略无效请求
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',  # 2. 控制请求频率
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',  # 3. 添加默认请求头
    'crawlo.middleware.proxy.ProxyMiddleware',  # 4. 设置代理

    # === 响应处理阶段 ===
    'crawlo.middleware.retry.RetryMiddleware',  # 5. 失败请求重试
    'crawlo.middleware.response_code.ResponseCodeMiddleware',  # 6. 处理特殊状态码
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',  # 7. 响应内容过滤
]

# ============================== 扩展与管道 ==============================

# 数据处理管道（启用的存储方式）
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # 控制台输出
    # 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',     # MySQL 存储（可选）
]

# 根据运行模式自动配置默认去重管道
if RUN_MODE == 'distributed':
    # 分布式模式下添加Redis去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)
else:
    # 单机模式下添加内存去重管道
    PIPELINES.insert(0, DEFAULT_DEDUP_PIPELINE)

# 扩展组件（监控与日志）
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',  # 定时日志
    'crawlo.extension.log_stats.LogStats',  # 统计信息
    'crawlo.extension.logging_extension.CustomLoggerExtension',  # 自定义日志
    # 'crawlo.extension.memory_monitor.MemoryMonitorExtension',  # 内存监控
    # 'crawlo.extension.request_recorder.RequestRecorderExtension',  # 请求记录
    # 'crawlo.extension.performance_profiler.PerformanceProfilerExtension',  # 性能分析
    # 'crawlo.extension.health_check.HealthCheckExtension',  # 健康检查
]

# ============================== 日志与监控 ==============================

LOG_LEVEL = 'INFO'  # 日志级别: DEBUG/INFO/WARNING/ERROR
STATS_DUMP = True  # 是否周期性输出统计信息
LOG_FILE = f'logs/{PROJECT_NAME}.log'  # 日志文件路径
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s： %(message)s'
LOG_ENCODING = 'utf-8'

# ============================== 代理配置 ==============================

PROXY_ENABLED = False  # 是否启用代理
PROXY_API_URL = "https://api.proxyprovider.com/get"  # 代理获取接口（请替换为真实地址）

# 代理提取方式（支持字段路径或函数）
PROXY_EXTRACTOR = "proxy"  # 如返回 {"proxy": "http://1.1.1.1:8080"}

# 代理刷新控制
PROXY_REFRESH_INTERVAL = 60  # 代理刷新间隔（秒）
PROXY_API_TIMEOUT = 10  # 请求代理 API 超时时间

# ============================== Curl-Cffi 特有配置 ==============================

# 浏览器指纹模拟（仅 CurlCffi 下载器有效）
CURL_BROWSER_TYPE = "chrome"  # 可选: chrome, edge, safari, firefox 或版本如 chrome136

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
CURL_RANDOMIZE_DELAY = False  # 是否启用随机延迟
CURL_RETRY_BACKOFF = True  # 是否启用指数退避重试

# 默认请求头（可被 Spider 覆盖）
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
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

# ============================== Selenium 下载器配置 ==============================

# Selenium 基础配置
SELENIUM_BROWSER_TYPE = "chrome"  # 浏览器类型: chrome, firefox, edge
SELENIUM_HEADLESS = True  # 是否无头模式
SELENIUM_TIMEOUT = 30  # 超时时间（秒）
SELENIUM_LOAD_TIMEOUT = 10  # 页面加载超时时间（秒）
SELENIUM_WINDOW_WIDTH = 1920  # 窗口宽度
SELENIUM_WINDOW_HEIGHT = 1080  # 窗口高度
SELENIUM_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器
SELENIUM_ENABLE_JS = True  # 是否启用JavaScript
SELENIUM_PROXY = None  # 代理设置
SELENIUM_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
SELENIUM_MAX_TABS_PER_BROWSER = 10  # 单浏览器最大标签页数量

# ============================== Playwright 下载器配置 ==============================

# Playwright 基础配置
PLAYWRIGHT_BROWSER_TYPE = "chromium"  # 浏览器类型: chromium, firefox, webkit
PLAYWRIGHT_HEADLESS = True  # 是否无头模式
PLAYWRIGHT_TIMEOUT = 30000  # 超时时间（毫秒）
PLAYWRIGHT_LOAD_TIMEOUT = 10000  # 页面加载超时时间（毫秒）
PLAYWRIGHT_VIEWPORT_WIDTH = 1920  # 视口宽度
PLAYWRIGHT_VIEWPORT_HEIGHT = 1080  # 视口高度
PLAYWRIGHT_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器
PLAYWRIGHT_PROXY = None  # 代理设置
PLAYWRIGHT_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10  # 单浏览器最大页面数量

# 通用优化配置
CONNECTION_TTL_DNS_CACHE = 300  # DNS缓存TTL（秒）
CONNECTION_KEEPALIVE_TIMEOUT = 15  # Keep-Alive超时（秒）