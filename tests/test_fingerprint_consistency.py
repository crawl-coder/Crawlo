#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
指纹一致性测试
==============
验证框架中各组件对相同数据生成一致的指纹
"""

import unittest
from unittest.mock import Mock

from crawlo import Item
from crawlo.pipelines.memory_dedup_pipeline import MemoryDedupPipeline
from crawlo.pipelines.redis_dedup_pipeline import RedisDedupPipeline
from crawlo.pipelines.bloom_dedup_pipeline import BloomDedupPipeline
from crawlo.pipelines.database_dedup_pipeline import DatabaseDedupPipeline
from crawlo.tools.distributed_coordinator import DeduplicationTool
from crawlo.utils.fingerprint import FingerprintGenerator


class TestItem(Item):
    """测试用数据项类"""
    
    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


class FingerprintConsistencyTest(unittest.TestCase):
    """指纹一致性测试"""
    
    def setUp(self):
        """测试初始化"""
        # 创建测试数据项
        self.test_item = TestItem(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            price=99.99
        )
        
        # 创建各去重管道实例
        self.memory_pipeline = MemoryDedupPipeline()
        self.redis_pipeline = RedisDedupPipeline(
            redis_host='localhost',
            redis_port=6379,
            redis_db=0,
            redis_key='test:fingerprints'
        )
        self.bloom_pipeline = BloomDedupPipeline()
        self.database_pipeline = DatabaseDedupPipeline()
        
        # 创建去重工具实例
        self.dedup_tool = DeduplicationTool()
    
    def test_item_fingerprint_consistency(self):
        """测试数据项指纹一致性"""
        # 使用各管道生成指纹
        memory_fingerprint = self.memory_pipeline._generate_item_fingerprint(self.test_item)
        redis_fingerprint = self.redis_pipeline._generate_item_fingerprint(self.test_item)
        bloom_fingerprint = self.bloom_pipeline._generate_item_fingerprint(self.test_item)
        database_fingerprint = self.database_pipeline._generate_item_fingerprint(self.test_item)
        
        # 使用指纹生成器直接生成指纹
        direct_fingerprint = FingerprintGenerator.item_fingerprint(self.test_item)
        
        # 验证所有指纹一致
        self.assertEqual(memory_fingerprint, redis_fingerprint)
        self.assertEqual(memory_fingerprint, bloom_fingerprint)
        self.assertEqual(memory_fingerprint, database_fingerprint)
        self.assertEqual(memory_fingerprint, direct_fingerprint)
        
        print(f"Memory Pipeline Fingerprint: {memory_fingerprint}")
        print(f"Redis Pipeline Fingerprint: {redis_fingerprint}")
        print(f"Bloom Pipeline Fingerprint: {bloom_fingerprint}")
        print(f"Database Pipeline Fingerprint: {database_fingerprint}")
        print(f"Direct Fingerprint: {direct_fingerprint}")
    
    def test_data_fingerprint_consistency(self):
        """测试通用数据指纹一致性"""
        # 测试字典数据
        test_data = {
            "name": "test",
            "value": 123,
            "nested": {
                "inner": "value"
            }
        }
        
        # 使用去重工具生成指纹
        tool_fingerprint = self.dedup_tool.generate_fingerprint(test_data)
        
        # 使用指纹生成器生成指纹
        generator_fingerprint = FingerprintGenerator.data_fingerprint(test_data)
        
        # 验证指纹一致
        self.assertEqual(tool_fingerprint, generator_fingerprint)
        
        print(f"DeduplicationTool Fingerprint: {tool_fingerprint}")
        print(f"FingerprintGenerator Fingerprint: {generator_fingerprint}")
    
    def test_fingerprint_stability(self):
        """测试指纹稳定性"""
        # 创建相同的测试数据项多次
        item1 = TestItem(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            price=99.99
        )
        
        item2 = TestItem(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            price=99.99
        )
        
        # 生成指纹
        fingerprint1 = FingerprintGenerator.item_fingerprint(item1)
        fingerprint2 = FingerprintGenerator.item_fingerprint(item2)
        
        # 验证相同数据生成相同指纹
        self.assertEqual(fingerprint1, fingerprint2)
        
        print(f"First fingerprint: {fingerprint1}")
        print(f"Second fingerprint: {fingerprint2}")


if __name__ == '__main__':
    unittest.main()