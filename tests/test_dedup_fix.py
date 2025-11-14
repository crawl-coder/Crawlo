#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去重管道异常处理修复测试
验证去重管道抛出的异常能被正确处理，防止重复数据传递到后续管道
"""
import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock
from collections import namedtuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.pipelines.redis_dedup_pipeline import RedisDedupPipeline
from crawlo.pipelines.memory_dedup_pipeline import MemoryDedupPipeline
from crawlo.pipelines.bloom_dedup_pipeline import BloomDedupPipeline
from crawlo.pipelines.pipeline_manager import PipelineManager
from crawlo.exceptions import ItemDiscard


class TestDedupFix(unittest.TestCase):
    """去重管道异常处理修复测试"""

    def setUp(self):
        """测试初始化"""
        # 创建模拟的crawler对象
        self.mock_crawler = Mock()
        self.mock_crawler.settings = Mock()
        self.mock_crawler.settings.get = Mock(return_value="INFO")
        self.mock_crawler.settings.get_int = Mock(return_value=0)
        self.mock_crawler.settings.get_bool = Mock(return_value=False)
        self.mock_crawler.subscriber = Mock()
        self.mock_crawler.subscriber.subscribe = Mock()
        
        # 创建简单的测试数据项（使用namedtuple模拟Item）
        self.TestItem = namedtuple('TestItem', ['title', 'url', 'content'])
        self.test_item = self.TestItem(
            title="Test Title",
            url="http://example.com",
            content="Test content"
        )

    def test_redis_dedup_pipeline_exception_type(self):
        """测试Redis去重管道抛出正确的异常类型"""
        # 创建Redis去重管道实例
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis_instance.sadd = Mock(return_value=0)  # 模拟已存在的指纹
            mock_redis.return_value = mock_redis_instance
            
            pipeline = RedisDedupPipeline(
                redis_host='localhost',
                redis_port=6379,
                redis_db=0,
                redis_password=None,
                redis_key='test:key',
                log_level='INFO'
            )
            
            # 验证抛出的是ItemDiscard异常
            with self.assertRaises(ItemDiscard) as context:
                pipeline.process_item(self.test_item, Mock())
            
            # 验证异常消息
            self.assertIn("Duplicate item:", str(context.exception))

    def test_memory_dedup_pipeline_exception_type(self):
        """测试内存去重管道抛出正确的异常类型"""
        # 创建内存去重管道实例
        pipeline = MemoryDedupPipeline(log_level='INFO')
        
        # 添加一个指纹到已见过的集合中
        fingerprint = pipeline._generate_item_fingerprint(self.test_item)
        pipeline.seen_items.add(fingerprint)
        
        # 验证抛出的是ItemDiscard异常
        with self.assertRaises(ItemDiscard) as context:
            pipeline.process_item(self.test_item, Mock())
        
        # 验证异常消息
        self.assertIn("重复的数据项:", str(context.exception))

    def test_bloom_dedup_pipeline_exception_type(self):
        """测试Bloom去重管道抛出正确的异常类型"""
        # 创建Bloom去重管道实例
        pipeline = BloomDedupPipeline(log_level='INFO')
        
        # 添加一个指纹到Bloom过滤器中
        fingerprint = pipeline._generate_item_fingerprint(self.test_item)
        pipeline.bloom_filter.add(fingerprint)
        
        # 验证抛出的是ItemDiscard异常
        with self.assertRaises(ItemDiscard) as context:
            pipeline.process_item(self.test_item, Mock())
        
        # 验证异常消息
        self.assertIn("可能重复的数据项:", str(context.exception))

    async def test_pipeline_manager_exception_handling(self):
        """测试管道管理器能正确处理ItemDiscard异常"""
        # 创建管道管理器实例
        pipeline_manager = PipelineManager(self.mock_crawler)
        
        # 创建测试数据项
        test_item = self.TestItem(
            title="Test Title",
            url="http://example.com",
            content="Test content"
        )
        
        # 模拟管道方法列表
        pipeline_manager.methods = []
        
        # 创建模拟的去重管道方法（抛出ItemDiscard异常）
        mock_dedup_method = Mock()
        mock_dedup_method.side_effect = ItemDiscard("测试ItemDiscard异常")
        
        # 创建模拟的MySQL管道方法
        mock_mysql_method = Mock()
        mock_mysql_method.return_value = test_item
        
        pipeline_manager.methods = [mock_dedup_method, mock_mysql_method]
        
        # 测试处理数据项
        with patch('crawlo.pipelines.pipeline_manager.common_call') as mock_common_call, \
             patch('crawlo.pipelines.pipeline_manager.create_task') as mock_create_task:
            
            # 设置common_call的副作用来模拟异常
            async def mock_common_call_func(method, *args, **kwargs):
                if method == mock_dedup_method:
                    raise ItemDiscard("测试ItemDiscard异常")
                return test_item
                
            mock_common_call.side_effect = mock_common_call_func
            
            # 调用处理方法
            await pipeline_manager.process_item(test_item)
            
            # 验证ItemDiscard异常被正确处理
            # 验证create_task被调用了一次（item_discard事件）
            self.assertEqual(mock_create_task.call_count, 1)
            
            # 验证MySQL管道方法没有被调用
            mock_mysql_method.assert_not_called()

    async def test_pipeline_manager_dropitem_exception_handling(self):
        """测试管道管理器能正确处理ItemDiscard异常（重复测试）"""
        # 创建管道管理器实例
        pipeline_manager = PipelineManager(self.mock_crawler)
        
        # 创建测试数据项
        test_item = self.TestItem(
            title="Test Title",
            url="http://example.com",
            content="Test content"
        )
        
        # 模拟管道方法列表
        pipeline_manager.methods = []
        
        # 创建模拟的去重管道方法（抛出ItemDiscard异常）
        mock_dedup_method = Mock()
        mock_dedup_method.side_effect = ItemDiscard("测试ItemDiscard异常")
        
        # 创建模拟的MySQL管道方法
        mock_mysql_method = Mock()
        mock_mysql_method.return_value = test_item
        
        pipeline_manager.methods = [mock_dedup_method, mock_mysql_method]
        
        # 测试处理数据项
        with patch('crawlo.pipelines.pipeline_manager.common_call') as mock_common_call, \
             patch('crawlo.pipelines.pipeline_manager.create_task') as mock_create_task:
            
            # 设置common_call的副作用来模拟异常
            async def mock_common_call_func(method, *args, **kwargs):
                if method == mock_dedup_method:
                    raise ItemDiscard("测试ItemDiscard异常")
                return test_item
                
            mock_common_call.side_effect = mock_common_call_func
            
            # 调用处理方法
            await pipeline_manager.process_item(test_item)
            
            # 验证ItemDiscard异常被正确处理
            # 验证create_task被调用了一次（item_discard事件）
            self.assertEqual(mock_create_task.call_count, 1)
            
            # 验证MySQL管道方法没有被调用
            mock_mysql_method.assert_not_called()


async def main():
    """主测试函数"""
    print("开始去重管道异常处理修复测试...")
    print("=" * 50)
    
    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestDedupFix)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("=" * 50)
    if result.wasSuccessful():
        print("所有测试通过！去重管道异常处理修复验证成功")
        return 0
    else:
        print("部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)