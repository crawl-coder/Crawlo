#!/usr/bin/python
# -*- coding:UTF-8 -*-
from crawlo.items import Item


class BasePipeline:

    def process_item(self, item: Item, spider):
        raise NotImplementedError

    @classmethod
    def create_instance(cls, crawler):
        return cls()


# 导出去重管道
from .memory_dedup_pipeline import MemoryDedupPipeline
from .redis_dedup_pipeline import RedisDedupPipeline
from .bloom_dedup_pipeline import BloomDedupPipeline
from .database_dedup_pipeline import DatabaseDedupPipeline

__all__ = ['BasePipeline', 'MemoryDedupPipeline', 'RedisDedupPipeline', 'BloomDedupPipeline', 'DatabaseDedupPipeline']