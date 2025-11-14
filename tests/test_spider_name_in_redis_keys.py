#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Redis key中spider_name的使用
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import RedisKeyManager


def test_spider_name_in_keys():
    """测试spider_name是否正确地被使用在Redis key中"""
    print("测试Redis key中spider_name的使用...")
    print("=" * 50)
    
    # 测试1: 只有project_name
    print("1. 测试只有project_name的情况...")
    key_manager1 = RedisKeyManager("my_project")
    print(f"   请求队列key: {key_manager1.get_requests_queue_key()}")
    print(f"   处理队列key: {key_manager1.get_processing_queue_key()}")
    print(f"   过滤器key: {key_manager1.get_filter_fingerprint_key()}")
    print(f"   数据项key: {key_manager1.get_item_fingerprint_key()}")
    
    expected1 = "crawlo:my_project:queue:requests"
    actual1 = key_manager1.get_requests_queue_key()
    assert actual1 == expected1, f"期望: {expected1}, 实际: {actual1}"
    print("   ✅ 只有project_name的测试通过")
    
    # 测试2: 有project_name和spider_name
    print("\n2. 测试有project_name和spider_name的情况...")
    key_manager2 = RedisKeyManager("my_project", "my_spider")
    print(f"   请求队列key: {key_manager2.get_requests_queue_key()}")
    print(f"   处理队列key: {key_manager2.get_processing_queue_key()}")
    print(f"   过滤器key: {key_manager2.get_filter_fingerprint_key()}")
    print(f"   数据项key: {key_manager2.get_item_fingerprint_key()}")
    
    expected2 = "crawlo:my_project:my_spider:queue:requests"
    actual2 = key_manager2.get_requests_queue_key()
    assert actual2 == expected2, f"期望: {expected2}, 实际: {actual2}"
    print("   ✅ 有project_name和spider_name的测试通过")
    
    # 测试3: 动态设置spider_name
    print("\n3. 测试动态设置spider_name...")
    key_manager3 = RedisKeyManager("my_project")
    print(f"   设置spider_name前的请求队列key: {key_manager3.get_requests_queue_key()}")
    
    key_manager3.set_spider_name("dynamic_spider")
    print(f"   设置spider_name后的请求队列key: {key_manager3.get_requests_queue_key()}")
    
    expected3 = "crawlo:my_project:dynamic_spider:queue:requests"
    actual3 = key_manager3.get_requests_queue_key()
    assert actual3 == expected3, f"期望: {expected3}, 实际: {actual3}"
    print("   ✅ 动态设置spider_name的测试通过")
    
    # 测试4: 从配置创建key manager
    print("\n4. 测试从配置创建key manager...")
    class MockSettings:
        def get(self, key, default=None):
            settings_map = {
                'PROJECT_NAME': 'config_project',
                'SPIDER_NAME': 'config_spider'
            }
            return settings_map.get(key, default)
    
    settings = MockSettings()
    key_manager4 = RedisKeyManager.from_settings(settings)
    print(f"   从配置创建的请求队列key: {key_manager4.get_requests_queue_key()}")
    
    expected4 = "crawlo:config_project:config_spider:queue:requests"
    actual4 = key_manager4.get_requests_queue_key()
    assert actual4 == expected4, f"期望: {expected4}, 实际: {actual4}"
    print("   ✅ 从配置创建key manager的测试通过")
    
    print("\n✅ 所有测试通过！spider_name正确地被使用在Redis key中。")


if __name__ == "__main__":
    test_spider_name_in_keys()