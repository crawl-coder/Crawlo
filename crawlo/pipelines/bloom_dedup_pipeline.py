#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 Bloom Filter 的数据项去重管道
=============================
提供大规模数据采集场景下的高效去重功能，使用概率性数据结构节省内存。

特点:
- 内存效率高: 相比传统集合节省大量内存
- 高性能: 快速的插入和查找操作
- 可扩展: 支持自定义容量和误判率
- 适用性广: 特别适合大规模数据采集

注意: Bloom Filter 有误判率，可能会错误地丢弃一些未见过的数据项。
"""

import hashlib
try:
    from pybloom_live import BloomFilter
    BLOOM_FILTER_AVAILABLE = True
except ImportError:
    # 如果没有安装 pybloom_live，使用简单的替代方案
    BLOOM_FILTER_AVAILABLE = False
    
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

from crawlo import Item
from crawlo.spider import Spider
from crawlo.utils.log import get_logger
from crawlo.exceptions import DropItem


class BloomDedupPipeline:
    """基于 Bloom Filter 的数据项去重管道"""

    def __init__(
            self,
            capacity: int = 1000000,
            error_rate: float = 0.001,
            log_level: str = "INFO"
    ):
        """
        初始化 Bloom Filter 去重管道
        
        :param capacity: 预期存储的元素数量
        :param error_rate: 误判率 (例如 0.001 表示 0.1%)
        :param log_level: 日志级别
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        
        # 初始化 Bloom Filter
        try:
            self.bloom_filter = BloomFilter(capacity=capacity, error_rate=error_rate)
            self.logger.info(f"Bloom Filter 去重管道初始化完成 (容量: {capacity}, 误判率: {error_rate})")
        except Exception as e:
            self.logger.error(f"Bloom Filter 初始化失败: {e}")
            raise RuntimeError(f"Bloom Filter 初始化失败: {e}")

        self.capacity = capacity
        self.error_rate = error_rate
        self.dropped_count = 0
        self.added_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
            capacity=settings.getint('BLOOM_FILTER_CAPACITY', 1000000),
            error_rate=settings.getfloat('BLOOM_FILTER_ERROR_RATE', 0.001),
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    def process_item(self, item: Item, spider: Spider) -> Item:
        """
        处理数据项，进行去重检查
        
        :param item: 要处理的数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        try:
            # 生成数据项指纹
            fingerprint = self._generate_item_fingerprint(item)
            
            # 检查指纹是否已存在
            if fingerprint in self.bloom_filter:
                # 如果可能已存在（Bloom Filter 可能有误判），丢弃这个数据项
                self.dropped_count += 1
                self.logger.debug(f"可能丢弃重复数据项: {fingerprint[:20]}...")
                raise DropItem(f"可能重复的数据项: {fingerprint}")
            else:
                # 添加指纹到 Bloom Filter
                self.bloom_filter.add(fingerprint)
                self.added_count += 1
                self.logger.debug(f"处理新数据项: {fingerprint[:20]}...")
                return item
                
        except Exception as e:
            self.logger.error(f"处理数据项时出错: {e}")
            # 在错误时继续处理，避免丢失数据
            return item

    def _generate_item_fingerprint(self, item: Item) -> str:
        """
        生成数据项指纹
        
        基于数据项的所有字段生成唯一指纹，用于去重判断。
        
        :param item: 数据项
        :return: 指纹字符串
        """
        # 将数据项转换为可序列化的字典
        try:
            item_dict = item.to_dict()
        except AttributeError:
            # 兼容没有to_dict方法的Item实现
            item_dict = dict(item)
        
        # 对字典进行排序以确保一致性
        sorted_items = sorted(item_dict.items())
        
        # 生成指纹字符串
        fingerprint_string = '|'.join([f"{k}={v}" for k, v in sorted_items if v is not None])
        
        # 使用 SHA256 生成固定长度的指纹
        return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        self.logger.info(f"爬虫 {spider.name} 关闭:")
        self.logger.info(f"  - 处理的数据项数: {self.added_count}")
        self.logger.info(f"  - 可能丢弃的重复数据项: {self.dropped_count}")
        
        if BLOOM_FILTER_AVAILABLE:
            # 注意：Bloom Filter 无法准确统计元素数量
            self.logger.info(f"  - Bloom Filter 容量: {self.capacity}")
            self.logger.info(f"  - Bloom Filter 误判率: {self.error_rate}")
        else:
            self.logger.warning("  - 未安装 pybloom_live，使用内存集合作为替代")