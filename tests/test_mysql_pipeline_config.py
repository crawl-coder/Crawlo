#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.pipelines.mysql_pipeline import BaseMySQLPipeline, AsyncmyMySQLPipeline, AiomysqlMySQLPipeline


class TestMySQLPipelineConfig(unittest.TestCase):
    """测试MySQL管道配置"""

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

    def test_default_config_values(self):
        """测试默认配置值"""
        # 设置默认返回值（模拟默认配置文件中的值）
        self.mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'MYSQL_AUTO_UPDATE': False,
            'MYSQL_INSERT_IGNORE': False,
            'MYSQL_USE_BATCH': False
        }.get(key, default))
        
        self.mock_crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'MYSQL_UPDATE_COLUMNS': ()
        }.get(key, default))
        
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 验证默认配置值
        self.assertEqual(pipeline.auto_update, False)
        self.assertEqual(pipeline.insert_ignore, False)
        self.assertEqual(pipeline.update_columns, ())

    def test_custom_config_values(self):
        """测试自定义配置值"""
        # 设置自定义配置值
        self.mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'MYSQL_AUTO_UPDATE': True,
            'MYSQL_INSERT_IGNORE': True
        }.get(key, default))
        
        self.mock_crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'MYSQL_UPDATE_COLUMNS': ('updated_at', 'view_count')
        }.get(key, default))
        
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 验证自定义配置值
        self.assertEqual(pipeline.auto_update, True)
        self.assertEqual(pipeline.insert_ignore, True)
        self.assertEqual(pipeline.update_columns, ('updated_at', 'view_count'))

    def test_sql_generation_with_config(self):
        """测试使用配置生成SQL"""
        # 设置配置
        self.mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'MYSQL_AUTO_UPDATE': True,
            'MYSQL_INSERT_IGNORE': False
        }.get(key, default))
        
        self.mock_crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'MYSQL_UPDATE_COLUMNS': ()
        }.get(key, default))
        
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 测试数据
        item_dict = {"id": 1, "name": "test"}
        
        async def test_async():
            with patch('crawlo.pipelines.mysql_pipeline.SQLBuilder.make_insert') as mock_make_insert:
                mock_make_insert.return_value = "TEST SQL"
                
                # 调用_make_insert_sql方法
                result = await pipeline._make_insert_sql(item_dict)
                
                # 验证调用了SQLBuilder.make_insert并传递了正确的参数
                mock_make_insert.assert_called_once()
                call_args = mock_make_insert.call_args
                self.assertEqual(call_args[1]['auto_update'], True)
                self.assertEqual(call_args[1]['insert_ignore'], False)
                self.assertEqual(call_args[1]['update_columns'], ())
                
        asyncio.run(test_async())

    def test_sql_generation_with_kwargs_override(self):
        """测试使用kwargs覆盖配置生成SQL"""
        # 设置配置
        self.mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'MYSQL_AUTO_UPDATE': False,
            'MYSQL_INSERT_IGNORE': False
        }.get(key, default))
        
        self.mock_crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'MYSQL_UPDATE_COLUMNS': ()
        }.get(key, default))
        
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 测试数据
        item_dict = {"id": 1, "name": "test"}
        
        async def test_async():
            with patch('crawlo.pipelines.mysql_pipeline.SQLBuilder.make_insert') as mock_make_insert:
                mock_make_insert.return_value = "TEST SQL"
                
                # 调用_make_insert_sql方法并传递kwargs
                result = await pipeline._make_insert_sql(
                    item_dict, 
                    auto_update=True, 
                    insert_ignore=True
                )
                
                # 验证kwargs覆盖了配置
                mock_make_insert.assert_called_once()
                call_args = mock_make_insert.call_args
                self.assertEqual(call_args[1]['auto_update'], True)
                self.assertEqual(call_args[1]['insert_ignore'], True)
                self.assertEqual(call_args[1]['update_columns'], ())
                
        asyncio.run(test_async())

    def test_batch_config_passing(self):
        """测试批量处理中配置的传递"""
        # 设置配置
        self.mock_crawler.settings.get_bool = Mock(side_effect=lambda key, default: {
            'MYSQL_AUTO_UPDATE': True,
            'MYSQL_INSERT_IGNORE': False,
            'MYSQL_USE_BATCH': True
        }.get(key, default))
        
        self.mock_crawler.settings.get = Mock(side_effect=lambda key, default=None: {
            'MYSQL_UPDATE_COLUMNS': ('updated_at',)
        }.get(key, default))
        
        self.mock_crawler.settings.get_int = Mock(side_effect=lambda key, default=100: {
            'MYSQL_BATCH_SIZE': 2
        }.get(key, default))
        
        pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        
        # 验证配置已正确设置
        self.assertEqual(pipeline.auto_update, True)
        self.assertEqual(pipeline.update_columns, ('updated_at',))
        self.assertEqual(pipeline.use_batch, True)
        self.assertEqual(pipeline.batch_size, 2)


if __name__ == "__main__":
    unittest.main()