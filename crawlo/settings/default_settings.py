# -*- coding:UTF-8 -*-
"""
默认配置文件
包含 Crawlo 框架的所有默认设置项
"""

from crawlo.settings.setting_manager import EnvConfigManager

# #############################################################################
# 1. 框架基础配置
# #############################################################################

runtime_config = EnvConfigManager.get_runtime_config()

PROJECT_NAME = runtime_config['PROJECT_NAME']           # 项目名称（用于日志、Redis Key 等标识）
VERSION = EnvConfigManager.get_version()                # 项目版本号（从 __version__.py 读取）
RUN_MODE = runtime_config['CRAWLO_MODE']                # 运行模式：standalone | distributed | auto
CONCURRENCY = runtime_config['CONCURRENCY']             # 并发数配置

# ---------------------------------------------------------------------------#
# 爬虫模块
# ---------------------------------------------------------------------------#

SPIDER_MODULES = []                                     # 爬虫模块列表
SPIDER_LOADER_WARN_ONLY = False                         # 爬虫加载器是否只警告不报错

# ---------------------------------------------------------------------------#
# 默认下载器
# ---------------------------------------------------------------------------#

DOWNLOADER = "crawlo.downloader.hybrid_downloader.HybridDownloader"  # 默认使用混合下载器


# #############################################################################
# 2. 调度器与队列配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 下载延迟
# ---------------------------------------------------------------------------#

DOWNLOAD_DELAY = 0.5                                    # 请求延迟（秒）
RANDOMNESS = True                                       # 是否启用随机延迟
RANDOM_RANGE = [0.5, 1.5]                               # 随机延迟范围因子

# ---------------------------------------------------------------------------#
# 深度优先级
# ---------------------------------------------------------------------------#

# 正数: 深度越深优先级越小 → 深度优先（详情页优先出队）
# 负数: 深度越深优先级越大 → 广度优先（列表页优先出队）
# 0:    不按深度调整优先级
DEPTH_PRIORITY = 1                                      # 深度优先级调整系数

# ---------------------------------------------------------------------------#
# 2.1 队列大小
# ---------------------------------------------------------------------------#

SCHEDULER_MAX_QUEUE_SIZE = 50000                        # 调度器队列最大大小（向后兼容，将被下面特定配置覆盖）
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 50000                 # 内存队列最大大小（单机模式）
REDIS_SCHEDULER_MAX_QUEUE_SIZE = 100000                 # Redis 队列最大大小（分布式模式）

# ---------------------------------------------------------------------------#
# 2.2 背压控制
# ---------------------------------------------------------------------------#

# 策略选项: queue_size（推荐）| adaptive（实验性）| composite（高级）
BACKPRESSURE_STRATEGY = 'queue_size'                    # 背压策略
BACKPRESSURE_CHECK_INTERVAL = 0.1                       # 背压检查间隔（秒）
ADAPTIVE_BACKPRESSURE_ENABLED = False                   # 自适应背压（实验性）

# 内存队列背压（单机小规模，纳秒级访问）
MEMORY_BACKPRESSURE_RATIO = 0.5                         # 触发阈值
MEMORY_BACKPRESSURE_DELAY_BASE = 0.5                    # 基础延迟（秒）
MEMORY_BACKPRESSURE_DELAY_MAX = 5.0                     # 最大延迟（秒）
MEMORY_BACKPRESSURE_WARNING_THRESHOLD = 0.4             # 警告阈值
MEMORY_BACKPRESSURE_CRITICAL_THRESHOLD = 0.7            # 危险阈值

# Redis 队列背压（分布式大规模，毫秒级网络延迟）
REDIS_BACKPRESSURE_RATIO = 0.6                          # 触发阈值
REDIS_BACKPRESSURE_DELAY_BASE = 0.5                     # 基础延迟（秒）
REDIS_BACKPRESSURE_DELAY_MAX = 5.0                      # 最大延迟（秒）
REDIS_BACKPRESSURE_WARNING_THRESHOLD = 0.5              # 警告阈值
REDIS_BACKPRESSURE_CRITICAL_THRESHOLD = 0.8             # 危险阈值

