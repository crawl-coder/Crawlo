#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试处理队列在爬虫正常结束时的清理行为
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_simple_cleanup_behavior():
    """简单测试清理行为"""
    print("开始简单测试处理队列清理行为...")
    print("=" * 50)
    
    # 测试1: cleanup_redis_data=False (保留数据)
    print("\n--- 测试1: cleanup_redis_data=False (保留数据) ---")
    queue1 = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:keep",
        module_name="test_keep",
        timeout=300,
        cleanup_redis_data=False  # 保留数据
    )
    
    await queue1.connect()
    if not queue1._redis:
        print("❌ Redis连接失败")
        return False
    
    # 清理旧数据
    await queue1._redis.delete(
        queue1.queue_name,
        f"{queue1.queue_name}:data",
        queue1.processing_queue,
        f"{queue1.processing_queue}:data"
    )
    
    # 添加并处理一个请求
    request = Request(url="https://example.com/test", priority=0)
    await queue1.put(request, priority=0)
    processed_request = await queue1.get(timeout=1.0)
    
    if processed_request:
        print("✅ 请求已移动到处理队列")
        # 不调用ack，模拟任务未完成
        await queue1.close()
        print("✅ close方法调用完成 (应该保留处理队列数据)")
    else:
        print("❌ 无法获取请求")
        return False
    
    # 测试2: cleanup_redis_data=True (自动清理)
    print("\n--- 测试2: cleanup_redis_data=True (自动清理) ---")
    queue2 = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:clean",
        module_name="test_clean",
        timeout=300,
        cleanup_redis_data=True  # 自动清理
    )
    
    await queue2.connect()
    if not queue2._redis:
        print("❌ Redis连接失败")
        return False
    
    # 清理旧数据
    await queue2._redis.delete(
        queue2.queue_name,
        f"{queue2.queue_name}:data",
        queue2.processing_queue,
        f"{queue2.processing_queue}:data"
    )
    
    # 添加并处理一个请求
    request = Request(url="https://example.com/test", priority=0)
    await queue2.put(request, priority=0)
    processed_request = await queue2.get(timeout=1.0)
    
    if processed_request:
        print("✅ 请求已移动到处理队列")
        # 不调用ack，模拟任务未完成
        await queue2.close()
        print("✅ close方法调用完成 (应该清理处理队列数据)")
    else:
        print("❌ 无法获取请求")
        return False
    
    print("\n✅ 简单测试完成")
    return True


if __name__ == "__main__":
    asyncio.run(test_simple_cleanup_behavior())