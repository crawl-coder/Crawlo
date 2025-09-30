#!/usr/bin/env python3
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue

async def test_empty_queue():
    """测试空队列"""
    print("测试空队列...")
    
    queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:edge:empty"
    )
    await queue.connect()
    
    # 确保队列是空的
    await queue._redis.delete("test:edge:empty")
    await queue._redis.delete("test:edge:empty:data")
    
    print("队列已清空")
    
    # 获取队列大小
    size = await queue.qsize()
    print(f"队列大小: {size}")
    
    # 获取空队列应该返回 None
    print("尝试从空队列获取元素...")
    result = await queue.get(timeout=0.1)
    print(f"结果: {result}")
    
    assert result is None, "空队列应该返回 None"
    print("空队列测试通过")
    
    await queue.close()

if __name__ == "__main__":
    asyncio.run(test_empty_queue())