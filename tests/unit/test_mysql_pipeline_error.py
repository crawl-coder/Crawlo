#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock

from crawlo.pipelines.sql.mysql import MySQLPipeline
from crawlo.items.exceptions import ItemDiscard


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
        """测试MySQLPipeline处理连接错误（通过 mock _helper 模拟异常）"""
        from unittest.mock import patch

        pipeline = MySQLPipeline(self.mock_crawler)

        # 跳过真实连接池初始化
        pipeline._initialized = True
        pipeline.pool = AsyncMock()

        # mock _helper.insert 抛出异常，避免真实 MySQL 连接
        mock_helper = AsyncMock()
        mock_helper.insert = AsyncMock(side_effect=Exception("测试异常"))
        pipeline._helper = mock_helper

        # 测试数据
        test_item = {"id": 1, "name": "test"}

        async def test_async():
            # mock is_pool_active 返回 True，避免触发真实连接池初始化
            with patch('crawlo.pipelines.sql.mysql.is_pool_active', return_value=True):
                with self.assertRaises(ItemDiscard) as context:
                    await pipeline.process_item(test_item, self.mock_spider)

                # process_item 层包装为 ItemDiscard("Insert failed: ...")
                self.assertIn("Insert failed", str(context.exception))

        asyncio.run(test_async())

    def test_execute_sql_with_exception(self):
        """测试_do_insert方法处理异常（_execute_sql 已重构为 _do_insert）"""
        pipeline = MySQLPipeline(self.mock_crawler)

        # _do_insert 委托给 _helper.insert，需要 mock _helper
        mock_helper = AsyncMock()
        mock_helper.insert = AsyncMock(side_effect=Exception("测试异常"))
        pipeline._helper = mock_helper

        async def test_async():
            with self.assertRaises(Exception) as context:
                await pipeline._do_insert({"id": 1, "name": "test"})

            # _do_insert 直接委托 _helper.insert，异常向上传播
            # process_item 层会包装为 ItemDiscard("Insert failed: ...")
            self.assertIn("测试异常", str(context.exception))

        asyncio.run(test_async())


if __name__ == "__main__":
    unittest.main()