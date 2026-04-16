# -*- coding: UTF-8 -*-
"""
listed_company_executive_crawler 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

此配置使用 CrawloConfig.auto() 工厂方法创建自动检测模式配置，
框架会自动检测Redis可用性，可用则使用分布式模式，否则使用单机模式。
"""

from datetime import datetime
from crawlo.config import CrawloConfig

# =================================== 0. 基础配置 ===================================
# 
# 本配置为单机版模板，适合开发测试和小规模生产环境。
# 
# 如需分布式配置，请使用 CrawloConfig.distributed() 并参考分布式部署文档。
# 
# 配置说明：
#   - concurrency: 单个爬虫的并发请求数（默认8，生产环境可调整为16）
#   - download_delay: 请求间隔延迟（秒），根据目标网站反爬强度调整
#   - max_running_spiders: 同时运行的最大爬虫数（单机版通常1-5个）

config = CrawloConfig.standalone(
    project_name='listed_company_executive_crawler',
    concurrency=8,              # 并发请求数：开发8，生产16-32
    download_delay=1.0,         # 下载延迟（秒）
    max_running_spiders=3       # 最大同时运行爬虫数
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 1. 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['listed_company_executive_crawler.spiders']

# 默认请求头
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://emweb.securities.eastmoney.com",
    "Pragma": "no-cache",
    "Referer": "https://emweb.securities.eastmoney.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\""
}

# 允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
# PIPELINES = {
#     'crawlo.pipelines.mysql_pipeline.MySQLPipeline': 500,  # MySQL 存储（使用asyncmy异步库）
#     'listed_company_executive_crawler.pipelines.CustomPipeline': 600,  # 用户自定义管道示例
# }

# =================================== 2. 系统配置 ===================================
# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'listed_company_executive_crawler.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
# 优先级规则：数值越小，请求阶段越先执行；数值越大，响应阶段越先执行
MIDDLEWARES = {
    'listed_company_executive_crawler.middlewares.ProxyMiddleware': 500,  # 代理中间件
}

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/listed_company_executive_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
# =================================== 3. 数据库配置 ===================================

# =================================== 3.1 Redis 数据库配置 ===================================

# Redis基础配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0

# Redis连接池配置
# REDIS_POOL_SHARED_MODE = False  # Redis连接池管理模式，True为共享模式（单例），False为独立模式（每个爬虫实例独立连接池）
# REDIS_MAX_CONNECTIONS = 20  # Redis连接池最大连接数
# REDIS_SOCKET_CONNECT_TIMEOUT = 5  # Redis连接超时时间（秒）
# REDIS_SOCKET_TIMEOUT = 30  # Redis socket超时时间（秒）
# REDIS_HEALTH_CHECK_INTERVAL = 30  # Redis健康检查间隔（秒）
# REDIS_RETRY_ON_TIMEOUT = True  # Redis超时是否重试
# REDIS_DECODE_RESPONSES = True  # Redis返回是否解码为字符串
# REDIS_TTL = 0  # Redis键过期时间（0表示永不过期）
# FILTER_DEBUG = True  # 是否开启去重调试日志
# CONNECTION_POOL_LIMIT = 100  # 连接池大小限制
# CONNECTION_POOL_LIMIT_PER_HOST = 20  # 每个主机的连接池大小限制
# CONNECTION_TTL_DNS_CACHE = 300  # DNS缓存TTL（秒）

# =================================== 3.2 MySQL 数据库配置 ===================================

# MySQL基础配置
MYSQL_HOST = "183.238.148.251"
MYSQL_PORT = 13016
MYSQL_USER = "data_collection"
MYSQL_PASSWORD = "BLDzcgz8sPx=%YJtfjk"
MYSQL_DB = 'internal_collection'
MYSQL_TABLE = ''

# MySQL连接池配置
# MYSQL_POOL_SHARED_MODE = False  # MySQL连接池管理模式，True为共享模式（单例），False为独立模式（每个爬虫实例独立连接池）
# MYSQL_POOL_MIN = 2  # 最小连接数
# MYSQL_POOL_MAX = 30  # 最大连接数
# MYSQL_POOL_REPAIR_ATTEMPTS = 3  # 连接池修复尝试次数，默认3次
# MYSQL_HEALTH_CHECK_INTERVAL = 300.0  # 连接池健康检查间隔（秒），默认5分钟

