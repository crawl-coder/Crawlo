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


# 基础配置默认值
BASE_CONFIG = {
    'PROJECT_NAME': 'crawlo',
    'CONCURRENCY': 8,
    'MAX_RUNNING_SPIDERS': 1,
    'DOWNLOAD_DELAY': 1.0,
    'DOWNLOAD_TIMEOUT': 30,
    'MAX_RETRY_TIMES': 3,
    'CONNECTION_POOL_LIMIT': 50,
    'LOG_LEVEL': 'INFO',
}

# 运行模式配置映射
MODE_CONFIG_MAP = {
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
        'DISTRIBUTED_WORKER_IDLE_TIMEOUT': 300,   # 连续空闲 N 秒后退出（0 = 永不退出）
        'STREAM_DELIVERY_COUNT_LIMIT': 3,           # Stream 最大投递次数
        'STREAM_CONSUMER_IDLE_TIMEOUT': 60000,      # ms，任务超时未 ACK 可回收
    }
}


__all__ = ['RunMode', 'BASE_CONFIG', 'MODE_CONFIG_MAP']