# 向后兼容的旧配置（将被队列类型特定配置覆盖）
BACKPRESSURE_RATIO = 0.75
BACKPRESSURE_DELAY_BASE = 0.2
BACKPRESSURE_DELAY_MAX = 3.0
BACKPRESSURE_WARNING_THRESHOLD = 0.7
BACKPRESSURE_CRITICAL_THRESHOLD = 0.9

# 请求生成控制
REQUEST_GENERATION_BATCH_SIZE = 10                      # 请求生成批处理大小
REQUEST_GENERATION_INTERVAL = 0.01                      # 请求生成间隔（秒）
ENABLE_CONTROLLED_REQUEST_GENERATION = False            # 是否启用受控请求生成

# ---------------------------------------------------------------------------#
# 2.3 队列类型
# ---------------------------------------------------------------------------#

QUEUE_TYPE = 'auto'                                     # 队列类型：memory | redis | auto
QUEUE_MAX_RETRIES = 3                                   # 队列操作最大重试次数
QUEUE_TIMEOUT = 300                                     # 队列操作超时时间（秒）
QUEUE_SERIALIZATION_FORMAT = 'pickle'                   # 序列化格式：pickle | json | msgpack


# #############################################################################
# 3. 下载器配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 3.1 协议下载器通用配置
# ---------------------------------------------------------------------------#

DOWNLOAD_TIMEOUT = 15                                   # 下载超时时间（秒）
VERIFY_SSL = True                                       # 是否验证 SSL 证书
CONNECTION_POOL_LIMIT = 100                             # 连接池大小限制
CONNECTION_POOL_LIMIT_PER_HOST = 20                     # 每个主机的连接池大小限制
DOWNLOAD_MAXSIZE = 10 * 1024 * 1024                     # 最大下载大小（字节）
DOWNLOAD_STATS = True                                   # 是否启用下载统计
DOWNLOAD_RETRY_TIMES = 3                                # 下载重试次数

# ---------------------------------------------------------------------------#
# 3.2 重试配置
# ---------------------------------------------------------------------------#

MAX_RETRY_TIMES = 3                                     # 最大重试次数
RETRY_PRIORITY = -100                                   # 重试请求优先级调整（负数降低优先级）
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]       # 需要重试的 HTTP 状态码
IGNORE_HTTP_CODES = [400, 401, 403, 404, 410]           # 不需要重试的 HTTP 状态码
RETRY_EXCEPTIONS = []                                   # 额外的自定义重试异常类型列表

# ---------------------------------------------------------------------------#
# 3.3 协议下载器特有配置
# ---------------------------------------------------------------------------#

# AioHttp 下载器
AIOHTTP_AUTO_DECOMPRESS = True                          # 是否自动解压响应

# Curl-Cffi 下载器（TLS 指纹模拟，可绕过部分 Cloudflare 检测）
CURL_BROWSER_TYPE = "chrome"                            # chrome | edge | safari | firefox
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",                              # chrome99, chrome100, ..., chrome136
    "edge": "edge101",                                  # edge99, edge101
    "safari": "safari184",                              # safari154, safari155, ..., safari184
    "firefox": "firefox135",                            # firefox110, firefox117, ..., firefox135
}

# ---------------------------------------------------------------------------#
# 3.4 混合下载器（HybridDownloader）
# ---------------------------------------------------------------------------#

# 检测优先级：请求标记 > URL 模式 > 域名配置 > 文件扩展名 > 默认
HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "httpx"            # 默认协议下载器
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "cloakbrowser"      # 默认动态下载器
HYBRID_VERBOSE_LOGGING = False                          # 是否启用详细日志
HYBRID_DYNAMIC_URL_PATTERNS = []                        # 需要动态加载的 URL 模式
HYBRID_PROTOCOL_URL_PATTERNS = []                       # 需要协议请求的 URL 模式
HYBRID_DYNAMIC_DOMAINS = []                             # 需要动态加载的域名
HYBRID_PROTOCOL_DOMAINS = []                            # 需要协议请求的域名

# ---------------------------------------------------------------------------#
# 3.4.1 浏览器下载器通用配置
# ---------------------------------------------------------------------------#

