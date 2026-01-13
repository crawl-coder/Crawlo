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

from crawlo.logging import get_logger
from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.spider import Spider


class BloomDedupPipeline(DedupPipeline):
    """基于 Bloom Filter 的数据项去重管道"""

    def __init__(
            self,
            crawler,
            capacity: int = 1000000,
            error_rate: float = 0.001,
            log_level: str = "INFO"
    ):
        """
        初始化 Bloom Filter 去重管道
        
        :param crawler: Crawler实例
        :param capacity: 预期存储的元素数量
        :param error_rate: 误判率 (例如 0.001 表示 0.1%)
        :param log_level: 日志级别
        """
        super().__init__(crawler)
        
        self.logger = get_logger(self.__class__.__name__)
        
        # 初始化 Bloom Filter
        try:
            self.bloom_filter = BloomFilter(capacity=capacity, error_rate=error_rate)
            self.logger.info(f"Bloom filter deduplication pipeline initialized (Capacity: {capacity}, Error rate: {error_rate})")
        except Exception as e:
            self.logger.error(f"Bloom filter initialization failed: {e}")
            raise RuntimeError(f"Bloom Filter 初始化失败: {e}")

        self.capacity = capacity
        self.error_rate = error_rate
        self.added_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
            crawler=crawler,
            capacity=settings.get_int('BLOOM_FILTER_CAPACITY', 1000000),
            error_rate=settings.get_float('BLOOM_FILTER_ERROR_RATE', 0.001),
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    async def _initialize_resources(self):
        """初始化资源"""
        # 调用父类的初始化方法
        await super()._initialize_resources()

    async def _cleanup_resources(self):
        """清理资源"""
        # 调用父类的清理方法
        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        """
        检查指纹是否已存在
        
        Args:
            fingerprint: 数据项指纹
            
        Returns:
            是否存在
        """
        return fingerprint in self.bloom_filter

    async def _record_fingerprint(self, fingerprint: str) -> None:
        """
        记录指纹
        
        Args:
            fingerprint: 数据项指纹
        """
        self.bloom_filter.add(fingerprint)
        self.added_count += 1

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        self.logger.info(f"Spider {spider.name} closed:")
        self.logger.info(f"  - Processed items: {self.added_count}")
        self.logger.info(f"  - Possibly dropped duplicate items: {self.dropped_count}")
        self.logger.info(f"  - Processed items (total): {self.processed_count}")
        
        if BLOOM_FILTER_AVAILABLE:
            # 注意：Bloom Filter 无法准确统计元素数量
            self.logger.info(f"  - Bloom filter capacity: {self.capacity}")
            self.logger.info(f"  - Bloom filter error rate: {self.error_rate}")
        else:
            self.logger.warning("  - pybloom_live not installed, using memory set as fallback")