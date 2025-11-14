#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模爬虫辅助工具测试
测试 LargeScaleHelper, ProgressManager, MemoryOptimizer, DataSourceAdapter, LargeScaleSpiderMixin
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import json
import tempfile

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.large_scale_helper import (
    LargeScaleHelper, 
    ProgressManager, 
    MemoryOptimizer, 
    DataSourceAdapter, 
    LargeScaleSpiderMixin
)


class TestLargeScaleHelper(unittest.TestCase):
    """大规模爬虫辅助类测试"""

    def setUp(self):
        """测试前准备"""
        self.helper = LargeScaleHelper(batch_size=100, checkpoint_interval=500)
        
    def test_helper_initialization(self):
        """测试辅助类初始化"""
        self.assertEqual(self.helper.batch_size, 100)
        self.assertEqual(self.helper.checkpoint_interval, 500)
        
    def test_batch_iterator_with_list(self):
        """测试批次迭代器与列表数据源"""
        data = list(range(250))  # 250个元素
        batches = list(self.helper.batch_iterator(data))
        
        # 验证批次数量
        self.assertEqual(len(batches), 3)  # 250/100 = 3批次(向上取整)
        
        # 验证每个批次的大小
        self.assertEqual(len(batches[0]), 100)
        self.assertEqual(len(batches[1]), 100)
        self.assertEqual(len(batches[2]), 50)  # 最后一个批次
        
        # 验证数据完整性
        all_data = []
        for batch in batches:
            all_data.extend(batch)
        self.assertEqual(all_data, data)
        
    def test_batch_iterator_with_offset(self):
        """测试批次迭代器与偏移量"""
        data = list(range(250))  # 250个元素
        batches = list(self.helper.batch_iterator(data, start_offset=50))
        
        # 验证批次数量
        self.assertEqual(len(batches), 2)  # 剩余200个元素，2个批次
        
        # 验证数据正确性
        all_data = []
        for batch in batches:
            all_data.extend(batch)
        self.assertEqual(all_data, list(range(50, 250)))
        
    def test_batch_iterator_invalid_source(self):
        """测试批次迭代器与无效数据源"""
        with self.assertRaises(ValueError) as context:
            list(self.helper.batch_iterator(123))  # 整数不是有效的数据源
        self.assertIn("不支持的数据源类型", str(context.exception))


class TestProgressManager(unittest.TestCase):
    """进度管理器测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时文件用于测试
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.progress_manager = ProgressManager(self.temp_file.name)
        
    def tearDown(self):
        """测试后清理"""
        try:
            os.unlink(self.temp_file.name)
        except:
            pass
            
    def test_progress_manager_initialization(self):
        """测试进度管理器初始化"""
        self.assertEqual(self.progress_manager.progress_file, self.temp_file.name)
        
    def test_save_and_load_progress(self):
        """测试保存和加载进度"""
        # 保存进度
        self.progress_manager.save_progress(
            batch_num=10,
            processed_count=1000,
            skipped_count=50
        )
        
        # 加载进度
        progress = self.progress_manager.load_progress()
        
        # 验证进度数据
        self.assertEqual(progress['batch_num'], 10)
        self.assertEqual(progress['processed_count'], 1000)
        self.assertEqual(progress['skipped_count'], 50)
        self.assertIn('timestamp', progress)
        self.assertIn('formatted_time', progress)
        
    def test_load_progress_file_not_found(self):
        """测试加载不存在的进度文件"""
        # 创建一个新的进度管理器与不存在的文件
        non_existent_file = tempfile.gettempdir() + "/non_existent_progress.json"
        pm = ProgressManager(non_existent_file)
        
        # 加载进度应该返回默认值
        progress = pm.load_progress()
        self.assertEqual(progress['batch_num'], 0)
        self.assertEqual(progress['processed_count'], 0)
        self.assertEqual(progress['skipped_count'], 0)


class TestMemoryOptimizer(unittest.TestCase):
    """内存优化器测试"""

    def setUp(self):
        """测试前准备"""
        self.optimizer = MemoryOptimizer(max_memory_mb=100)
        
    def test_optimizer_initialization(self):
        """测试内存优化器初始化"""
        self.assertEqual(self.optimizer.max_memory_mb, 100)
        
    def test_should_pause_for_memory_without_psutil(self):
        """测试在没有psutil时的内存检查"""
        # 在没有psutil的情况下，should_pause_for_memory应该返回False
        result = self.optimizer.should_pause_for_memory()
        self.assertFalse(result)
        
    def test_force_garbage_collection(self):
        """测试强制垃圾回收"""
        # 这个方法应该能正常执行而不抛出异常
        try:
            self.optimizer.force_garbage_collection()
            success = True
        except:
            success = False
        self.assertTrue(success)


class TestDataSourceAdapter(unittest.TestCase):
    """数据源适配器测试"""

    def test_from_file_adapter(self):
        """测试文件数据源适配器"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            for i in range(10):
                f.write(f"line {i}\n")
            temp_file_name = f.name
            
        try:
            # 创建文件数据源适配器
            adapter = DataSourceAdapter.from_file(temp_file_name, batch_size=5)
            
            # 获取第一批数据
            batch = adapter(0, 5)
            self.assertEqual(len(batch), 5)
            self.assertEqual(batch[0], "line 0")
            self.assertEqual(batch[4], "line 4")
            
            # 获取第二批数据
            batch = adapter(5, 5)
            self.assertEqual(len(batch), 5)
            self.assertEqual(batch[0], "line 5")
            self.assertEqual(batch[4], "line 9")
            
        finally:
            # 清理临时文件
            os.unlink(temp_file_name)


class TestLargeScaleSpiderMixin(unittest.TestCase):
    """大规模爬虫混入类测试"""

    def test_mixin_initialization(self):
        """测试混入类初始化"""
        # 创建一个模拟的爬虫类
        class MockSpider:
            def __init__(self):
                self.name = "test_spider"
                
        class TestSpider(MockSpider, LargeScaleSpiderMixin):
            def __init__(self):
                MockSpider.__init__(self)
                LargeScaleSpiderMixin.__init__(self)
                
        spider = TestSpider()
        
        # 验证初始化
        self.assertEqual(spider.name, "test_spider")
        self.assertIsNotNone(spider.large_scale_helper)
        self.assertIsNotNone(spider.progress_manager)
        self.assertIsNotNone(spider.memory_optimizer)
        
    def test_mixin_attributes(self):
        """测试混入类属性"""
        # 创建一个模拟的爬虫类
        class MockSpider:
            def __init__(self):
                self.name = "test_spider"
                
        class TestSpider(MockSpider, LargeScaleSpiderMixin):
            def __init__(self):
                MockSpider.__init__(self)
                LargeScaleSpiderMixin.__init__(self)
                
        spider = TestSpider()
        
        # 验证属性
        self.assertIsInstance(spider.large_scale_helper, LargeScaleHelper)
        self.assertIsInstance(spider.progress_manager, ProgressManager)
        self.assertIsInstance(spider.memory_optimizer, MemoryOptimizer)


if __name__ == '__main__':
    unittest.main()