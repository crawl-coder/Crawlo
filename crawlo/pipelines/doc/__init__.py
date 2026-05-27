# -*- coding: utf-8 -*-
"""文档型存储管道子包"""

from .mongo import MongoPipeline
from .elasticsearch import ElasticsearchPipeline

__all__ = [
    'MongoPipeline',
    'ElasticsearchPipeline',
]
