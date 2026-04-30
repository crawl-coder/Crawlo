#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
去重管道指纹一致性测试
==================
验证所有去重管道对相同数据生成一致的指纹
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.fingerprint import FingerprintGenerator
from tests.fixtures.mock_item import MockItem


def test_pipeline_fingerprint_consistency():
    """测试各管道指纹一致性"""
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
    
    # 验证指纹生成的稳定性
    for i in range(5):
        fingerprint = FingerprintGenerator.item_fingerprint(test_item)
        print(f"Generated fingerprint {i+1}: {fingerprint}")
        assert fingerprint == expected_fingerprint, f"Fingerprint mismatch at iteration {i+1}"
    
    print("\n✓ 所有指纹生成一致")
    
    # 测试不同数据生成不同指纹
    test_item2 = MockItem(
        title="Test Title 2",
        url="https://example.com",
        content="Test content",
        price=99.99
    )
    
    fingerprint2 = FingerprintGenerator.item_fingerprint(test_item2)
    print(f"\nDifferent item fingerprint: {fingerprint2}")
    assert fingerprint2 != expected_fingerprint, "Different items should generate different fingerprints"
    
    print("✓ 不同数据生成不同指纹")


def test_data_fingerprint_variants():
    """测试不同数据类型的指纹生成"""
    # 测试字典
    dict_data = {"name": "test", "value": 123}
    dict_fingerprint = FingerprintGenerator.data_fingerprint(dict_data)
    print(f"\nDict fingerprint: {dict_fingerprint}")
    
    # 测试相同内容的字典（不同顺序）
    dict_data2 = {"value": 123, "name": "test"}
    dict_fingerprint2 = FingerprintGenerator.data_fingerprint(dict_data2)
    print(f"Reordered dict fingerprint: {dict_fingerprint2}")
    assert dict_fingerprint == dict_fingerprint2, "Reordered dict should generate same fingerprint"
    
    print("✓ 字典顺序不影响指纹生成")


if __name__ == '__main__':
    test_pipeline_fingerprint_consistency()
    test_data_fingerprint_variants()
    print("\n🎉 所有测试通过!")