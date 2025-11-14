#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock

from crawlo.pipelines.mysql_pipeline import AsyncmyMySQLPipeline, AiomysqlMySQLPipeline
from crawlo.exceptions import ItemDiscard


class TestMySQLPipelineError(unittest.TestCase):
    """测试MySQL管道错误处理"""

    def setUp(self):
        """设置测试环境"""
        self.mock_crawler = Mock()
        self.mock_crawler.settings = Mock()
        self.mock_crawler.settings.get = Mock(return_value=None)
        self.mock_crawler.settings.get_int = Mock(return_value=100)
        self.mock_crawler.settings.get_bool = Mock(return_value=False)
        self.mock_crawler.subscriber = Mock()
        self.mock_crawler.subscriber.subscribe = Mock()
        self.mock_crawler.stats = Mock()
        self.mock_crawler.stats.inc_value = Mock()
        
        # 模拟爬虫对象
        self.mock_spider = Mock()
        self.mock_spider.name = "test_spider"
        self.mock_spider.custom_settings = {}
        self.mock_spider.mysql_table = None
        self.mock_crawler.spider = self.mock_spider

    def test_asyncmy_process_item_with_connection_error(self):
        """测试AsyncmyMySQLPipeline处理连接错误"""
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 模拟连接池和数据库操作
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        # 模拟acquire方法返回连接
        mock_pool.acquire.return_value = mock_conn
        
        # 模拟cursor方法返回游标
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟execute方法抛出异常
        mock_cursor.execute.side_effect = Exception("测试异常")
        
        # 设置管道的连接池
        pipeline.pool = mock_pool
        pipeline._pool_initialized = True
        
        # 测试数据
        test_item = {"id": 1, "name": "test"}
        
        async def test_async():
            with self.assertRaises(ItemDiscard) as context:
                await pipeline.process_item(test_item, self.mock_spider)
            
            # 验证错误信息
            self.assertIn("MySQL插入失败", str(context.exception))
            
        asyncio.run(test_async())

    def test_execute_sql_with_exception(self):
        """测试_execute_sql方法处理异常"""
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 模拟连接池和数据库操作
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        # 模拟acquire方法返回连接
        mock_pool.acquire.return_value = mock_conn
        
        # 模拟cursor方法返回游标
        mock_conn.cursor.return_value = mock_cursor
        
        # 模拟execute方法抛出异常
        mock_cursor.execute.side_effect = Exception("测试异常")
        
        # 设置管道的连接池
        pipeline.pool = mock_pool
        pipeline._pool_initialized = True
        
        async def test_async():
            with self.assertRaises(ItemDiscard) as context:
                await pipeline._execute_sql("SELECT 1")
            
            # 验证错误信息
            self.assertIn("MySQL插入失败", str(context.exception))
            
        asyncio.run(test_async())


if __name__ == "__main__":
    unittest.main()