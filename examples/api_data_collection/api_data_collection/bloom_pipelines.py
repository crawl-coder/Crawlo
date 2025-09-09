# -*- coding: UTF-8 -*-
"""
api_data_collection.bloom_pipelines
===============================
基于 Bloom Filter 的高效数据处理管道
"""

import hashlib
try:
    from pybloom_live import BloomFilter
except ImportError:
    # 如果没有安装 pybloom_live，使用简单的替代方案
    class BloomFilter:
        def __init__(self, capacity, error_rate):
            self._data = set()
        
        def add(self, item):
            if item in self._data:
                return False
            else:
                self._data.add(item)
                return True
        
        def __contains__(self, item):
            return item in self._data


class BloomDeduplicationPipeline:
    """基于 Bloom Filter 的高效数据项去重管道"""
    
    def __init__(self, capacity=1000000, error_rate=0.001):
        """
        初始化 Bloom Filter
        :param capacity: 预期存储的元素数量
        :param error_rate: 误判率
        """
        self.bloom_filter = BloomFilter(capacity=capacity, error_rate=error_rate)
    
    @classmethod
    def from_settings(cls, settings):
        """
        从设置中创建管道实例
        :param settings: 设置对象
        :return: 管道实例
        """
        capacity = settings.get('BLOOM_FILTER_CAPACITY', 1000000)
        error_rate = settings.get('BLOOM_FILTER_ERROR_RATE', 0.001)
        return cls(capacity=capacity, error_rate=error_rate)
    
    def process_item(self, item, spider):
        """
        处理数据项，进行去重检查
        :param item: 数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        # 基于关键字段生成数据项指纹
        fingerprint = self._generate_item_fingerprint(item)
        
        # 检查指纹是否已存在
        if fingerprint in self.bloom_filter:
            # 如果可能已存在（Bloom Filter 可能有误判），丢弃这个数据项
            raise DropItem(f"可能重复的数据项: {fingerprint}")
        else:
            # 添加指纹到 Bloom Filter
            self.bloom_filter.add(fingerprint)
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
        # Bloom Filter 不需要特殊清理
        pass