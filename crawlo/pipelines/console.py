#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
控制台输出管道
================
将 Item 内容输出到控制台日志，用于调试和监控。
"""
from typing import Dict, Any

from crawlo.items import Item
from crawlo.spider import Spider
from crawlo.logging import get_logger
from crawlo.pipelines.base_pipeline import BasePipeline


class ConsolePipeline(BasePipeline):
    """将 Item 内容输出到控制台的管道"""

    def __init__(self, crawler, log_level: str = "DEBUG"):
        """
        初始化控制台管道
        
        :param crawler: Crawler 实例
        :param log_level: 日志级别
        """
        # ConsolePipeline 是简单管道，不需要资源管理
        # 但仍需保持 BasePipeline 接口一致性
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        self.log_level = log_level

    @classmethod
    def from_crawler(cls, crawler):
        """从 crawler 实例创建管道"""
        return cls(
            crawler=crawler,
            log_level=crawler.settings.get('LOG_LEVEL', 'DEBUG')
        )

    async def process_item(self, item: Item, spider: Spider, **kwargs) -> Item:
        """处理 Item 并输出到日志"""
        try:
            item_dict = self._convert_to_serializable(item)
            self.logger.info(f"Item processed: {item_dict}")
            return item
        except Exception as e:
            self.logger.error(f"Error processing item: {e}", exc_info=True)
            raise

    @staticmethod
    def _convert_to_serializable(item: Item) -> Dict[str, Any]:
        """将 Item 转换为可序列化的字典"""
        try:
            return item.to_dict()
        except AttributeError:
            # 兼容没有 to_dict 方法的 Item 实现
            return dict(item)
