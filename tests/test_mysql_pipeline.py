#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo MySQL 管道全面测试脚本
用于验证我们对 aiomysql 和 asyncmy 差异处理的优化
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapy.settings import Settings
from crawlo.pipelines.mysql_pipeline import AsyncmyMySQLPipeline, AiomysqlMySQLPipeline
from crawlo.items import Item, Field
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestItem(Item):
    """测试用的 Item"""
    id = Field()
    name = Field()
    value = Field()
    created_at = Field()


class MockCrawler:
    """模拟 Crawler 对象用于测试"""
    def __init__(self, settings_dict):
        self.settings = Settings()
        for key, value in settings_dict.items():
            self.settings[key] = value
        
        # 模拟 subscriber
        class MockSubscriber:
            def subscribe(self, handler, event):
                logger.info(f"Subscribed {handler.__name__} to event {event}")
        
        self.subscriber = MockSubscriber()
        
        # 模拟 stats
        class MockStats:
            def inc_value(self, key, count=1):
                logger.info(f"Stat incremented: {key} = {count}")
        
        self.stats = MockStats()
        
        # 模拟 spider
        class MockSpider:
            name = 'test_spider'
            
        self.spider = MockSpider()


async def test_asyncmy_pipeline():
    """测试 AsyncmyMySQLPipeline"""
    print("=" * 60)
    print("测试 AsyncmyMySQLPipeline...")
    
    # 配置测试设置
    settings = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': 3306,
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'your_password',  # 替换为你的密码
        'MYSQL_DB': 'test_db',
        'MYSQL_TABLE': 'test_table',
        'MYSQL_BATCH_SIZE': 10,
        'MYSQL_USE_BATCH': True,
        'MYSQL_AUTO_UPDATE': False,
        'MYSQL_INSERT_IGNORE': False,
        'MYSQL_UPDATE_COLUMNS': ('name', 'value'),
    }
    
    crawler = MockCrawler(settings)
    
    try:
        pipeline = AsyncmyMySQLPipeline.from_crawler(crawler)
        await pipeline.open_spider(crawler.spider)
        
        # 测试单个 item 处理
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test_name'
        item['value'] = 'test_value'
        item['created_at'] = '2023-01-01 00:00:00'
        
        print(f"处理测试项目: {dict(item)}")
        result = await pipeline.process_item(item, crawler.spider)
        print(f"处理结果: {result}")
        
        # 测试批量处理
        print("测试批量处理...")
        for i in range(5):
            item = TestItem()
            item['id'] = i + 2
            item['name'] = f'test_name_{i}'
            item['value'] = f'test_value_{i}'
            item['created_at'] = '2023-01-01 00:00:00'
            
            result = await pipeline.process_item(item, crawler.spider)
            print(f"批量处理项目 {i+1} 结果: {result}")
        
        await pipeline.spider_closed()
        print("AsyncmyMySQLPipeline 测试完成")
        
    except Exception as e:
        logger.error(f"AsyncmyMySQLPipeline 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_aiomysql_pipeline():
    """测试 AiomysqlMySQLPipeline"""
    print("=" * 60)
    print("测试 AiomysqlMySQLPipeline...")
    
    # 配置测试设置
    settings = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': 3306,
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'your_password',  # 替换为你的密码
        'MYSQL_DB': 'test_db',
        'MYSQL_TABLE': 'test_table',
        'MYSQL_BATCH_SIZE': 10,
        'MYSQL_USE_BATCH': True,
        'MYSQL_AUTO_UPDATE': False,
        'MYSQL_INSERT_IGNORE': False,
        'MYSQL_UPDATE_COLUMNS': ('name', 'value'),
    }
    
    crawler = MockCrawler(settings)
    
    try:
        pipeline = AiomysqlMySQLPipeline.from_crawler(crawler)
        await pipeline.open_spider(crawler.spider)
        
        # 测试单个 item 处理
        item = TestItem()
        item['id'] = 10
        item['name'] = 'aiomysql_test'
        item['value'] = 'aiomysql_value'
        item['created_at'] = '2023-01-01 00:00:00'
        
        print(f"处理测试项目: {dict(item)}")
        result = await pipeline.process_item(item, crawler.spider)
        print(f"处理结果: {result}")
        
        # 测试批量处理
        print("测试批量处理...")
        for i in range(5):
            item = TestItem()
            item['id'] = i + 11
            item['name'] = f'aiomysql_test_{i}'
            item['value'] = f'aiomysql_value_{i}'
            item['created_at'] = '2023-01-01 00:00:00'
            
            result = await pipeline.process_item(item, crawler.spider)
            print(f"批量处理项目 {i+1} 结果: {result}")
        
        await pipeline.spider_closed()
        print("AiomysqlMySQLPipeline 测试完成")
        
    except Exception as e:
        logger.error(f"AiomysqlMySQLPipeline 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_connection_pool_utils():
    """测试连接池工具类"""
    print("=" * 60)
    print("测试连接池工具类...")
    
    from crawlo.utils.mysql_connection_pool import AsyncmyConnectionPoolManager, AiomysqlConnectionPoolManager
    from crawlo.utils.database_connection_pool import get_mysql_pool
    
    try:
        # 测试 asyncmy 连接池
        print("测试 asyncmy 连接池...")
        pool1 = await get_mysql_pool(
            pool_type='asyncmy',
            host='localhost',
            port=3306,
            user='root',
            password='your_password',  # 替换为你的密码
            db='test_db',
            minsize=1,
            maxsize=2
        )
        
        print(f"asyncmy 连接池获取成功: {pool1}")
        
        # 测试 aiomysql 连接池
        print("测试 aiomysql 连接池...")
        pool2 = await get_mysql_pool(
            pool_type='aiomysql',
            host='localhost',
            port=3306,
            user='root',
            password='your_password',  # 替换为你的密码
            db='test_db',
            minsize=1,
            maxsize=2
        )
        
        print(f"aiomysql 连接池获取成功: {pool2}")
        
        # 测试连接池统计
        from crawlo.utils.database_connection_pool import get_database_pool_stats
        stats = get_database_pool_stats()
        print(f"连接池统计信息: {stats}")
        
        print("连接池工具类测试完成")
        
    except Exception as e:
        logger.error(f"连接池工具类测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始 Crawlo MySQL 管道全面测试...")
    print(f"Crawlo 版本: 1.5.3")
    print()
    
    # 测试连接池工具类
    await test_connection_pool_utils()
    
    # 测试 AsyncmyMySQLPipeline（如果可用）
    try:
        import asyncmy
        print("asyncmy 库可用，开始测试 AsyncmyMySQLPipeline")
        await test_asyncmy_pipeline()
    except ImportError:
        print("asyncmy 库不可用，跳过 AsyncmyMySQLPipeline 测试")
    
    # 测试 AiomysqlMySQLPipeline（如果可用）
    try:
        import aiomysql
        print("aiomysql 库可用，开始测试 AiomysqlMySQLPipeline")
        await test_aiomysql_pipeline()
    except ImportError:
        print("aiomysql 库不可用，跳过 AiomysqlMySQLPipeline 测试")
    
    print("=" * 60)
    print("全面测试完成!")


if __name__ == "__main__":
    asyncio.run(main())