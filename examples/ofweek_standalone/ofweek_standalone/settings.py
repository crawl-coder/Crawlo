# -*- coding: UTF-8 -*-
"""
ofweek_standalone 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

此配置使用 CrawloConfig.auto() 工厂方法创建自动检测模式配置，
框架会自动检测Redis可用性，可用则使用分布式模式，否则使用单机模式。
"""

from crawlo.config import CrawloConfig

# 使用自动检测模式配置工厂创建配置
config = CrawloConfig.standalone(
    project_name='ofweek_standalone',
    concurrency=8,
    download_delay=1.0,
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['ofweek_standalone.spiders']

# 默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
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
# MIDDLEWARES = {
#     # 'crawlo.middleware.proxy.ProxyMiddleware': 50,
#     'ofweek_standalone.middlewares.OfweekStandaloneMiddleware': 40,  # 用户自定义中间件示例
# }

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/ofweek_standalone.log'
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
LOG_MAX_BYTES = 0 * 1024 * 1024  # 20MB，推荐值
LOG_BACKUP_COUNT = 0  # 10个备份文件，推荐值
# 如果不想要日志轮转，可以设置 LOG_MAX_BYTES = 0
# 当LOG_MAX_BYTES或LOG_BACKUP_COUNT为0时，日志轮转将被禁用，文件会持续增长
STATS_DUMP = True

# 输出配置
OUTPUT_DIR = 'output'

# =================================== 数据库配置 ===================================

# Redis配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0



# MySQL配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'oscar&0503'
MYSQL_DB = 'crawlo_db'
MYSQL_TABLE = 'ofweek_news'
MYSQL_BATCH_SIZE = 20
MYSQL_USE_BATCH = True  # 是否启用批量插入

# MySQL SQL生成行为控制配置
MYSQL_AUTO_UPDATE = False  # 是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = True  # 是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_UPDATE_COLUMNS = ()  # 冲突时需更新的列名；指定后 MYSQL_AUTO_UPDATE 失效

# MongoDB配置
# MONGO_URI = 'mongodb://localhost:27017'
# MONGO_DATABASE = 'ofweek_standalone_db'
# MONGO_COLLECTION = 'ofweek_standalone_items'
# MONGO_MAX_POOL_SIZE = 200
# MONGO_MIN_POOL_SIZE = 20
# MONGO_BATCH_SIZE = 100  # 批量插入条数
# MONGO_USE_BATCH = False  # 是否启用批量插入

# =================================== 代理配置 ===================================

# 简单代理（SimpleProxyMiddleware）
# 配置代理列表后中间件自动启用
# PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]
# 动态代理（ProxyMiddleware）
# 配置代理API URL后中间件自动启用
# PROXY_API_URL = "http://your-proxy-api.com/get-proxy"

# =================================== 定时任务配置 ===================================

# 启用定时任务 - 用于测试
SCHEDULER_ENABLED = True

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',           # 爬虫名称（对应spider的name属性）
        'cron': '*/2 * * * *',       # 每2分钟执行一次
        'enabled': True,              # 任务启用状态
        'args': {},                  # 传递给爬虫的参数
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'kwargs': {}                  # 传递给爬虫的额外参数
    },
    {
        'spider': 'of_week',           # 爬虫名称
        'cron': '0 2 * * *',         # 每天凌晨2点执行
        'enabled': True,              # 任务启用状态
        'args': {'daily': True},      # 传递给爬虫的参数
        'priority': 20,               # 任务优先级
        'max_retries': 2,             # 最大重试次数
        'retry_delay': 120            # 重试延迟（秒）
    }
]

# 关键配置参数（用户可能需要调整）
SCHEDULER_CHECK_INTERVAL = 1           # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3           # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600           # 单个任务超时时间（秒）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True  # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300    # 资源检查间隔（秒）
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600   # 资源泄露检测阈值（秒）

# =================================== 附加监控配置 ===================================

# 启用MySQL监控（用于测试）
MYSQL_MONITOR_ENABLED = True
MYSQL_MONITOR_INTERVAL = 60  # MySQL监控间隔（秒）

# 启用Redis监控（用于测试）
REDIS_MONITOR_ENABLED = True
REDIS_MONITOR_INTERVAL = 60  # Redis监控间隔（秒）

# 启用内存监控（用于测试）
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL = 30  # 内存监控检查间隔（秒）
MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用率警告阈值（百分比）
MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用率严重阈值（百分比）