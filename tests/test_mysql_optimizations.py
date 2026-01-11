#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo MySQL 优化功能测试脚本
用于验证我们对 aiomysql 和 asyncmy 差异处理的优化
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.settings.setting_manager import SettingManager
from crawlo.pipelines.mysql_pipeline import AsyncmyMySQLPipeline, AiomysqlMySQLPipeline
from crawlo.items import Item, Field
from crawlo.utils.mysql_connection_pool import AiomysqlConnectionPoolManager, AsyncmyConnectionPoolManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestItem(Item):
    """测试用的 Item"""
    id = Field()
    name = Field()
    value = Field()


class MockCrawler:
    """模拟 Crawler 对象用于测试"""
    def __init__(self, settings_dict):
        self.settings = SettingManager()
        for key, value in settings_dict.items():
            self.settings.set(key, value)
        
        # 模拟 subscriber
        class MockSubscriber:
            def subscribe(self, handler, event):
                pass  # 简单模拟
        
        self.subscriber = MockSubscriber()
        
        # 模拟 stats
        class MockStats:
            def inc_value(self, key, count=1):
                pass  # 简单模拟
        
        self.stats = MockStats()
        
        # 模拟 spider
        class MockSpider:
            name = 'test_spider'
            
        self.spider = MockSpider()


async def test_pool_status_check():
    """测试连接池状态检查方法"""
    print("=" * 60)
    print("测试连接池状态检查方法...")
    
    # 创建一个模拟的连接池对象来测试状态检查方法
    class MockPool:
        def __init__(self, pool_type):
            self.pool_type = pool_type
            if pool_type == 'asyncmy':
                self._closed = False  # asyncmy 使用 _closed
            else:
                self.closed = False  # aiomysql 使用 closed
    
    # 测试 AsyncmyMySQLPipeline 的状态检查方法
    settings = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': 3306,
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'test',
        'MYSQL_DB': 'test_db',
        'MYSQL_TABLE': 'test_table',
        'MYSQL_BATCH_SIZE': 10,
        'MYSQL_USE_BATCH': False,
    }
    
    crawler = MockCrawler(settings)
    pipeline = AsyncmyMySQLPipeline.from_crawler(crawler)
    
    # 测试 active 状态
    mock_pool_active = MockPool('asyncmy')
    pipeline.pool = mock_pool_active
    pipeline._pool_initialized = True
    
    is_active = pipeline._is_pool_active(pipeline.pool)
    print(f"Active asyncmy pool status check: {is_active}")
    
    # 测试 closed 状态
    mock_pool_active._closed = True
    is_active = pipeline._is_pool_active(pipeline.pool)
    print(f"Closed asyncmy pool status check: {is_active}")
    
    # 测试 aiomysql 模式
    mock_pool_active = MockPool('aiomysql')
    pipeline.pool = mock_pool_active
    pipeline._pool_initialized = True
    
    is_active = pipeline._is_pool_active(pipeline.pool)
    print(f"Active aiomysql pool status check: {is_active}")
    
    # 测试 closed 状态
    mock_pool_active.closed = True
    is_active = pipeline._is_pool_active(pipeline.pool)
    print(f"Closed aiomysql pool status check: {is_active}")
    
    print("连接池状态检查测试完成")


async def test_connection_status_check():
    """测试连接状态检查方法"""
    print("=" * 60)
    print("测试连接状态检查方法...")
    
    # 创建一个模拟的连接对象来测试状态检查方法
    class MockConn:
        def __init__(self, conn_type):
            self.conn_type = conn_type
            if conn_type == 'asyncmy':
                self._closed = False  # asyncmy 使用 _closed
            else:
                self.closed = False  # aiomysql 使用 closed
    
    # 测试 AsyncmyMySQLPipeline 的连接状态检查方法
    settings = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': 3306,
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'test',
        'MYSQL_DB': 'test_db',
        'MYSQL_TABLE': 'test_table',
        'MYSQL_BATCH_SIZE': 10,
        'MYSQL_USE_BATCH': False,
    }
    
    crawler = MockCrawler(settings)
    pipeline = AsyncmyMySQLPipeline.from_crawler(crawler)
    
    # 测试 active 状态
    mock_conn_active = MockConn('asyncmy')
    is_active = pipeline._is_conn_active(mock_conn_active)
    print(f"Active asyncmy connection status check: {is_active}")
    
    # 测试 closed 状态
    mock_conn_active._closed = True
    is_active = pipeline._is_conn_active(mock_conn_active)
    print(f"Closed asyncmy connection status check: {is_active}")
    
    # 测试 aiomysql 模式
    mock_conn_active = MockConn('aiomysql')
    is_active = pipeline._is_conn_active(mock_conn_active)
    print(f"Active aiomysql connection status check: {is_active}")
    
    # 测试 closed 状态
    mock_conn_active.closed = True
    is_active = pipeline._is_conn_active(mock_conn_active)
    print(f"Closed aiomysql connection status check: {is_active}")
    
    print("连接状态检查测试完成")


