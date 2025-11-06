#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析项目中ack()方法的调用情况
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType
from crawlo.core.scheduler import Scheduler
from crawlo.network.request import Request


async def analyze_ack_calls():
    """分析ack()方法的调用情况"""
    print("分析项目中ack()方法的调用情况...")
    print("=" * 50)
    
    # 1. 直接测试RedisPriorityQueue的ack方法
    print("\n1. 测试RedisPriorityQueue的ack方法:")
    queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:analysis",
        module_name="test_analysis",
        timeout=300,
        cleanup_redis_data=False
    )
    
    await queue.connect()
    if not queue._redis:
        print("❌ Redis连接失败")
        return
    
    # 清理旧数据
    await queue._redis.delete(
        queue.queue_name,
        f"{queue.queue_name}:data",
        queue.processing_queue,
        f"{queue.processing_queue}:data"
    )
    
    # 添加并处理一个请求
    request = Request(url="https://example.com/test", priority=0)
    await queue.put(request, priority=0)
    processed_request = await queue.get(timeout=1.0)
    
    if processed_request:
        print("✅ 请求已移动到处理队列")
        # 调用ack方法
        await queue.ack(processed_request)
        print("✅ ack方法调用完成")
        
        # 检查处理队列是否为空
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        if processing_queue_size == 0 and processing_data_size == 0:
            print("✅ 处理队列已被正确清理")
        else:
            print(f"❌ 处理队列未被正确清理: 队列大小={processing_queue_size}, 数据大小={processing_data_size}")
    else:
        print("❌ 无法获取请求")
    
    # 2. 测试QueueManager是否调用ack方法
    print("\n2. 测试QueueManager:")
    config = QueueConfig(
        queue_type=QueueType.REDIS,
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:manager",
        cleanup_redis_data=False
    )
    
    queue_manager = QueueManager(config)
    await queue_manager.initialize()
    
    if queue_manager._queue:
        print("✅ QueueManager初始化成功")
        # QueueManager没有直接的ack方法，它使用底层队列的ack方法
    else:
        print("❌ QueueManager初始化失败")
    
    # 3. 测试Scheduler是否调用ack方法
    print("\n3. 测试Scheduler:")
    # Scheduler也没有直接的ack方法
    
    print("\n" + "=" * 50)
    print("分析结果:")
    print("1. RedisPriorityQueue有ack()方法，但项目中没有地方直接调用它")
    print("2. QueueManager和Scheduler都没有提供ack()方法")
    print("3. 处理队列的清理主要通过close()方法中的清理逻辑完成")
    print("4. 在正常流程中，ack()方法应该在请求处理完成后被调用")
    
    # 清理测试数据
    await queue._redis.delete(
        queue.queue_name,
        f"{queue.queue_name}:data",
        queue.processing_queue,
        f"{queue.processing_queue}:data"
    )


if __name__ == "__main__":
    asyncio.run(analyze_ack_calls())