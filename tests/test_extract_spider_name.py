#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从Redis key中提取spider_name
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import RedisKeyManager


def test_extract_spider_name():
    """测试从Redis key中提取spider_name"""
    print("测试从Redis key中提取spider_name...")
    print("=" * 50)
    
    # 测试1: 包含spider_name的key
    print("1. 测试包含spider_name的key...")
    key1 = "crawlo:my_project:my_spider:queue:requests"
    spider_name1 = RedisKeyManager.extract_spider_name_from_key(key1)
    print(f"   Key: {key1}")
    print(f"   提取的spider_name: {spider_name1}")
    assert spider_name1 == "my_spider", f"期望: my_spider, 实际: {spider_name1}"
    print("   ✅ 包含spider_name的key测试通过")
    
    # 测试2: 不包含spider_name的key
    print("\n2. 测试不包含spider_name的key...")
    key2 = "crawlo:my_project:queue:requests"
    spider_name2 = RedisKeyManager.extract_spider_name_from_key(key2)
    print(f"   Key: {key2}")
    print(f"   提取的spider_name: {spider_name2}")
    assert spider_name2 is None, f"期望: None, 实际: {spider_name2}"
    print("   ✅ 不包含spider_name的key测试通过")
    
    # 测试3: 包含spider_name但组件是filter的key
    print("\n3. 测试包含spider_name但组件是filter的key...")
    key3 = "crawlo:my_project:my_spider:filter:fingerprint"
    spider_name3 = RedisKeyManager.extract_spider_name_from_key(key3)
    print(f"   Key: {key3}")
    print(f"   提取的spider_name: {spider_name3}")
    assert spider_name3 == "my_spider", f"期望: my_spider, 实际: {spider_name3}"
    print("   ✅ 包含spider_name但组件是filter的key测试通过")
    
    # 测试4: 包含spider_name但组件是item的key
    print("\n4. 测试包含spider_name但组件是item的key...")
    key4 = "crawlo:my_project:my_spider:item:fingerprint"
    spider_name4 = RedisKeyManager.extract_spider_name_from_key(key4)
    print(f"   Key: {key4}")
    print(f"   提取的spider_name: {spider_name4}")
    assert spider_name4 == "my_spider", f"期望: my_spider, 实际: {spider_name4}"
    print("   ✅ 包含spider_name但组件是item的key测试通过")
    
    print("\n✅ 所有测试通过！spider_name提取功能正常工作。")


if __name__ == "__main__":
    test_extract_spider_name()