# 适用于 Playwright / Camoufox / CloakBrowser / DrissionPage
# 读取优先级：{PREFIX}_{KEY} > BROWSER_{KEY} > 硬编码默认值
# 各下载器可通过自身前缀参数覆盖通用配置（如 CLOAKBROWSER_HEADLESS 覆盖 BROWSER_HEADLESS）

BROWSER_HEADLESS = True                                 # 无头模式
BROWSER_TIMEOUT = 30000                                 # 超时时间（毫秒）
BROWSER_LOAD_TIMEOUT = 10000                            # 页面加载超时（毫秒）
BROWSER_VIEWPORT_WIDTH = 1280                           # 视口宽度
BROWSER_VIEWPORT_HEIGHT = 720                           # 视口高度
BROWSER_MAX_PAGES = 10                                  # 单浏览器最大页面数
BROWSER_PROXY = None                                    # 代理设置
BROWSER_BLOCK_RESOURCES = ["image", "font", "media"]    # 屏蔽的资源类型
BROWSER_AUTO_SCROLL = False                             # 是否自动滚动加载更多内容
BROWSER_SCROLL_DELAY = 500                              # 滚动延迟（毫秒）
BROWSER_WAIT_STRATEGY = "auto"                          # 等待策略：auto | networkidle | domcontentloaded | element
BROWSER_WAIT_TIMEOUT = 10000                            # 智能等待超时时间（毫秒）
BROWSER_WAIT_FOR_ELEMENT = None                         # 等待特定元素选择器
BROWSER_STEALTH_LEVEL = 'basic'                         # 反检测级别：none | basic | advanced
BROWSER_HUMANIZE = False                                # 是否启用拟人化行为模拟

# ---------------------------------------------------------------------------#
# 3.5 Playwright 下载器
# ---------------------------------------------------------------------------#

# 通用参数由 BROWSER_* 统一提供，以下仅保留 Playwright 特有参数

PLAYWRIGHT_BROWSER_TYPE = "chromium"                    # 浏览器类型：chromium | firefox | webkit
PLAYWRIGHT_SINGLE_BROWSER_MODE = True                   # 单浏览器多标签页模式
PLAYWRIGHT_BLOCK_ADS = True                             # 是否屏蔽广告
PLAYWRIGHT_SCROLL_COUNT = 3                             # 滚动次数

# 高级反检测
PLAYWRIGHT_BLOCK_WEBRTC = False                         # 是否阻止 WebRTC 泄露本地 IP
PLAYWRIGHT_HIDE_CANVAS = False                          # 是否为 Canvas 添加随机噪声
PLAYWRIGHT_ALLOW_WEBGL = True                           # 是否启用 WebGL
PLAYWRIGHT_REAL_CHROME = False                          # 是否使用本地 Chrome 浏览器
PLAYWRIGHT_GOOGLE_REFERER = True                        # 是否自动添加 Google Referer
PLAYWRIGHT_IGNORE_HTTPS_ERRORS = True                   # 是否忽略 HTTPS 错误

# ---------------------------------------------------------------------------#
# 3.6 DrissionPage 下载器
# ---------------------------------------------------------------------------#

# 通用参数由 BROWSER_* 统一提供，框架自动完成毫秒→秒转换

DRISSIONPAGE_BROWSER_PATH = None                        # 浏览器路径
DRISSIONPAGE_USER_DATA_PATH = None                      # 用户数据目录
DRISSIONPAGE_LOAD_IMAGES = True                         # 是否加载图片

# ---------------------------------------------------------------------------#
# 3.7 Camoufox 隐身浏览器
# ---------------------------------------------------------------------------#

# 基于 Firefox，内置 Cloudflare 绕过能力
# 安装：pip install camoufox
# 通用参数由 BROWSER_* 统一提供

CAMOUFOX_SOLVE_CLOUDFLARE = True                        # 自动解决 Cloudflare Turnstile（核心能力）
CAMOUFOX_HUMANIZE = True                                # 默认开启拟人化（覆盖 BROWSER_HUMANIZE=False）

