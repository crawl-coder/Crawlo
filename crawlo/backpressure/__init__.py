#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
背压控制模块（已迁移至 crawlo.queue.backpressure）

此模块为向后兼容层，所有代码已迁移至 crawlo.queue.backpressure。
"""

import sys
import warnings
import importlib

# 注册旧子模块路径，使 from crawlo.backpressure.xxx import Yyy 仍可用
_MODULE_MAP = {
    'crawlo.backpressure.interfaces': 'crawlo.queue.backpressure.interfaces',
    'crawlo.backpressure.strategies': 'crawlo.queue.backpressure.strategies',
    'crawlo.backpressure.metrics_collector': 'crawlo.queue.backpressure.metrics_collector',
    'crawlo.backpressure.intelligent_calculator': 'crawlo.queue.backpressure.intelligent_calculator',
    'crawlo.backpressure.monitor': 'crawlo.queue.backpressure.monitor',
}
for _old, _new in _MODULE_MAP.items():
    if _old not in sys.modules:
        sys.modules[_old] = importlib.import_module(_new)

from crawlo.queue.backpressure import (
    BackpressureController,
    PressureLevel,
    BackpressureMetrics,
    IBackpressureStrategy,
    BackpressureStrategyConfig,
    QueueSizeStrategy,
    AdaptiveStrategy,
    CompositeStrategy,
    BackpressureMetricsCollector,
    QueueMetrics,
    IntelligentBackpressureCalculator,
    BackpressureMonitor,
)

warnings.warn(
    "crawlo.backpressure is deprecated, use crawlo.queue.backpressure instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    'BackpressureController',
    'PressureLevel',
    'BackpressureMetrics',
    'IBackpressureStrategy',
    'BackpressureStrategyConfig',
    'QueueSizeStrategy',
    'AdaptiveStrategy',
    'CompositeStrategy',
    'BackpressureMetricsCollector',
    'QueueMetrics',
    'IntelligentBackpressureCalculator',
    'BackpressureMonitor',
]
