#!/usr/bin/env python3
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request

async def test_priority_behavior():
    print("=== 测试优先级行为 ===")
    
    # 创建内存队列
    memory_queue = SpiderPriorityQueue()
    
    # 创建Redis队列
    redis_queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:priority:behavior"
    )
    await redis_queue.connect()
    
    # 清理之前的测试数据
    await redis_queue._redis.delete(redis_queue.queue_name)
    await redis_queue._redis.delete(f"{redis_queue.queue_name}:data")
    
    # 创建不同优先级的请求
    # 注意：Request构造函数会将传入的priority值取反存储
    urgent_request = Request(url="https://urgent.com", priority=-200)    # 实际存储为200
    high_request = Request(url="https://high.com", priority=-100)         # 实际存储为100
    normal_request = Request(url="https://normal.com", priority=0)        # 实际存储为0
    low_request = Request(url="https://low.com", priority=100)            # 实际存储为-100
    background_request = Request(url="https://background.com", priority=200) # 实际存储为-200
    
    print("请求的实际存储优先级:")
    print(f"  Urgent: {urgent_request.priority}")
    print(f"  High: {high_request.priority}")
    print(f"  Normal: {normal_request.priority}")
    print(f"  Low: {low_request.priority}")
    print(f"  Background: {background_request.priority}")
    
    # 向内存队列添加请求
    await memory_queue.put((urgent_request.priority, urgent_request))
    await memory_queue.put((high_request.priority, high_request))
    await memory_queue.put((normal_request.priority, normal_request))
    await memory_queue.put((low_request.priority, low_request))
    await memory_queue.put((background_request.priority, background_request))
    
    # 向Redis队列添加请求
    await redis_queue.put(urgent_request, priority=urgent_request.priority)
    await redis_queue.put(high_request, priority=high_request.priority)
    await redis_queue.put(normal_request, priority=normal_request.priority)
    await redis_queue.put(low_request, priority=low_request.priority)
    await redis_queue.put(background_request, priority=background_request.priority)
    
    print("\n内存队列出队顺序（应该按priority从小到大）:")
    for i in range(5):
        item = await memory_queue.get(timeout=1.0)
        if item:
            request = item[1]
            print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
    
    print("\nRedis队列出队顺序（应该按priority从小到大）:")
    for i in range(5):
        request = await redis_queue.get(timeout=2.0)
        if request:
            print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
    
    await redis_queue.close()
    print("\n✅ 测试完成：priority数值小优先级高")

if __name__ == "__main__":
    asyncio.run(test_priority_behavior())