# ---------------------------------------------------------------------------#
# 3.8 CloakBrowser 隐身浏览器
# ---------------------------------------------------------------------------#

# 源码级修补的 Chromium（57 项 C++ 补丁），内置全链路指纹伪造
# 安装：pip install cloakbrowser[geoip]
# 通用参数由 BROWSER_* 统一提供

# 特有配置
CLOAKBROWSER_HUMAN_PRESET = "default"                   # humanize 预设：default | fast | slow
CLOAKBROWSER_HUMAN_CONFIG = None                        # humanize 自定义配置（dict，覆盖 preset）
CLOAKBROWSER_GEOIP = False                              # 是否启用 GeoIP 自动时区匹配
CLOAKBROWSER_TIMEZONE = None                            # 手动设置时区（如 "Asia/Shanghai"）
CLOAKBROWSER_LOCALE = None                              # 手动设置语言环境（如 "zh-CN"）
CLOAKBROWSER_BACKEND = "playwright"                     # 后端引擎
CLOAKBROWSER_STEALTH_ARGS = True                        # 是否启用隐身启动参数
CLOAKBROWSER_FINGERPRINT = None                         # 指纹种子（整数，相同种子生成相同指纹）
CLOAKBROWSER_FINGERPRINT_PLATFORM = None                # 指纹平台：windows | mac | linux
CLOAKBROWSER_ARGS = []                                  # 额外浏览器启动参数

# 持久化配置
CLOAKBROWSER_PERSISTENT_CONTEXT = False                 # 是否使用持久化上下文模式
CLOAKBROWSER_USER_DATA_DIR = None                       # 持久化上下文的用户数据目录


# #############################################################################
# 4. 中间件配置
# #############################################################################

# 优先级规则：数值越小，请求阶段越先执行；数值越大，响应阶段越先执行
MIDDLEWARES = {
    # ===== 请求预处理阶段 =====
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware':          100,
    'crawlo.middleware.download_delay.DownloadDelayMiddleware':          200,
    'crawlo.middleware.default_header.DefaultHeaderMiddleware':          300,
    'crawlo.middleware.DynamicRenderMiddleware':                         350,
    'crawlo.middleware.cloudflare_bypass.CloudflareBypassMiddleware':    355,
    'crawlo.middleware.offsite.OffsiteMiddleware':                       400,

    # ===== 响应处理阶段 =====
    'crawlo.middleware.retry.RetryMiddleware':                           600,
    'crawlo.middleware.response_code.ResponseCodeMiddleware':            650,
    'crawlo.middleware.response_filter.ResponseFilterMiddleware':        700,
}


# #############################################################################
# 5. 管道配置
# #############################################################################

PIPELINES = {
    'crawlo.pipelines.console_pipeline.ConsolePipeline': 100,
}


# #############################################################################
# 6. 数据存储配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 6.1 Redis
# ---------------------------------------------------------------------------#

# 键命名规范：
#   crawlo:{PROJECT_NAME}:filter:fingerprint  — 请求去重
#   crawlo:{PROJECT_NAME}:item:fingerprint    — 数据项去重
#   crawlo:{PROJECT_NAME}:queue:requests      — 请求队列
#   crawlo:{PROJECT_NAME}:queue:processing    — 处理中队列
#   crawlo:{PROJECT_NAME}:queue:failed        — 失败队列

REDIS_HOST = '127.0.0.1'                                # Redis 主机地址
REDIS_PORT = 6379                                       # Redis 端口
REDIS_PASSWORD = ''                                     # Redis 密码
REDIS_DB = 0                                            # Redis 数据库编号
REDIS_TTL = 0                                           # 指纹过期时间（0 = 永不过期）
REDIS_POOL_SHARED_MODE = False                          # 连接池共享模式（True=共享单例）
DECODE_RESPONSES = True                                 # Redis 返回是否解码为字符串
FILTER_DEBUG = True                                     # 是否开启去重调试日志

# ---------------------------------------------------------------------------#
# 6.2 MySQL
# ---------------------------------------------------------------------------#

