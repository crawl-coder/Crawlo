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

import hashlib
from typing import Dict, Any, Set

from crawlo import Item
from crawlo.spider import Spider
from crawlo.utils.log import get_logger
from crawlo.exceptions import DropItem


class MemoryDedupPipeline:
    """基于内存的数据项去重管道"""

    def __init__(self, log_level: str = "INFO"):
        """
        初始化内存去重管道
        
        :param log_level: 日志级别
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        
        # 使用集合存储已见过的数据项指纹
        self.seen_items: Set[str] = set()
        self.dropped_count = 0
        
        self.logger.info("内存去重管道初始化完成")

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
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
            if fingerprint in self.seen_items:
                # 如果已存在，丢弃这个数据项
                self.dropped_count += 1
                self.logger.debug(f"丢弃重复数据项: {fingerprint[:20]}...")
                raise DropItem(f"重复的数据项: {fingerprint}")
            else:
                # 记录新数据项的指纹
                self.seen_items.add(fingerprint)
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
        self.logger.info(f"  - 丢弃的重复数据项: {self.dropped_count}")
        self.logger.info(f"  - 内存中存储的指纹数: {len(self.seen_items)}")
        
        # 清理内存
        self.seen_items.clear()
        self.dropped_count = 0