# MySQL 冲突处理策略（三者互斥，按优先级生效）
MYSQL_UPDATE_COLUMNS = ()      # 优先级最高：主键冲突时更新指定列，使用 ON DUPLICATE KEY UPDATE
MYSQL_AUTO_UPDATE = False      # 优先级中等：是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = True    # 优先级最低：是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_PREFER_ALIAS_SYNTAX = True      # 是否优先使用 AS `alias` 语法，False 则使用 VALUES() 语法
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# 重试配置
MAX_RETRY_TIMES = 3  # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]  # 需要重试的HTTP状态码
RETRY_PRIORITY = 10  # 重试请求的优先级
RETRY_EXCEPTIONS = [  # 需要重试的异常类型
    'httpx.TimeoutException',
    'httpx.ConnectError',
    'httpx.ReadTimeout',
    'httpx.ConnectTimeout',
    'httpx.WriteTimeout',
    'httpx.PoolTimeout',
]

# =================================== 3.3 MongoDB 数据库配置 ===================================

# MongoDB基础配置
# MONGO_URI = 'mongodb://localhost:27017'
# MONGO_DATABASE = 'listed_company_executive_crawler_db'
# MONGO_COLLECTION = 'listed_company_executive_crawler_items'
# MONGO_MAX_POOL_SIZE = 200
# MONGO_MIN_POOL_SIZE = 20
# MONGO_BATCH_SIZE = 100  # 批量插入条数
# MONGO_USE_BATCH = False  # 是否启用批量插入

# =================================== 4. 定时任务配置 ===================================

# 启用定时任务 - 默认关闭
SCHEDULER_ENABLED = False

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'listed_company_executive_crawler.spiders.{{spider_name}}',  # 爬虫名称（对应spider的name属性）
        'cron': '*/2 * * * *',       # 每2分钟执行一次
        'enabled': True,              # 任务启用状态
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'args': {},                  # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    },
    {
        'spider': 'listed_company_executive_crawler.spiders.{{spider_name}}',  # 爬虫名称
        'cron': '0 2 * * *',         # 每天凌晨2点执行
        'enabled': True,              # 任务启用状态
        'priority': 20,               # 任务优先级
        'max_retries': 2,             # 最大重试次数
        'retry_delay': 120,           # 重试延迟（秒）
        'args': {'daily': True},      # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    }
]

# 关键配置参数（用户可能需要调整）
SCHEDULER_CHECK_INTERVAL = 1           # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3           # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600           # 单个任务超时时间（秒）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True  # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300    # 资源检查间隔（秒）
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600   # 资源泄露检测阈值（秒）

# =================================== 5. 资源监控配置 ===================================

# 内存监控配置
# MEMORY_MONITOR_ENABLED = False  # 是否启用内存监控
# MEMORY_MONITOR_INTERVAL = 60  # 内存监控检查间隔（秒）
# MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用率警告阈值（百分比）
# MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用率严重阈值（百分比）

# MySQL监控配置
# MYSQL_MONITOR_ENABLED = False  # 是否启用MySQL监控
# MYSQL_MONITOR_INTERVAL = 120  # MySQL监控检查间隔（秒）

# Redis监控配置
# REDIS_MONITOR_ENABLED = False  # 是否启用Redis监控
# REDIS_MONITOR_INTERVAL = 120  # Redis监控检查间隔（秒）

# 输出配置
OUTPUT_DIR = 'output'

# =================================== 6. 代理配置 ===================================

# 简单代理（SimpleProxyMiddleware）
# 配置代理列表后中间件自动启用
# PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]

# 动态代理（ProxyMiddleware）
# 配置代理API URL后中间件自动启用
PROXY_API_URL = 'http://123.56.42.142:5000/proxy/getitem/'

# =================================== 6.1 动态渲染配置 ===================================

