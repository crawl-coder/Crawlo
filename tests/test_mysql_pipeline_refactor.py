#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock

from crawlo.pipelines.mysql_pipeline import BaseMySQLPipeline, AsyncmyMySQLPipeline, AiomysqlMySQLPipeline


class TestBaseMySQLPipeline(unittest.TestCase):
    """测试MySQL管道基类"""

    def setUp(self):
        """设置测试环境"""
        self.mock_crawler = Mock()
        self.mock_crawler.settings = Mock()
        self.mock_crawler.settings.get = Mock(return_value=None)
        self.mock_crawler.settings.get_int = Mock(return_value=100)
        self.mock_crawler.settings.get_bool = Mock(return_value=False)
        self.mock_crawler.subscriber = Mock()
        self.mock_crawler.subscriber.subscribe = Mock()
        
        # 模拟爬虫对象
        self.mock_spider = Mock()
        self.mock_spider.name = "test_spider"
        self.mock_spider.custom_settings = {}
        self.mock_spider.mysql_table = None
        self.mock_crawler.spider = self.mock_spider

    def test_base_init(self):
        """测试基类初始化"""
        # 创建一个实现基类的测试类
        class TestMySQLPipeline(BaseMySQLPipeline):
            async def _ensure_pool(self):
                pass
        
        pipeline = TestMySQLPipeline(self.mock_crawler)
        
        # 验证属性初始化
        self.assertEqual(pipeline.crawler, self.mock_crawler)
        self.assertEqual(pipeline.settings, self.mock_crawler.settings)
        self.assertEqual(pipeline.table_name, "test_spider_items")
        self.assertEqual(pipeline.batch_size, 100)
        self.assertEqual(pipeline.use_batch, False)
        self.assertEqual(pipeline.batch_buffer, [])
        
        # 验证订阅了关闭事件
        self.mock_crawler.subscriber.subscribe.assert_called_once_with(
            pipeline.spider_closed, event='spider_closed'
        )

    def test_make_insert_sql_default(self):
        """测试默认的SQL生成方法"""
        class TestMySQLPipeline(BaseMySQLPipeline):
            async def _ensure_pool(self):
                pass
                
        pipeline = TestMySQLPipeline(self.mock_crawler)
        item_dict = {"name": "test", "value": 123}
        
        # 由于_make_insert_sql是异步方法，我们需要运行事件循环
        async def test_async():
            with patch('crawlo.pipelines.mysql_pipeline.SQLBuilder.make_insert') as mock_make_insert:
                mock_make_insert.return_value = "TEST SQL"
                result = await pipeline._make_insert_sql(item_dict)
                mock_make_insert.assert_called_once_with(table=pipeline.table_name, data=item_dict)
                self.assertEqual(result, "TEST SQL")
                
        asyncio.run(test_async())


class TestAsyncmyMySQLPipeline(unittest.TestCase):
    """测试AsyncmyMySQLPipeline实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_crawler = Mock()
        self.mock_crawler.settings = Mock()
        self.mock_crawler.settings.get = Mock(return_value=None)
        self.mock_crawler.settings.get_int = Mock(return_value=100)
        self.mock_crawler.settings.get_bool = Mock(return_value=False)
        self.mock_crawler.subscriber = Mock()
        self.mock_crawler.subscriber.subscribe = Mock()
        
        # 模拟爬虫对象
        self.mock_spider = Mock()
        self.mock_spider.name = "test_spider"
        self.mock_spider.custom_settings = {}
        self.mock_spider.mysql_table = None
        self.mock_crawler.spider = self.mock_spider

    def test_init(self):
        """测试初始化"""
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 验证属性初始化
        self.assertEqual(pipeline.crawler, self.mock_crawler)
        self.assertEqual(pipeline.settings, self.mock_crawler.settings)
        self.assertEqual(pipeline.table_name, "test_spider_items")

    def test_from_crawler(self):
        """测试from_crawler类方法"""
        pipeline = AsyncmyMySQLPipeline.from_crawler(self.mock_crawler)
        self.assertIsInstance(pipeline, AsyncmyMySQLPipeline)
        self.assertEqual(pipeline.crawler, self.mock_crawler)


class TestAiomysqlMySQLPipeline(unittest.TestCase):
    """测试AiomysqlMySQLPipeline实现"""

    def setUp(self):
        """设置测试环境"""
        self.mock_crawler = Mock()
        self.mock_crawler.settings = Mock()
        self.mock_crawler.settings.get = Mock(return_value=None)
        self.mock_crawler.settings.get_int = Mock(return_value=100)
        self.mock_crawler.settings.get_bool = Mock(return_value=False)
        self.mock_crawler.subscriber = Mock()
        self.mock_crawler.subscriber.subscribe = Mock()
        
        # 模拟爬虫对象
        self.mock_spider = Mock()
        self.mock_spider.name = "test_spider"
        self.mock_spider.custom_settings = {}
        self.mock_spider.mysql_table = None
        self.mock_crawler.spider = self.mock_spider

    def test_init(self):
        """测试初始化"""
        pipeline = AiomysqlMySQLPipeline(self.mock_crawler)
        
        # 验证属性初始化
        self.assertEqual(pipeline.crawler, self.mock_crawler)
        self.assertEqual(pipeline.settings, self.mock_crawler.settings)
        self.assertEqual(pipeline.table_name, "test_spider_items")

    def test_from_crawler(self):
        """测试from_crawler类方法"""
        pipeline = AiomysqlMySQLPipeline.from_crawler(self.mock_crawler)
        self.assertIsInstance(pipeline, AiomysqlMySQLPipeline)
        self.assertEqual(pipeline.crawler, self.mock_crawler)


if __name__ == "__main__":
    unittest.main()