MYSQL_HOST = '127.0.0.1'                                # MySQL 主机地址
MYSQL_PORT = 3306                                       # MySQL 端口
MYSQL_USER = 'root'                                     # MySQL 用户名
MYSQL_PASSWORD = '123456'                               # MySQL 密码
MYSQL_DB = 'crawl_pro'                                  # 数据库名
MYSQL_TABLE = 'crawlo'                                  # 默认表名

# 批量操作
MYSQL_BATCH_SIZE = 200                                  # 批量插入大小
MYSQL_USE_BATCH = True                                  # 是否启用批量插入
MYSQL_BATCH_TIMEOUT = 90                                # 批量操作超时时间（秒）

# 冲突处理策略（三者互斥，按优先级生效）
MYSQL_UPDATE_COLUMNS = ()                               # ON DUPLICATE KEY UPDATE
MYSQL_AUTO_UPDATE = False                               # REPLACE INTO（完全覆盖）
MYSQL_INSERT_IGNORE = False                             # INSERT IGNORE（忽略重复）

# 连接池
MYSQL_POOL_MIN = 2                                      # 最小连接数
MYSQL_POOL_MAX = 30                                     # 最大连接数
MYSQL_POOL_SHARED_MODE = False                          # 连接池共享模式
MYSQL_HEALTH_CHECK_INTERVAL = 300.0                     # 连接池健康检查间隔（秒）
MYSQL_POOL_REPAIR_ATTEMPTS = 3                          # 连接池修复尝试次数

# 执行重试
MYSQL_EXECUTE_MAX_RETRIES = 4                           # SQL 执行最大重试次数
MYSQL_EXECUTE_RETRY_DELAY = 0.8                         # 重试延迟系数

# 表检查
MYSQL_CHECK_TABLE_EXISTS = True                         # 初始化时检查表存在性

# ---------------------------------------------------------------------------#
# 6.3 过滤器
# ---------------------------------------------------------------------------#

DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'
BLOOM_FILTER_CAPACITY = 1000000                         # Bloom 过滤器容量
BLOOM_FILTER_ERROR_RATE = 0.001                         # Bloom 过滤器错误率


# #############################################################################
# 7. 网络配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 7.1 请求头
# ---------------------------------------------------------------------------#

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------#
# 7.2 代理
# ---------------------------------------------------------------------------#

PROXY_LIST = []                                         # 静态代理列表
PROXY_API_URL = ""                                      # 动态代理 API
PROXY_EXTRACTOR = "proxy"                               # 代理提取方式：字段名 或 {"type": "jsonpath", "value": "$.data[0].proxy"}
PROXY_MAX_FAILED_ATTEMPTS = 3                           # 代理最大失败尝试次数

# ---------------------------------------------------------------------------#
# 7.3 域名过滤
# ---------------------------------------------------------------------------#

ALLOWED_DOMAINS = []                                    # 允许的域名列表


# #############################################################################
# 8. 反反爬虫配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 8.1 动态渲染中间件
# ---------------------------------------------------------------------------#

# 与 HybridDownloader 分层协作：中间件设置请求标记，下载器读取标记选择下载方式
DYNAMIC_RENDER_ENABLED = True                           # 是否启用动态渲染中间件
DYNAMIC_RENDER_DEFAULT_DYNAMIC = False                  # 默认是否使用动态下载器
DYNAMIC_RENDER_CACHE_ENABLED = True                     # 是否启用检测结果缓存
DYNAMIC_RENDER_DOMAINS = []                             # 需要动态渲染的域名列表
DYNAMIC_RENDER_STATIC_DOMAINS = []                      # 静态内容域名列表
DYNAMIC_RENDER_URL_PATTERNS = []                        # 动态内容 URL 模式
DYNAMIC_RENDER_STATIC_PATTERNS = []                     # 静态内容 URL 模式

# ---------------------------------------------------------------------------#
# 8.2 Cloudflare 绕过
# ---------------------------------------------------------------------------#

# 当检测到 Cloudflare 挑战页面时，自动使用隐身浏览器重新请求
CLOUDFLARE_BYPASS_MAX_RETRIES = 2                       # 最大绕过重试次数
CLOUDFLARE_BYPASS_DOWNLOADER = 'camoufox'               # 绕过时使用的下载器


