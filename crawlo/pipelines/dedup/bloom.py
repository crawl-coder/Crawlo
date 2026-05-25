#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 Bloom Filter 的数据项去重管道
=============================
提供大规模数据采集场景下的高效去重功能，使用概率性数据结构节省内存。

注意: Bloom Filter 有误判率，可能会错误地丢弃一些未见过的数据项。
"""

try:
    from pybloom_live import BloomFilter
    BLOOM_FILTER_AVAILABLE = True
except ImportError:
    BLOOM_FILTER_AVAILABLE = False
    
    class BloomFilter:
        """BloomFilter 回退实现（使用 set，与 MemoryDedupPipeline 功能重叠）"""
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

from crawlo.pipelines.base_pipeline import DedupPipeline


class BloomDedupPipeline(DedupPipeline):
    """基于 Bloom Filter 的数据项去重管道"""

    def __init__(
            self,
            crawler,
            capacity: int = 1000000,
            error_rate: float = 0.001,
            log_level: str = "INFO"
    ):
        super().__init__(crawler)
        
        # 初始化 Bloom Filter
        try:
            self.bloom_filter = BloomFilter(capacity=capacity, error_rate=error_rate)
            self.logger.info(
                f"Bloom filter initialized (capacity={capacity}, error_rate={error_rate})"
            )
        except Exception as e:
            self.logger.error(f"Bloom filter init failed: {e}")
            raise RuntimeError(f"Bloom Filter 初始化失败: {e}")

        self.capacity = capacity
        self.error_rate = error_rate
        self.added_count = 0
        self._bloom_available = BLOOM_FILTER_AVAILABLE

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            crawler=crawler,
            capacity=settings.get_int('BLOOM_FILTER_CAPACITY', 1000000),
            error_rate=settings.get_float('BLOOM_FILTER_ERROR_RATE', 0.001),
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    # _initialize_resources / _cleanup_resources: 无额外逻辑，直接继承 DedupPipeline

    async def _cleanup_resources(self):
        """清理资源 + 输出统计"""
        self.logger.info(
            f"BloomDedupPipeline closed: "
            f"added={self.added_count}, dropped={self.dropped_count}, "
            f"processed_total={self.processed_count}"
        )
        if self._bloom_available:
            self.logger.info(
                f"  capacity={self.capacity}, error_rate={self.error_rate}"
            )
        else:
            self.logger.warning("  pybloom_live not installed, using memory set fallback")
        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        return fingerprint in self.bloom_filter

    async def _record_fingerprint(self, fingerprint: str) -> None:
        self.bloom_filter.add(fingerprint)
        self.added_count += 1