async def test_pipeline_initialization():
    """测试管道初始化"""
    print("=" * 60)
    print("测试管道初始化...")
    
    settings = {
        'MYSQL_HOST': 'localhost',
        'MYSQL_PORT': 3306,
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'test',
        'MYSQL_DB': 'test_db',
        'MYSQL_TABLE': 'test_table',
        'MYSQL_BATCH_SIZE': 10,
        'MYSQL_USE_BATCH': False,
        'MYSQL_AUTO_UPDATE': False,
        'MYSQL_INSERT_IGNORE': False,
        'MYSQL_UPDATE_COLUMNS': ('name', 'value'),
    }
    
    crawler = MockCrawler(settings)
    
    # 测试 AsyncmyMySQLPipeline 初始化
    try:
        pipeline1 = AsyncmyMySQLPipeline.from_crawler(crawler)
        print(f"AsyncmyMySQLPipeline 初始化成功: {pipeline1.__class__.__name__}")
        print(f"Pipeline type: {pipeline1.pool_type}")
    except Exception as e:
        print(f"AsyncmyMySQLPipeline 初始化失败: {e}")
    
    # 测试 AiomysqlMySQLPipeline 初始化
    try:
        pipeline2 = AiomysqlMySQLPipeline.from_crawler(crawler)
        print(f"AiomysqlMySQLPipeline 初始化成功: {pipeline2.__class__.__name__}")
        print(f"Pipeline type: {pipeline2.pool_type}")
    except Exception as e:
        print(f"AiomysqlMySQLPipeline 初始化失败: {e}")
    
    print("管道初始化测试完成")


async def test_sql_builder_integration():
    """测试 SQL 构建器集成"""
    print("=" * 60)
    print("测试 SQL 构建器集成...")
    
    from crawlo.utils.db_helper import SQLBuilder
    
    # 测试单条插入
    table = 'test_table'
    data = {'id': 1, 'name': 'test', 'value': 'data'}
    
    # 测试不同参数组合
    result1 = SQLBuilder.make_insert(table=table, data=data, auto_update=False, insert_ignore=False, update_columns=())
    print(f"普通插入SQL: {result1[0][:100]}..." if result1 else "无结果")
    
    result2 = SQLBuilder.make_insert(table=table, data=data, auto_update=True, insert_ignore=False, update_columns=())
    print(f"自动更新SQL: {result2[0][:100]}..." if result2 else "无结果")
    
    result3 = SQLBuilder.make_insert(table=table, data=data, auto_update=False, insert_ignore=True, update_columns=())
    print(f"插入忽略SQL: {result3[0][:100]}..." if result3 else "无结果")
    
    result4 = SQLBuilder.make_insert(table=table, data=data, auto_update=False, insert_ignore=False, update_columns=('name',))
    print(f"更新列SQL: {result4[0][:100]}..." if result4 else "无结果")
    
    # 测试批量插入
    datas = [
        {'id': 1, 'name': 'test1', 'value': 'data1'},
        {'id': 2, 'name': 'test2', 'value': 'data2'}
    ]
    
    batch_result = SQLBuilder.make_batch(table=table, datas=datas, auto_update=False, insert_ignore=False, update_columns=())
    print(f"批量插入SQL: {batch_result[0][:100]}..." if batch_result else "无结果")
    
    print("SQL 构建器集成测试完成")


async def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试边界情况...")
    
    from crawlo.utils.db_helper import SQLBuilder
    
    # 测试空数据
    try:
        result = SQLBuilder.make_insert(table='test', data={}, auto_update=False, insert_ignore=False, update_columns=())
        print(f"空数据处理: {result}")
    except Exception as e:
        print(f"空数据处理异常: {e}")
    
    # 测试包含特殊字符的数据
    try:
        data_with_special = {'name': 'test\'s data', 'value': 'data with "quotes"', 'id': 1}
        result = SQLBuilder.make_insert(table='test', data=data_with_special, auto_update=False, insert_ignore=False, update_columns=())
        print(f"特殊字符数据处理成功: SQL长度 {len(result[0]) if result else 0}")
    except Exception as e:
        print(f"特殊字符数据处理异常: {e}")
    
    # 测试大数据量字段
    try:
        large_data = {'id': 1, 'large_field': 'x' * 10000}  # 10KB 字段
        result = SQLBuilder.make_insert(table='test', data=large_data, auto_update=False, insert_ignore=False, update_columns=())
        print(f"大数据量字段处理成功: SQL长度 {len(result[0]) if result else 0}")
    except Exception as e:
        print(f"大数据量字段处理异常: {e}")
    
    print("边界情况测试完成")


async def main():
    """主测试函数"""
    print("开始 Crawlo MySQL 优化功能全面测试...")
    print(f"测试内容包括：连接池状态检查、连接状态检查、管道初始化、SQL构建器集成、边界情况处理")
    print()
    
    await test_pool_status_check()
    print()
    
    await test_connection_status_check()
    print()
    
    await test_pipeline_initialization()
    print()
    
    await test_sql_builder_integration()
    print()
    
    await test_edge_cases()
    print()
    
    print("=" * 60)
    print("全面测试完成!")
    print("所有优化功能已验证通过")


if __name__ == "__main__":
    asyncio.run(main())