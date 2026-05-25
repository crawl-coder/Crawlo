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
"""

from typing import Set

from crawlo.pipelines.base_pipeline import DedupPipeline


class MemoryDedupPipeline(DedupPipeline):
    """基于内存的数据项去重管道"""

    def __init__(self, crawler, log_level: str = "INFO"):
        super().__init__(crawler)
        # 使用集合存储已见过的数据项指纹
        self.seen_items: Set[str] = set()
        self.logger.info("Memory deduplication pipeline initialized")

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(
            crawler=crawler,
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    # _initialize_resources: 无需重写，直接继承 DedupPipeline 的默认统计记录

    async def _cleanup_resources(self):
        """清理资源 + 输出统计（从 close_spider 迁移至此）"""
        # 输出统计（StatsCollector 已有完整统计，此处降为 debug 避免重复）
        self.logger.debug(
            f"MemoryDedupPipeline closed: "
            f"processed={self.processed_count}, dropped={self.dropped_count}, "
            f"fingerprints_stored={len(self.seen_items)}"
        )
        # 清理内存
        self.seen_items.clear()
        # 调用父类
        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        return fingerprint in self.seen_items

    async def _record_fingerprint(self, fingerprint: str) -> None:
        self.seen_items.add(fingerprint)
