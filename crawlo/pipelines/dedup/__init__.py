# -*- coding: utf-8 -*-
"""去重管道子包"""

from .memory import MemoryDedupPipeline
from .redis import RedisDedupPipeline


def __getattr__(name):
    """延迟导入有可选依赖的管道"""
    import importlib

    _lazy_map = {
        'BloomDedupPipeline': ('crawlo.pipelines.dedup.bloom', 'BloomDedupPipeline'),
        'MySQLDedupPipeline': ('crawlo.pipelines.dedup.mysql', 'MySQLDedupPipeline'),
        'DatabaseDedupPipeline': ('crawlo.pipelines.dedup.mysql', 'DatabaseDedupPipeline'),
    }
    if name in _lazy_map:
        module_path, attr = _lazy_map[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'crawlo.pipelines.dedup' has no attribute '{name}'")


__all__ = [
    'MemoryDedupPipeline',
    'RedisDedupPipeline',
    'BloomDedupPipeline',
    'MySQLDedupPipeline',
    'DatabaseDedupPipeline',
]
