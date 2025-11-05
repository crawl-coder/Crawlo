#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
"""
测试 MySQL 管道初始化日志
验证在管道初始化时是否正确打印日志
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.pipelines.mysql_pipeline import AsyncmyMySQLPipeline, AiomysqlMySQLPipeline


# 创建一个简单的爬虫模拟类
class MockSpider:
    name = "test_spider"


# 创建一个简单的设置模拟类
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


# 创建一个简单的订阅者模拟类
class MockSubscriber:
    def subscribe(self, func, event):
        # 简化的订阅
        pass


# 创建一个简单的爬虫模拟类
class MockCrawler:
    def __init__(self):
        self.settings = MockSettings()
        self.subscriber = MockSubscriber()
        self.spider = MockSpider()


def test_pipeline_init_logs():
    """测试管道初始化日志"""
    print("=== Testing MySQL Pipeline Initialization Logs ===")
    
    # 创建模拟的爬虫
    crawler = MockCrawler()
    
    print("1. Testing AsyncmyMySQLPipeline initialization...")
    try:
        asyncmy_pipeline = AsyncmyMySQLPipeline.from_crawler(crawler)
        print("   ✓ AsyncmyMySQLPipeline initialized successfully")
    except Exception as e:
        print(f"   ✗ AsyncmyMySQLPipeline initialization failed: {e}")
    
    print("\n2. Testing AiomysqlMySQLPipeline initialization...")
    try:
        aiomysql_pipeline = AiomysqlMySQLPipeline.from_crawler(crawler)
        print("   ✓ AiomysqlMySQLPipeline initialized successfully")
    except Exception as e:
        print(f"   ✗ AiomysqlMySQLPipeline initialization failed: {e}")
    
    print("\n=== Test completed ===")
    print("Note: Actual log output can be seen when running in a full crawler environment")


if __name__ == "__main__":
    test_pipeline_init_logs()