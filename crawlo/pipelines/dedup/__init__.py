# -*- coding: utf-8 -*-
"""去重管道子包"""

from .memory import MemoryDedupPipeline
from .redis import RedisDedupPipeline
from .bloom import BloomDedupPipeline
from .mysql import MySQLDedupPipeline, DatabaseDedupPipeline

__all__ = [
    'MemoryDedupPipeline',
    'RedisDedupPipeline',
    'BloomDedupPipeline',
    'MySQLDedupPipeline',
    'DatabaseDedupPipeline',
]
