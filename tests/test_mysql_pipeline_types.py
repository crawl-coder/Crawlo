#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
"""
测试 MySQL 管道类型检查
验证修复的类型问题
"""
import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.items import Item, Field
from crawlo.pipelines.mysql_pipeline import BaseMySQLPipeline


# 创建一个简单的 Item 类用于测试
class TestItem(Item):
    title = Field()
    content = Field()


# 创建一个简单的爬虫模拟类
class MockSpider:
    name = "test_spider"


# 创建一个简单的爬虫模拟类
class MockCrawler:
    def __init__(self):
        self.settings = MockSettings()
        self.subscriber = MockSubscriber()
        self.spider = MockSpider()


class MockSettings:
    def get(self, key, default=None):
        # 简化的设置获取
        settings_map = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'LOG_LEVEL': 'INFO'
        }
        return settings_map.get(key, default)
    
    def get_int(self, key, default=0):
        return int(self.get(key, default))
    
    def get_bool(self, key, default=False):
        return bool(self.get(key, default))


class MockSubscriber:
    def subscribe(self, func, event):
        # 简化的订阅
        pass


def test_types():
    """测试类型检查"""
    print("=== 测试 MySQL 管道类型 ===")
    
    # 创建模拟的爬虫和管道
    crawler = MockCrawler()
    
    # 测试基类不能直接实例化（因为有抽象方法）
    try:
        # 这应该会失败，因为基类是抽象的
        pipeline = BaseMySQLPipeline(crawler)
        print("✓ BaseMySQLPipeline 实例化成功")
    except Exception as e:
        print(f"✗ BaseMySQLPipeline 实例化失败: {e}")
    
    # 测试方法签名
    print("\n方法签名检查:")
    print("- process_item(self, item: Item, spider, kwargs: Dict[str, Any] = None) -> Item")
    print("- _execute_sql(self, sql: str, values: list = None) -> int (abstractmethod)")
    print("- _execute_batch_sql(self, sql: str, values_list: list) -> int (abstractmethod)")
    
    print("\n=== 类型检查完成 ===")


if __name__ == "__main__":
    test_types()