# DynamicRenderMiddleware - 自动检测页面是否需要动态渲染
# 与 HybridDownloader 分层协作：中间件检测页面类型，设置请求标记
# DYNAMIC_RENDER_ENABLED = True  # 是否启用动态渲染检测
# DYNAMIC_RENDER_DEFAULT_DYNAMIC = False  # 默认是否使用动态下载器（默认为 False，需用户显式配置）
# DYNAMIC_RENDER_CACHE_ENABLED = True  # 是否启用检测结果缓存
# 
# # 动态内容 URL 模式（正则表达式列表）- 用户显式配置需要动态渲染的 URL
# DYNAMIC_RENDER_URL_PATTERNS = [
#     r'/#/',  # Hash 路由（SPA）
#     r'/app/',  # 应用页面
#     r'/spa/',  # SPA 页面
# ]
# 
# # 静态内容 URL 模式（正则表达式列表）
# DYNAMIC_RENDER_STATIC_PATTERNS = [
#     r'\.(html?|htm)$',
#     r'\.(xml|json|rss|atom)$',
# ]
# 
# # 需要动态渲染的域名列表（用户显式配置）
# DYNAMIC_RENDER_DOMAINS = ['www.example.com', 'spa.example.com']
# 
# # 静态内容域名列表
# DYNAMIC_RENDER_STATIC_DOMAINS = ['static.example.com']

# =================================== 6.2 Playwright 下载器配置 ===================================

# PlaywrightDownloader - 动态浏览器下载器
# PLAYWRIGHT_BROWSER_TYPE = "chromium"  # 浏览器类型：chromium, firefox, webkit
# PLAYWRIGHT_HEADLESS = True  # 是否无头模式
# PLAYWRIGHT_TIMEOUT = 30000  # 默认超时时间（毫秒）
# PLAYWRIGHT_LOAD_TIMEOUT = 10000  # 页面加载超时时间（毫秒）
# PLAYWRIGHT_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
# PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10  # 每个浏览器的最大页面数

# ===== 智能等待配置 =====
# PLAYWRIGHT_WAIT_STRATEGY = "auto"  # 等待策略：auto, networkidle, domcontentloaded, element, custom
# PLAYWRIGHT_WAIT_TIMEOUT = 10000  # 等待超时时间（毫秒）
# PLAYWRIGHT_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器

# ===== 资源屏蔽配置（提升性能）=====
# PLAYWRIGHT_BLOCK_RESOURCES = ["image", "font", "media"]  # 屏蔽的资源类型
# PLAYWRIGHT_BLOCK_ADS = True  # 是否屏蔽广告

# ===== 反检测配置 =====
# PLAYWRIGHT_STEALTH_LEVEL = 'basic'  # 反检测级别: none, basic, advanced

# ===== 自动滚动配置 =====
# PLAYWRIGHT_AUTO_SCROLL = False  # 是否自动滚动加载更多内容
# PLAYWRIGHT_SCROLL_COUNT = 3  # 滚动次数
# PLAYWRIGHT_SCROLL_DELAY = 500  # 滚动延迟（毫秒）

# ===== 代理配置 =====
# PLAYWRIGHT_PROXY = None  # 代理服务器配置，例如 "http://proxy:8080" 或 {"server": "http://proxy:8080"}

# =================================== 6.3 HybridDownloader 配置 ===================================

# HybridDownloader - 智能混合下载器
# HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "aiohttp"  # 默认协议下载器：aiohttp, httpx, curl_cffi
# HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "playwright"  # 默认动态下载器：playwright, drissionpage
# HYBRID_VERBOSE_LOGGING = False  # 是否启用详细日志
# 
# # URL 模式配置
# HYBRID_DYNAMIC_URL_PATTERNS = []  # 需要动态加载的 URL 模式
# HYBRID_PROTOCOL_URL_PATTERNS = []  # 需要协议请求的 URL 模式
# 
# # 域名配置
# HYBRID_DYNAMIC_DOMAINS = []  # 需要动态加载的域名
# HYBRID_PROTOCOL_DOMAINS = []  # 需要协议请求的域名

