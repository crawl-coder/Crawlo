# -*- coding: UTF-8 -*-
"""
api_data_collection.pipelines
===========================
数据处理管道
"""

import hashlib
from crawlo.pipelines import Pipeline
from crawlo.exceptions import DropItem


class DeduplicationPipeline(Pipeline):
    """数据项去重管道"""
    
    def __init__(self):
        # 使用集合存储已见过的数据项指纹
        # 在生产环境中，建议使用 Redis 等外部存储
        self.seen_items = set()
    
    def process_item(self, item, spider):
        """
        处理数据项，进行去重检查
        :param item: 数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        # 基于关键字段生成数据项指纹
        fingerprint = self._generate_item_fingerprint(item)
        
        if fingerprint in self.seen_items:
            # 如果已经见过这个数据项，丢弃它
            raise DropItem(f"重复的数据项: {fingerprint}")
        else:
            # 记录新数据项的指纹
            self.seen_items.add(fingerprint)
            return item
    
    def _generate_item_fingerprint(self, item):
        """
        生成数据项指纹
        :param item: 数据项
        :return: 指纹字符串
        """
        # 使用数据项的关键字段生成指纹
        key_fields = [
            str(item.get('id', '')),
            item.get('name', ''),
            item.get('category', '')
        ]
        fingerprint_string = '|'.join(key_fields)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def close_spider(self, spider):
        """
        爬虫关闭时的清理工作
        :param spider: 爬虫实例
        """
        # 清理资源
        self.seen_items.clear()


class ConsolePipeline(Pipeline):
    """控制台输出管道"""
    
    def process_item(self, item, spider):
        """
        在控制台输出数据项
        :param item: 数据项
        :param spider: 爬虫实例
        :return: 数据项
        """
        print(f"采集到数据项: {item}")
        return item