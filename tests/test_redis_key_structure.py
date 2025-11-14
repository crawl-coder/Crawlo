#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Redis key的结构
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import RedisKeyManager


def test_redis_key_structure():
    """测试Redis key的结构"""
    print("测试Redis key的结构...")
    print("=" * 50)
    
    # 创建一个包含project_name和spider_name的key manager
    key_manager = RedisKeyManager("ofweek_standalone", "ofweek_spider")
    
    # 获取各种key
    requests_queue_key = key_manager.get_requests_queue_key()
    processing_queue_key = key_manager.get_processing_queue_key()
    filter_key = key_manager.get_filter_fingerprint_key()
    item_key = key_manager.get_item_fingerprint_key()
    
    print(f"请求队列key: {requests_queue_key}")
    print(f"处理队列key: {processing_queue_key}")
    print(f"过滤器key: {filter_key}")
    print(f"数据项key: {item_key}")
    
    # 验证key的结构
    expected_prefix = "crawlo:ofweek_standalone:ofweek_spider"
    assert requests_queue_key.startswith(expected_prefix), f"请求队列key前缀不正确: {requests_queue_key}"
    assert processing_queue_key.startswith(expected_prefix), f"处理队列key前缀不正确: {processing_queue_key}"
    assert filter_key.startswith(expected_prefix), f"过滤器key前缀不正确: {filter_key}"
    assert item_key.startswith(expected_prefix), f"数据项key前缀不正确: {item_key}"
    
    # 验证具体的组件部分
    assert requests_queue_key.endswith(":queue:requests"), f"请求队列key后缀不正确: {requests_queue_key}"
    assert processing_queue_key.endswith(":queue:processing"), f"处理队列key后缀不正确: {processing_queue_key}"
    assert filter_key.endswith(":filter:fingerprint"), f"过滤器key后缀不正确: {filter_key}"
    assert item_key.endswith(":item:fingerprint"), f"数据项key后缀不正确: {item_key}"
    
    print("\n✅ Redis key结构正确!")
    print("格式为: crawlo:{project}:{spider}:{component}:{sub_component}")
    print("- project: ofweek_standalone")
    print("- spider: ofweek_spider")
    print("- component: queue/filter/item")
    print("- sub_component: requests/processing/failed/fingerprint")


if __name__ == "__main__":
    test_redis_key_structure()