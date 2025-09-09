#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
去重机制演示脚本
Demonstration script for deduplication mechanisms
"""

import redis
import hashlib
from urllib.parse import urlparse, parse_qs


def demonstrate_request_deduplication():
    """
    演示请求去重机制
    Demonstrate request deduplication mechanism
    """
    print("=== 请求去重机制演示 (Request Deduplication) ===")
    
    # 模拟 Crawlo 框架的请求去重实现
    redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
    redis_key = "crawlo:request_fingerprints"
    
    # 模拟一些请求
    requests = [
        "https://api.example.com/data?page=1",
        "https://api.example.com/data?page=2",
        "https://api.example.com/data?page=1",  # 重复请求
        "https://api.example.com/data?page=3",
        "https://api.example.com/data?page=2",  # 重复请求
    ]
    
    print("发送的请求:")
    for i, url in enumerate(requests, 1):
        # 生成请求指纹（简化版本）
        parsed = urlparse(url)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        page = query_params.get('page', [''])[0]
        fingerprint = f"{path}?page={page}"
        
        # 检查是否已存在
        is_new = redis_client.sadd(redis_key, fingerprint)
        
        if is_new:
            print(f"  {i}. {url} -> 发送请求")
        else:
            print(f"  {i}. {url} -> 请求已存在，跳过")
    
    # 清理
    redis_client.delete(redis_key)
    print()


def demonstrate_item_deduplication():
    """
    演示数据项去重机制
    Demonstrate item deduplication mechanism
    """
    print("=== 数据项去重机制演示 (Item Deduplication) ===")
    
    # 模拟 RedisDeduplicationPipeline 的实现
    redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
    redis_key = "api_data:item_fingerprints"
    
    # 模拟一些数据项
    items = [
        {"id": "1", "name": "产品A", "category": "电子"},
        {"id": "2", "name": "产品B", "category": "服装"},
        {"id": "1", "name": "产品A", "category": "电子"},  # 重复数据项
        {"id": "3", "name": "产品C", "category": "家居"},
        {"id": "2", "name": "产品B", "category": "服装"},  # 重复数据项
    ]
    
    print("处理的数据项:")
    for i, item in enumerate(items, 1):
        # 生成数据项指纹
        key_fields = [
            str(item.get('id', '')),
            item.get('name', ''),
            item.get('category', '')
        ]
        fingerprint_string = '|'.join(key_fields)
        fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]  # 缩短显示
        
        # 检查是否已存在
        is_new = redis_client.sadd(redis_key, fingerprint)
        
        if is_new:
            print(f"  {i}. {item} -> 保存数据")
        else:
            print(f"  {i}. {item} -> 数据已存在，丢弃")
    
    # 清理
    redis_client.delete(redis_key)
    print()


def main():
    """主函数"""
    print("Crawlo 框架去重机制演示")
    print("Crawlo Framework Deduplication Mechanism Demonstration")
    print("=" * 50)
    
    # 演示请求去重
    demonstrate_request_deduplication()
    
    # 演示数据项去重
    demonstrate_item_deduplication()
    
    print("总结:")
    print("Summary:")
    print("1. 请求去重: 防止发送重复的网络请求，节省带宽和服务器资源")
    print("   Request deduplication: Prevents duplicate network requests, saves bandwidth and server resources")
    print("2. 数据项去重: 防止保存重复的数据结果，确保数据唯一性")
    print("   Item deduplication: Prevents duplicate data results, ensures data uniqueness")
    print("3. 两种机制可以同时使用，互不冲突")
    print("   Both mechanisms can be used simultaneously without conflict")


if __name__ == "__main__":
    main()