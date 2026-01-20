# -*- coding: UTF-8 -*-
"""
eastmoney_fin_report_crawler 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

此配置使用 CrawloConfig.auto() 工厂方法创建自动检测模式配置，
框架会自动检测Redis可用性，可用则使用分布式模式，否则使用单机模式。
"""

from crawlo.config import CrawloConfig

# 使用自动检测模式配置工厂创建配置
config = CrawloConfig.standalone(
    project_name='eastmoney_fin_report_crawler',
    concurrency=8,
    download_delay=1.0
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['eastmoney_fin_report_crawler.spiders']

# 默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL 存储（使用asyncmy异步库）
    # 'eastmoney_fin_report_crawler.pipelines.CustomPipeline',  # 用户自定义管道示例
]

# =================================== 系统配置 ===================================

# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'eastmoney_fin_report_crawler.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
# MIDDLEWARES = {
#     # 'eastmoney_fin_report_crawler.middlewares.CustomMiddleware': 50,  # 用户自定义中间件示例
# }

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/eastmoney_fin_report_crawler1.log'
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
LOG_MAX_BYTES = 0  # 20MB，推荐值
LOG_BACKUP_COUNT = 0  # 10个备份文件，推荐值
# 如果不想要日志轮转，可以设置 LOG_MAX_BYTES = 0
# 当LOG_MAX_BYTES或LOG_BACKUP_COUNT为0时，日志轮转将被禁用，文件会持续增长


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

STOCK_LIST = 'listed_stock_list'

# MySQL 冲突处理策略（三者互斥，按优先级生效）
MYSQL_UPDATE_COLUMNS = ()      # 优先级最高：主键冲突时更新指定列，使用 ON DUPLICATE KEY UPDATE
MYSQL_AUTO_UPDATE = False      # 优先级中等：是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = True    # 优先级最低：是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_PREFER_ALIAS_SYNTAX = False      # 是否优先使用 AS `alias` 语法，False 则使用 VALUES() 语法
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# MongoDB配置
# MONGO_URI = 'mongodb://localhost:27017'
# MONGO_DATABASE = 'eastmoney_fin_report_crawler_db'
# MONGO_COLLECTION = 'eastmoney_fin_report_crawler_items'
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

# ============================== 自定义配置区域 ==============================
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

# 报告期筛选配置

from utils.report_date_helper import get_target_report_date
REPORT_DATE_FILTER = get_target_report_date()

# 从数据库表listed_stock_list中读取A股数据作为股票列表
from utils.stock_loader import load_a_stocks

# 加载A股股票列表，如果加载失败则使用默认列表
loaded_stocks = load_a_stocks()
if loaded_stocks:
    STOCKS = loaded_stocks
else:
    # 如果数据库加载失败，使用默认的股票列表作为备选
    STOCKS = []