#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Dict, Any

from crawlo import Item
from crawlo.spider import Spider
from crawlo.utils.log import get_logger


class ConsolePipeline:
    """将Item内容输出到控制台的管道"""

    def __init__(self, log_level: str = "DEBUG"):
        self.logger = get_logger(self.__class__.__name__, log_level)

    @classmethod
    def from_crawler(cls, crawler):
        """从crawler实例创建管道"""
        return cls(
            log_level=crawler.settings.get('LOG_LEVEL', 'DEBUG')
        )

    async def process_item(self, item: Item, spider: Spider) -> Item:
        """处理Item并输出到日志"""
        try:
            item_dict = self._convert_to_serializable(item)
            self.logger.info(f"Item processed: {item_dict}")
            return item
        except Exception as e:
            self.logger.error(f"Error processing item: {e}", exc_info=True)
            raise

    @staticmethod
    def _convert_to_serializable(item: Item) -> Dict[str, Any]:
        """将Item转换为可序列化的字典"""
        try:
            return item.to_dict()
        except AttributeError:
            # 兼容没有to_dict方法的Item实现
            return dict(item)