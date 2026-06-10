# -*- coding: UTF-8 -*-
"""
ofweek_distributed 项目配置文件（分布式版）
=============================
基于 Crawlo 框架的分布式爬虫项目配置。
适合大规模数据采集和多节点部署。

此配置使用 CrawloConfig.distributed() 工厂方法创建分布式模式配置，
支持多节点协同工作，适用于大规模数据采集任务。
"""

from crawlo.config import CrawloConfig

# ---------------------------------------------------------------------------#
# Redis（分布式模式依赖）
# ---------------------------------------------------------------------------#

REDIS_HOST = '127.0.0.1'                                # Redis 主机地址
REDIS_PORT = 6379                                       # Redis 端口
REDIS_PASSWORD = ''                                     # Redis 密码
REDIS_USER = ''                                         # Redis 用户名（Redis 6.0+ ACL）
REDIS_DB = 0                                            # Redis 数据库编号

# 使用分布式模式配置工厂创建配置
config = CrawloConfig.distributed(
    project_name='ofweek_distributed',
    concurrency=8,          # 分布式模式下并发数（每个 worker）
    download_delay=1.0,     # 请求间隔（秒）
)

# 将配置转换为当前模块的全局变量
globals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['ofweek_distributed.spiders']

# 默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 400,
    'crawlo.pipelines.ConsolePipeline': 500,
}

# =================================== 系统配置 ===================================

# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'ofweek_distributed.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
# MIDDLEWARES = {
#     # 'ofweek_distributed.middlewares.CustomMiddleware': 50,  # 用户自定义中间件示例
# }

# 日志配置
from datetime import datetime
LOG_LEVEL = 'INFO'
LOG_FILE = f'logs/ofweek_distributed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码

# 输出配置
OUTPUT_DIR = 'output'

# =================================== 数据库配置 ===================================

# Redis配置（已由 CrawloConfig.distributed() 设置，此处供参考）
# REDIS_HOST = '127.0.0.1'
# REDIS_PORT = 6379
# REDIS_PASSWORD = ''
# REDIS_DB = 0

# MySQL配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'crawlo'
MYSQL_PASSWORD = 'crawlo123'
MYSQL_DB = 'crawlo_deployer'
MYSQL_TABLE = 'ofweek_news'
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = True

# =================================== 代理配置 ===================================

# 简单代理（SimpleProxyMiddleware）
# 配置代理列表后中间件自动启用
# PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]

# 动态代理（ProxyMiddleware）
# 配置代理API URL后中间件自动启用
# PROXY_API_URL = "http://your-proxy-api.com/get-proxy"