# =================================== 7. 通知系统配置 ===================================
# 通知系统默认禁用，如需启用请取消注释并配置相关参数
NOTIFICATION_ENABLED = False  # 启用通知系统 - 默认禁用
NOTIFICATION_CHANNELS = []  # 启用的通知渠道列表，例如 ['dingtalk', 'feishu', 'wecom', 'email', 'sms']
# 
# 钉钉通知配置示例：
# DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
# DINGTALK_SECRET = "your_secret"  # 可选
# DINGTALK_KEYWORDS = ["爬虫"]  # 可选
# DINGTALK_AT_MOBILES = ["13800138000"]  # 可选，需要@的手机号
# DINGTALK_IS_AT_ALL = False  # 可选，是否@所有人
# 
# 飞书通知配置示例：
# FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook"
# FEISHU_SECRET = "your_secret"  # 可选
# 
# 企业微信通知配置示例：
# WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key"
# WECOM_MENTIONED_LIST = ["user_id1", "user_id2"]  # 可选
# WECOM_MENTIONED_MOBILE_LIST = ["13800138000"]  # 可选
# 
# 邮件通知配置示例：
# EMAIL_HOST = "smtp.example.com"
# EMAIL_PORT = 587
# EMAIL_USERNAME = "your_email@example.com"
# EMAIL_PASSWORD = "your_password"
# EMAIL_RECIPIENTS = ["recipient@example.com"]
# 
# 短信通知配置示例：
# SMS_ACCESS_KEY_ID = "your_access_key_id"
# SMS_ACCESS_KEY_SECRET = "your_access_key_secret"
# SMS_SIGN_NAME = "签名名称"
# SMS_TEMPLATE_CODE = "SMS_123456789"
# SMS_PHONE_NUMBERS = ["13800138000"]

# # 钉钉通知配置
# # DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"  # 钉钉机器人 Webhook 地址
# # DINGTALK_SECRET = "SECxxx"   # 钉钉机器人密钥（可选，用于加签）
# # DINGTALK_KEYWORDS = ["爬虫"] # 钉钉机器人关键词（可选，用于通过关键词验证）
# # DINGTALK_AT_MOBILES = ["13800138000"] # 需要@的手机号列表（可选）
# # DINGTALK_AT_USERIDS = ["userid1"] # 需要@的用户ID列表（可选）
# # DINGTALK_IS_AT_ALL = False # 是否@所有人（可选，默认False）
# 
# # 飞书通知配置
# # FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID"  # 飞书机器人 Webhook 地址
# # FEISHU_SECRET = "YOUR_SECRET"     # 飞书机器人密钥（可选，用于验证）
# # FEISHU_AT_USERS = ["open_id1"]   # 需要@的用户ID列表（可选）
# # FEISHU_AT_MOBILE = ["13800138000"]  # 需要@的手机号列表（可选）
# # FEISHU_IS_AT_ALL = False # 是否@所有人（可选，默认False）
# 
# # 企业微信通知配置
# # WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_WEBHOOK_KEY"  # 企业微信机器人 Webhook 地址
# # WECOM_SECRET = "YOUR_SECRET"      # 企业微信机器人密钥（可选，用于验证）
# # WECOM_AGENT_ID = "1000001"       # 企业微信应用 AgentId
# # WECOM_AT_USERS = ["UserID1"]     # 需要@的用户ID列表（可选）
# # WECOM_AT_MOBILE = ["13800138000"]   # 需要@的手机号列表（可选）
# # WECOM_IS_AT_ALL = False # 是否@所有人（可选，默认False）
# 
# # 邮件通知配置
# # EMAIL_SMTP_SERVER = "smtp.gmail.com"  # SMTP服务器地址
# # EMAIL_SMTP_PORT = 587   # SMTP服务器端口
# # EMAIL_USERNAME = "your_email@gmail.com"     # 邮箱用户名
# # EMAIL_PASSWORD = "your_app_password"     # 邮箱密码或授权码
# # EMAIL_FROM = "your_email@gmail.com"         # 发送方邮箱地址
# # EMAIL_TO = ["recipient@example.com"]           # 接收方邮箱地址列表
# 
# # 短信通知配置
# # SMS_PROVIDER = "alibaba"       # 短信服务提供商（如: alibaba, tencent等）
# # SMS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"  # 短信服务 Access Key ID
# # SMS_ACCESS_KEY_SECRET = "YOUR_ACCESS_KEY_SECRET"  # 短信服务 Access Key Secret
# # SMS_SIGN_NAME = "YourSignName"      # 短信签名名称
# # SMS_TEMPLATE_CODE = "SMS_XXXXX"  # 短信模板代码
# 
# # 通知系统高级配置
# # NOTIFICATION_RETRY_ENABLED = True  # 是否启用通知发送失败重试
# # NOTIFICATION_RETRY_TIMES = 3      # 通知发送失败重试次数
# # NOTIFICATION_RETRY_DELAY = 5      # 通知发送失败重试延迟（秒）
# # NOTIFICATION_TIMEOUT = 30         # 通知发送超时时间（秒）