# #############################################################################
# 9. 监控与日志配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 9.1 健康检查
# ---------------------------------------------------------------------------#

HEALTH_CHECK_ENABLED = True                             # 是否启用健康检查
HEALTH_CHECK_INTERVAL = 60                              # 健康检查间隔（秒）

# ---------------------------------------------------------------------------#
# 9.2 日志
# ---------------------------------------------------------------------------#

LOG_LEVEL = None                                        # 日志级别：DEBUG | INFO | WARNING | ERROR
LOG_FILE = None                                         # 日志文件路径
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
LOG_ENCODING = 'utf-8'
STATS_DUMP = True                                       # 是否周期性输出统计信息
INTERVAL = 60                                           # 日志输出间隔（秒）
LOG_RETENTION_DAYS = 1                                  # 日志文件保留天数（爬虫关闭时自动清理）

# ---------------------------------------------------------------------------#
# 9.3 内存监控
# ---------------------------------------------------------------------------#

MEMORY_MONITOR_ENABLED = False                          # 是否启用内存监控
MEMORY_MONITOR_INTERVAL = 60                            # 内存监控检查间隔（秒）
MEMORY_WARNING_THRESHOLD = 80.0                         # 内存使用率警告阈值（百分比）
MEMORY_CRITICAL_THRESHOLD = 90.0                        # 内存使用率严重阈值（百分比）

# ---------------------------------------------------------------------------#
# 9.4 MySQL 监控
# ---------------------------------------------------------------------------#

MYSQL_MONITOR_ENABLED = False                           # 是否启用 MySQL 监控
MYSQL_MONITOR_INTERVAL = 300                            # MySQL 监控检查间隔（秒）

# ---------------------------------------------------------------------------#
# 9.5 Redis 监控
# ---------------------------------------------------------------------------#

REDIS_MONITOR_ENABLED = False                           # 是否启用 Redis 监控
REDIS_MONITOR_INTERVAL = 300                            # Redis 监控检查间隔（秒）


# #############################################################################
# 10. 扩展配置
# #############################################################################

EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',              # 定时日志
    'crawlo.extension.log_stats.LogStats',                             # 统计信息
    'crawlo.extension.logging_extension.CustomLoggerExtension',        # 自定义日志
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',          # 内存监控
    'crawlo.extension.mysql_monitor.MySQLMonitorExtension',            # MySQL 监控
    'crawlo.extension.redis_monitor.RedisMonitorExtension',            # Redis 监控
]


# #############################################################################
# 11. 通知系统配置
# #############################################################################

NOTIFICATION_ENABLED = False                            # 是否启用通知系统
NOTIFICATION_CHANNELS = []                              # 启用的通知渠道列表

# ---------------------------------------------------------------------------#
# 钉钉
# ---------------------------------------------------------------------------#

DINGTALK_WEBHOOK = ""                                   # 钉钉机器人 Webhook 地址
DINGTALK_SECRET = ""                                    # 钉钉机器人密钥（加签验证）
DINGTALK_KEYWORDS = []                                  # 钉钉机器人关键词列表
DINGTALK_AT_MOBILES = []                                # 需要 @ 的手机号列表
DINGTALK_AT_USERIDS = []                                # 需要 @ 的用户 ID 列表
DINGTALK_IS_AT_ALL = False                              # 是否 @ 所有人

# ---------------------------------------------------------------------------#
# 飞书
# ---------------------------------------------------------------------------#

FEISHU_WEBHOOK = ""                                     # 飞书机器人 Webhook 地址
FEISHU_SECRET = ""                                      # 飞书机器人密钥（验证）
FEISHU_AT_USERS = []                                    # 需要 @ 的用户 ID 列表
FEISHU_AT_MOBILE = []                                   # 需要 @ 的手机号列表
FEISHU_IS_AT_ALL = False                                # 是否 @ 所有人

# ---------------------------------------------------------------------------#
# 企业微信
# ---------------------------------------------------------------------------#

