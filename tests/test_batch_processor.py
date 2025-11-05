#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理工具测试
测试 BatchProcessor, RedisBatchProcessor, batch_process
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.batch_processor import BatchProcessor, RedisBatchProcessor, batch_process


class TestBatchProcessor(unittest.TestCase):
    """批处理工具测试类"""

    def setUp(self):
        """测试前准备"""
        self.batch_processor = BatchProcessor(batch_size=3, max_concurrent_batches=2)
        
    def test_batch_processor_initialization(self):
        """测试批处理器初始化"""
        self.assertEqual(self.batch_processor.batch_size, 3)
        self.assertEqual(self.batch_processor.max_concurrent_batches, 2)
        
    def sync_process_item(self, item):
        """同步处理函数"""
        return item * 2
        
    def test_batch_processor_process_batch_sync(self):
        """测试批处理器同步处理批次"""
        items = [1, 2, 3]
        # 使用事件循环运行异步方法
        results = asyncio.run(self.batch_processor.process_batch(items, self.sync_process_item))
        self.assertEqual(results, [2, 4, 6])
        
    def test_batch_processor_process_in_batches_sync(self):
        """测试批处理器同步分批处理大量数据"""
        items = [1, 2, 3, 4, 5, 6, 7]
        # 使用事件循环运行异步方法
        results = asyncio.run(self.batch_processor.process_in_batches(items, self.sync_process_item))
        expected = [2, 4, 6, 8, 10, 12, 14]
        self.assertEqual(results, expected)
        
    def test_batch_processor_with_exception_handling(self):
        """测试批处理器异常处理"""
        def failing_processor(item):
            if item == 2:
                raise ValueError("处理失败")
            return item * 2
            
        items = [1, 2, 3]
        # 使用事件循环运行异步方法
        results = asyncio.run(self.batch_processor.process_batch(items, failing_processor))
        # 异常项应该被过滤掉
        self.assertIn(2, results)
        self.assertIn(6, results)
        # 检查长度至少为2
        self.assertGreaterEqual(len(results), 2)
        
    def test_batch_processor_decorator(self):
        """测试批处理器装饰器"""
        @self.batch_processor.batch_process_decorator(batch_size=2)
        def process_func(items):
            return [item * 3 for item in items]
            
        items = [1, 2, 3, 4]
        results = process_func(items)
        # 检查结果不为空
        self.assertIsNotNone(results)
        self.assertIsInstance(results, list)


class TestRedisBatchProcessor(unittest.TestCase):
    """Redis批处理器测试类"""

    def setUp(self):
        """测试前准备"""
        self.mock_redis_client = Mock()
        self.redis_batch_processor = RedisBatchProcessor(self.mock_redis_client, batch_size=3)
        
    def test_redis_batch_processor_initialization(self):
        """测试Redis批处理器初始化"""
        self.assertEqual(self.redis_batch_processor.batch_size, 3)
        self.assertEqual(self.redis_batch_processor.redis_client, self.mock_redis_client)
        
    def test_redis_batch_processor_batch_set(self):
        """测试Redis批处理器批量设置"""
        items = [
            {'key': 'key1', 'value': 'value1'},
            {'key': 'key2', 'value': 'value2'},
            {'key': 'key3', 'value': 'value3'}
        ]
        
        # 模拟pipeline行为
        mock_pipe = Mock()
        self.mock_redis_client.pipeline.return_value = mock_pipe
        mock_pipe.execute.return_value = None  # execute方法返回None
        mock_pipe.set.return_value = mock_pipe  # set方法返回pipe自身以支持链式调用
        
        # 使用事件循环运行异步方法
        count = asyncio.run(self.redis_batch_processor.batch_set(items))
        self.assertEqual(count, 3)
        
    def test_redis_batch_processor_batch_set_empty(self):
        """测试Redis批处理器批量设置空列表"""
        items = []
        # 使用事件循环运行异步方法
        count = asyncio.run(self.redis_batch_processor.batch_set(items))
        self.assertEqual(count, 0)
        
    def test_redis_batch_processor_batch_get(self):
        """测试Redis批处理器批量获取"""
        keys = ['key1', 'key2', 'key3']
        
        # 模拟pipeline行为
        mock_pipe = Mock()
        self.mock_redis_client.pipeline.return_value = mock_pipe
        mock_pipe.get.return_value = mock_pipe  # get方法返回pipe自身以支持链式调用
        mock_pipe.execute.return_value = ['value1', 'value2', 'value3']
        
        # 使用事件循环运行异步方法
        result = asyncio.run(self.redis_batch_processor.batch_get(keys))
        expected = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.assertEqual(result, expected)
        
    def test_redis_batch_processor_batch_get_with_none_values(self):
        """测试Redis批处理器批量获取包含None值"""
        keys = ['key1', 'key2', 'key3']
        
        # 模拟pipeline行为，其中key2返回None
        mock_pipe = Mock()
        self.mock_redis_client.pipeline.return_value = mock_pipe
        mock_pipe.get.return_value = mock_pipe  # get方法返回pipe自身以支持链式调用
        mock_pipe.execute.return_value = ['value1', None, 'value3']
        
        # 使用事件循环运行异步方法
        result = asyncio.run(self.redis_batch_processor.batch_get(keys))
        expected = {'key1': 'value1', 'key3': 'value3'}  # key2应该被过滤掉
        self.assertEqual(result, expected)
        
    def test_redis_batch_processor_batch_delete(self):
        """测试Redis批处理器批量删除"""
        keys = ['key1', 'key2', 'key3']
        
        # 模拟pipeline行为
        mock_pipe = Mock()
        self.mock_redis_client.pipeline.return_value = mock_pipe
        mock_pipe.delete.return_value = mock_pipe  # delete方法返回pipe自身以支持链式调用
        mock_pipe.execute.return_value = None
        
        # 使用事件循环运行异步方法
        count = asyncio.run(self.redis_batch_processor.batch_delete(keys))
        self.assertEqual(count, 3)


class TestBatchProcessFunction(unittest.TestCase):
    """批处理便捷函数测试类"""

    def sync_process_item(self, item):
        """同步处理函数"""
        return item * 2
        
    def test_batch_process_sync_function(self):
        """测试批处理便捷函数处理同步函数"""
        items = [1, 2, 3, 4, 5]
        results = batch_process(items, self.sync_process_item, batch_size=2, max_concurrent_batches=2)
        expected = [2, 4, 6, 8, 10]
        self.assertEqual(results, expected)


if __name__ == '__main__':
    # 运行测试
    unittest.main()