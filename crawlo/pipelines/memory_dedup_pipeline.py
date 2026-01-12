#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于内存的数据项去重管道
======================
提供单节点环境下的数据项去重功能，防止保存重复的数据记录。

特点:
- 高性能: 使用内存集合进行快速查找
- 简单易用: 无需外部依赖
- 轻量级: 适用于小规模数据采集
- 低延迟: 内存操作无网络开销
"""

from typing import Set

from crawlo.logging import get_logger
from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.spider import Spider


class MemoryDedupPipeline(DedupPipeline):
    """基于内存的数据项去重管道"""

    def __init__(self, crawler, log_level: str = "INFO"):
        """
        初始化内存去重管道
        
        :param crawler: Crawler实例
        :param log_level: 日志级别
        """
        super().__init__(crawler)
        
        self.logger = get_logger(self.__class__.__name__)
        
        # 使用集合存储已见过的数据项指纹
        self.seen_items: Set[str] = set()
        
        self.logger.info("Memory deduplication pipeline initialized")

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
            crawler=crawler,
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    async def _initialize_resources(self):
        """初始化资源"""
        # 调用父类的初始化方法
        await super()._initialize_resources()

    async def _cleanup_resources(self):
        """清理资源"""
        # 清理内存
        self.seen_items.clear()
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
        return fingerprint in self.seen_items

    async def _record_fingerprint(self, fingerprint: str) -> None:
        """
        记录指纹
        
        Args:
            fingerprint: 数据项指纹
        """
        self.seen_items.add(fingerprint)

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        self.logger.info(f"Spider {spider.name} closed:")
        self.logger.info(f"  - Dropped duplicate items: {self.dropped_count}")
        self.logger.info(f"  - Processed items: {self.processed_count}")
        self.logger.info(f"  - Fingerprints stored in memory: {len(self.seen_items)}")