WECOM_WEBHOOK = ""                                      # 企业微信机器人 Webhook 地址
WECOM_SECRET = ""                                       # 企业微信机器人密钥（验证）
WECOM_AGENT_ID = ""                                     # 企业微信应用 AgentId
WECOM_AT_USERS = []                                     # 需要 @ 的用户 ID 列表
WECOM_AT_MOBILE = []                                    # 需要 @ 的手机号列表
WECOM_IS_AT_ALL = False                                 # 是否 @ 所有人


# #############################################################################
# 12. 定时任务配置
# #############################################################################

# ---------------------------------------------------------------------------#
# 基础配置
# ---------------------------------------------------------------------------#

SCHEDULER_ENABLED = False                               # 是否启用定时任务
SCHEDULER_JOBS = [
    {
        'spider': 'spider_name',      # 爬虫名称（对应spider的name属性）
        'cron': '*/2 * * * *',        # 每2分钟执行一次
        'enabled': True,              # 任务启用状态
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'args': {}                   # 传递给爬虫的参数
    }
]                                     # 定时任务配置列表
SCHEDULER_CHECK_INTERVAL = 1                            # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3                            # 爬虫实例最大并发数（同时运行的不同爬虫数量，非单个爬虫内部并发）
SCHEDULER_JOB_TIMEOUT = 3600                            # 单个任务超时时间（秒）

# ---------------------------------------------------------------------------#
# 资源监控
# ---------------------------------------------------------------------------#

SCHEDULER_RESOURCE_MONITOR_ENABLED = True               # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300                 # 资源检查间隔（秒）
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600                # 资源泄露检测阈值（秒）

# ---------------------------------------------------------------------------#
# 高级配置
# ---------------------------------------------------------------------------#

SCHEDULER_TASK_CLEANUP_INTERVAL = 60                    # 任务清理间隔（秒）
SCHEDULER_STATS_LOGGING_INTERVAL = 300                  # 统计信息记录间隔（秒）
SCHEDULER_GRACEFUL_SHUTDOWN_TIMEOUT = 60                # 优雅关闭超时时间（秒）
SCHEDULER_ERROR_RETRY_DELAY = 30                        # 错误重试延迟（秒）
SCHEDULER_ERROR_LOG_RETENTION_DAYS = 30                 # 错误日志保留天数
SCHEDULER_STATS_RETENTION_HOURS = 24                   # 统计信息保留小时数
SCHEDULER_HEARTBEAT_INTERVAL = 10                       # 心跳间隔（秒）
SCHEDULER_RESOURCE_CLEANUP_ON_STOP = True               # 停止时是否清理资源
SCHEDULER_MAX_RESOURCE_AGE = 7200                       # 资源最大存活时间（秒）


# #############################################################################
# 13. 自适应选择器配置
# #############################################################################

# 当网站改版导致选择器失效时自动重新定位元素（选择器自愈）
# 使用方式：items = response.css('.product', adaptive=True)

ADAPTIVE_STORAGE_BACKEND = 'sqlite'                     # 存储后端：sqlite（单机）| redis（分布式）
ADAPTIVE_SQLITE_PATH = 'adaptive_fingerprints.db'       # SQLite 数据库路径
ADAPTIVE_SIMILARITY_THRESHOLD = 0.0                     # 最低相似度阈值（0-100，0 = 不过滤）


# #############################################################################
# 14. 检查点持久化配置
# #############################################################################

# 支持 Ctrl+C 优雅关闭后从断点续爬
# 保存内容：待处理请求 + 去重指纹 + 统计信息
# 检查点默认始终启用，通过 CLI 参数控制行为：
#   crawlo run myspider                  # 自动恢复检查点
#   crawlo run myspider --fresh           # 忽略检查点，从头开始
#   crawlo run myspider --clean-checkpoint # 清除检查点并从头开始

CHECKPOINT_ENABLED = False                              # 是否启用检查点功能（默认关闭）
CHECKPOINT_STORAGE = 'json'                             # 存储后端：json | sqlite
CHECKPOINT_DIR = None                                   # 存储目录（默认 .checkpoints/{project}/{spider}）
CHECKPOINT_SAVE_ON_SIGNAL = True                        # Ctrl+C 时是否自动保存检查点
