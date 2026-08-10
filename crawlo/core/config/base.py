#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置基础常量与映射
==================
- RunMode 枚举
- BASE_CONFIG 默认配置
- MODE_CONFIG_MAP 各运行模式配置映射
"""
from enum import Enum


class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"   # 单机模式
    DISTRIBUTED = "distributed" # 分布式模式
    AUTO = "auto"               # 自动检测模式


# 基础配置默认值（保持与 crawlo.settings.default_settings 一致，避免两处产生不同默认值导致覆盖异常）
from typing import Any, Dict

BASE_CONFIG: Dict[str, Any] = {
    'PROJECT_NAME': 'crawlo',
    'CONCURRENCY': 8,
    'MAX_RUNNING_SPIDERS': 3,
    'DOWNLOAD_DELAY': 0.5,
    'DOWNLOAD_TIMEOUT': 15,
    'MAX_RETRY_TIMES': 3,
    'CONNECTION_POOL_LIMIT': 100,
    'LOG_LEVEL': 'INFO',   # 与 ConfigValidator 允许的枚举保持一致；项目 settings 可覆盖
}

# 运行模式配置映射
MODE_CONFIG_MAP: Dict[str, Dict[str, Any]] = {
    'standalone': {
        'RUN_MODE': 'standalone',
        'QUEUE_TYPE': 'memory',
        'FILTER_CLASS': 'crawlo.filters.MemoryFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.MemoryDedupPipeline',
    },
    'distributed': {
        'RUN_MODE': 'distributed',
        'QUEUE_TYPE': 'redis_stream',
        'FILTER_CLASS': 'crawlo.filters.AioRedisFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.RedisDedupPipeline',
        'CONCURRENCY': 16,
        'MAX_RUNNING_SPIDERS': 10,
        'DISTRIBUTED_WORKER_IDLE_TIMEOUT': 120,   # 与 default_settings.py 对齐（连续空闲 N 秒后退出，0 = 永不退出）
        'STREAM_DELIVERY_COUNT_LIMIT': 5,           # Stream 最大投递次数（网络抖动时给重试留余量）
        'STREAM_CONSUMER_IDLE_TIMEOUT': 90000,      # ms，任务超时未 ACK 可回收（1.5 min）
        'CLUSTER_FAILOVER_CHECK_INTERVAL': 15,      # 故障检测间隔（秒）
        'CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START': True,  # 空集群下自动清除残留的 shutdown 状态
    }
}


__all__ = ['RunMode', 'BASE_CONFIG', 'MODE_CONFIG_MAP']
