#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试队列中score的含义
验证主队列和处理队列中score的不同用途
"""
import asyncio
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_queue_scores():
    """测试队列中score的含义"""
    print("开始测试队列中score的含义...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:scores",
            module_name="test_scores",
            timeout=300  # 设置超时时间为300秒
        )
        
        # 连接Redis
        await queue.connect()
        print("✅ Redis连接成功")
        
        # 确保Redis连接存在
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 清理可能存在的旧数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求，使用不同的优先级
        test_requests = [
            Request(url="https://example.com/high_priority", priority=-100),  # 高优先级
            Request(url="https://example.com/normal_priority", priority=0),   # 正常优先级
            Request(url="https://example.com/low_priority", priority=100)     # 低优先级
        ]
        
        print("\n--- 添加测试请求（不同优先级） ---")
        current_time = time.time()
        print(f"当前时间戳: {current_time}")
        
        for i, request in enumerate(test_requests):
            success = await queue.put(request, priority=request.priority)
            if success:
                print(f"✅ 请求{i+1}已添加到主队列: {request.url} (priority: {request.priority})")
            else:
                print(f"❌ 请求{i+1}添加失败")
                return False
        
        # 查看主队列中的score
        print("\n--- 主队列中的score ---")
        main_queue_items = await queue._redis.zrange(queue.queue_name, 0, -1, withscores=True)
        for item, score in main_queue_items:
            print(f"  Key: {item.decode('utf-8') if isinstance(item, bytes) else item}, Score: {score}")
        
        # 从主队列获取任务（会自动移动到处理队列）
        print("\n--- 从主队列获取任务 ---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 查看处理队列中的score
        print("\n--- 处理队列中的score ---")
        processing_queue_items = await queue._redis.zrange(queue.processing_queue, 0, -1, withscores=True)
        for item, score in processing_queue_items:
            item_str = item.decode('utf-8') if isinstance(item, bytes) else item
            print(f"  Key: {item_str}, Score: {score}")
            # 计算超时时间
            timeout_time = score
            current_time = time.time()
            time_left = timeout_time - current_time
            print(f"    超时时间: {timeout_time}, 当前时间: {current_time}, 剩余时间: {time_left:.2f}秒")
        
        print("\n✅ 队列score测试完成！")
        print("\n总结:")
        print("1. 主队列中的score = 请求的priority值")
        print("2. 处理队列中的score = time.time() + timeout（超时时间戳）")
        print("3. 这种设计使得:")
        print("   - 主队列按优先级排序（score小的先出队）")
        print("   - 处理队列可以检测任务是否超时（通过比较当前时间和score）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        if queue and queue._redis:
            await queue._redis.delete(
                queue.queue_name,
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


if __name__ == "__main__":
    asyncio.run(test_queue_scores())