#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch
from abc import ABC, abstractmethod

from crawlo.pipelines.mysql_pipeline import BaseMySQLPipeline, AsyncmyMySQLPipeline, AiomysqlMySQLPipeline


class TestMySQLPipelineRefactor(unittest.TestCase):
    """测试MySQL管道重构"""

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

    def test_inheritance_structure(self):
        """测试继承结构"""
        # 检查两个实现类都继承自BaseMySQLPipeline
        self.assertTrue(issubclass(AsyncmyMySQLPipeline, BaseMySQLPipeline))
        self.assertTrue(issubclass(AiomysqlMySQLPipeline, BaseMySQLPipeline))
        
        # 检查基类是抽象类
        self.assertTrue(issubclass(BaseMySQLPipeline, ABC))
        
    def test_common_attributes(self):
        """测试公共属性"""
        # 由于BaseMySQLPipeline是抽象类，我们不能直接实例化它
        # 但我们可以通过子类来测试公共属性
        asyncmy_pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        aiomysql_pipeline = AiomysqlMySQLPipeline(self.mock_crawler)
        
        # 检查两个实例都有相同的公共属性
        common_attrs = ['crawler', 'settings', 'logger', 'table_name', 
                       'batch_size', 'use_batch', 'batch_buffer']
        
        for attr in common_attrs:
            self.assertTrue(hasattr(asyncmy_pipeline, attr))
            self.assertTrue(hasattr(aiomysql_pipeline, attr))
            
    def test_abstract_method_requirement(self):
        """测试抽象方法要求"""
        # 创建一个不实现_ensure_pool方法的子类应该会失败
        class IncompletePipeline(BaseMySQLPipeline):
            pass
            
        # 由于Python的ABC机制，尝试实例化没有实现抽象方法的类会抛出TypeError
        with self.assertRaises(TypeError):
            incomplete = IncompletePipeline(self.mock_crawler)
            
    def test_polymorphism(self):
        """测试多态性"""
        asyncmy_pipeline = AsyncmyMySQLPipeline(self.mock_crawler)
        aiomysql_pipeline = AiomysqlMySQLPipeline(self.mock_crawler)
        
        # 两个实例都应该有相同的公共方法
        common_methods = ['process_item', '_execute_sql', '_flush_batch', 'spider_closed']
        
        for method in common_methods:
            self.assertTrue(hasattr(asyncmy_pipeline, method))
            self.assertTrue(hasattr(aiomysql_pipeline, method))
            
    def test_specific_implementations(self):
        """测试特定实现"""
        # 检查每个类都有自己的_ensure_pool实现
        self.assertTrue(hasattr(AsyncmyMySQLPipeline, '_ensure_pool'))
        self.assertTrue(hasattr(AiomysqlMySQLPipeline, '_ensure_pool'))
        
        # 检查AiomysqlMySQLPipeline有自己特定的_make_insert_sql实现
        self.assertTrue(hasattr(AiomysqlMySQLPipeline, '_make_insert_sql'))


if __name__ == "__main__":
    unittest.main()