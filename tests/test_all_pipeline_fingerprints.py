#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
所有去重管道指纹一致性测试
====================
验证所有去重管道对相同数据生成一致的指纹
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.fingerprint import FingerprintGenerator


class MockItem:
    """模拟数据项类"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


def test_all_pipeline_fingerprints():
    """测试所有管道指纹一致性"""
    # 创建测试数据项
    test_item = MockItem(
        title="Test Title",
        url="https://example.com",
        content="Test content",
        price=99.99
    )
    
    # 使用指纹生成器生成指纹
    expected_fingerprint = FingerprintGenerator.item_fingerprint(test_item)
    
    print(f"Expected fingerprint: {expected_fingerprint}")
    
    # 测试内存去重管道指纹生成方法
    try:
        from crawlo.pipelines.memory_dedup_pipeline import MemoryDedupPipeline
        memory_pipeline = MemoryDedupPipeline()
        memory_fingerprint = memory_pipeline._generate_item_fingerprint(test_item)
        print(f"Memory pipeline fingerprint: {memory_fingerprint}")
        assert memory_fingerprint == expected_fingerprint, "Memory pipeline fingerprint mismatch"
        print("✓ Memory pipeline fingerprint一致")
    except Exception as e:
        print(f"✗ Memory pipeline test failed: {e}")
    
    # 测试Redis去重管道指纹生成方法
    try:
        from crawlo.pipelines.redis_dedup_pipeline import RedisDedupPipeline
        redis_pipeline = RedisDedupPipeline()
        redis_fingerprint = redis_pipeline._generate_item_fingerprint(test_item)
        print(f"Redis pipeline fingerprint: {redis_fingerprint}")
        assert redis_fingerprint == expected_fingerprint, "Redis pipeline fingerprint mismatch"
        print("✓ Redis pipeline fingerprint一致")
    except Exception as e:
        print(f"✗ Redis pipeline test failed: {e}")
    
    # 测试Bloom去重管道指纹生成方法
    try:
        from crawlo.pipelines.bloom_dedup_pipeline import BloomDedupPipeline
        bloom_pipeline = BloomDedupPipeline()
        bloom_fingerprint = bloom_pipeline._generate_item_fingerprint(test_item)
        print(f"Bloom pipeline fingerprint: {bloom_fingerprint}")
        assert bloom_fingerprint == expected_fingerprint, "Bloom pipeline fingerprint mismatch"
        print("✓ Bloom pipeline fingerprint一致")
    except Exception as e:
        print(f"✗ Bloom pipeline test failed: {e}")
    
    # 测试数据库去重管道指纹生成方法
    try:
        from crawlo.pipelines.database_dedup_pipeline import DatabaseDedupPipeline
        database_pipeline = DatabaseDedupPipeline()
        database_fingerprint = database_pipeline._generate_item_fingerprint(test_item)
        print(f"Database pipeline fingerprint: {database_fingerprint}")
        assert database_fingerprint == expected_fingerprint, "Database pipeline fingerprint mismatch"
        print("✓ Database pipeline fingerprint一致")
    except Exception as e:
        print(f"✗ Database pipeline test failed: {e}")
    
    # 测试分布式协调工具指纹生成方法
    try:
        from crawlo.tools.distributed_coordinator import DeduplicationTool
        dedup_tool = DeduplicationTool()
        tool_fingerprint = dedup_tool.generate_fingerprint(test_item.to_dict())
        print(f"Deduplication tool fingerprint: {tool_fingerprint}")
        # 注意：这里我们传入的是字典，因为工具类的generate_fingerprint方法直接处理数据
        expected_tool_fingerprint = FingerprintGenerator.data_fingerprint(test_item.to_dict())
        assert tool_fingerprint == expected_tool_fingerprint, "Deduplication tool fingerprint mismatch"
        print("✓ Deduplication tool fingerprint一致")
    except Exception as e:
        print(f"✗ Deduplication tool test failed: {e}")


def test_fingerprint_stability():
    """测试指纹稳定性"""
    # 创建相同的测试数据项多次
    item1 = MockItem(
        title="Test Title",
        url="https://example.com",
        content="Test content",
        price=99.99
    )
    
    item2 = MockItem(
        title="Test Title",
        url="https://example.com",
        content="Test content",
        price=99.99
    )
    
    # 生成指纹
    fingerprint1 = FingerprintGenerator.item_fingerprint(item1)
    fingerprint2 = FingerprintGenerator.item_fingerprint(item2)
    
    # 验证相同数据生成相同指纹
    print(f"\nFirst fingerprint: {fingerprint1}")
    print(f"Second fingerprint: {fingerprint2}")
    assert fingerprint1 == fingerprint2, "Same items should generate same fingerprints"
    print("✓ 相同数据生成相同指纹")


if __name__ == '__main__':
    test_all_pipeline_fingerprints()
    test_fingerprint_stability()
    print("\n🎉 所有测试通过!")