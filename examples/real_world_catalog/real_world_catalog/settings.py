# -*- coding: UTF-8 -*-
"""
real_world_catalog 项目配置
===========================

一个"整站抓取" cookbook 示例：列表页 → 分页 → 详情页 → 去重 → 存储
→ 监控告警。支持单机与分布式两种模式（见 run.py）。
"""

import os

from crawlo.core.config import CrawloConfig


def _distributed() -> bool:
    """分布式模式由环境变量 / 命令行开关控制。"""
    return os.environ.get("CRAWLO_MODE", "standalone") == "distributed"


config = CrawloConfig.auto(
    project_name="real_world_catalog",
    concurrency=8,
    download_delay=0.2,
)

locals().update(config.to_dict())

# ── 爬虫发现 ──
SPIDER_MODULES = ["real_world_catalog.spiders"]

# ── 队列：单机 memory / 分布式 redis_stream ──
if _distributed():
    QUEUE_TYPE = "redis_stream"
    # 分布式运行参数（示例值，生产按需调整）
    DISTRIBUTED_WORKER_IDLE_TIMEOUT = 60
    CLUSTER_HEARTBEAT_INTERVAL = 10

# ── 中间件 ──
MIDDLEWARES = {
    "crawlo.middleware.RetryMiddleware": 550,
    "crawlo.middleware.DownloadDelayMiddleware": 100,
    "crawlo.middleware.OffsiteMiddleware": 500,
}

# ── 管道：JSONL 存储（开箱即用）+ 可选 MySQL ──
PIPELINES = {
    "real_world_catalog.pipelines.JsonlCatalogPipeline": 300,
}

MYSQL_ENABLED = os.environ.get("CRAWLO_MYSQL_ENABLED", "0") == "1"
if MYSQL_ENABLED:
    # 启用 MySQL 存储（需 asyncmy）：crawlo.pipelines.MySQLPipeline 的完整配置见教程
    PIPELINES["crawlo.pipelines.MySQLPipeline"] = 400
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "crawlo_catalog")
    MYSQL_TABLE = "catalog_items"
    MYSQL_USE_BATCH = True
    MYSQL_BATCH_SIZE = 100

# ── 输出文件（JSONL 管道使用）──
CATALOG_OUTPUT_PATH = os.environ.get(
    "CATALOG_OUTPUT_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "catalog.jsonl"),
)

# ── 监控 ──
EXTENSIONS = [
    "crawlo.extensions.HealthCheckExtension",
    "crawlo.extensions.LogStats",
]
STATS_DUMP = True
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_INTERVAL = 60

# ── 日志 ──
LOG_LEVEL = "INFO"

# ── 通知（可选，配置后启用）──
# NOTIFICATION_ENABLED = True
# NOTIFICATION_CHANNELS = ["dingtalk"]
# DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
