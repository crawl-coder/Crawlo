#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的内存队列和Redis队列优先级行为一致性
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.request import Request
from crawlo.queue.memory_queue import SpiderPriorityQueue
from crawlo.queue.redis_priority_queue import RedisPriorityQueue


async def test_priority_consistency_after_fix():
    """测试修复后内存队列和Redis队列优先级行为的一致性"""
    print("=== 测试修复后内存队列和Redis队列优先级行为一致性 ===")
    
    # 创建内存队列
    memory_queue = SpiderPriorityQueue()
    
    # 创建Redis队列
    redis_queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:consistency:fixed:queue"
    )
    
    try:
        await redis_queue.connect()
        
        # 清理之前的测试数据
        await redis_queue._redis.delete(redis_queue.queue_name)
        await redis_queue._redis.delete(f"{redis_queue.queue_name}:data")
        
        # 创建相同优先级的请求（注意Request构造函数会将priority取反存储）
        requests = [
            Request(url="https://priority-100.com", priority=100),   # 实际存储为-100（高优先级）
            Request(url="https://priority-0.com", priority=0),       # 实际存储为0（正常优先级）
            Request(url="https://priority--100.com", priority=-100)  # 实际存储为100（低优先级）
        ]
        
        # 向内存队列添加请求
        print("向内存队列添加请求...")
        for req in requests:
            # 内存队列直接使用priority值（实际存储的值）
            await memory_queue.put((req.priority, req))
            print(f"  内存队列: {req.url} (stored priority: {req.priority})")
        
        # 向Redis队列添加请求
        print("向Redis队列添加请求...")
        for req in requests:
            # Redis队列需要传入priority参数（实际存储的值）
            await redis_queue.put(req, priority=req.priority)
            print(f"  Redis队列: {req.url} (stored priority: {req.priority})")
        
        print(f"  内存队列大小: {memory_queue.qsize()}")
        print(f"  Redis队列大小: {await redis_queue.qsize()}")
        
        # 从内存队列获取请求
        print("从内存队列获取请求（应该按priority从小到大，即-100, 0, 100）:")
        memory_results = []
        memory_priorities = []
        for i in range(len(requests)):
            item = await memory_queue.get(timeout=1.0)
            if item:
                request = item[1]  # 解包(priority, request)元组
                memory_results.append(request.url)
                memory_priorities.append(request.priority)
                print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
        
        # 从Redis队列获取请求
        print("从Redis队列获取请求（修复后应该与内存队列一致）:")
        redis_results = []
        redis_priorities = []
        for i in range(len(requests)):
            request = await redis_queue.get(timeout=2.0)
            if request:
                redis_results.append(request.url)
                redis_priorities.append(request.priority)
                print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
        
        # 验证一致性
        print("\n一致性检查:")
        print(f"  内存队列出队顺序: {memory_results}")
        print(f"  内存队列优先级顺序: {memory_priorities}")
        print(f"  Redis队列出队顺序: {redis_results}")
        print(f"  Redis队列优先级顺序: {redis_priorities}")
        
        # 验证出队顺序一致性
        if memory_results == redis_results:
            print("  ✅ 出队顺序一致")
        else:
            print("  ❌ 出队顺序不一致")
            return False
        
        # 验证优先级顺序一致性（都应该按priority从小到大）
        expected_priority_order = [-100, 0, 100]  # 高优先级到低优先级
        if memory_priorities == expected_priority_order and redis_priorities == expected_priority_order:
            print("  ✅ 优先级顺序一致（按priority从小到大）")
        else:
            print(f"  ❌ 优先级顺序不一致，期望: {expected_priority_order}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await redis_queue.close()


async def test_real_world_scenario():
    """测试真实场景下的优先级行为"""
    print("\n=== 测试真实场景下的优先级行为 ===")
    
    # 创建内存队列
    memory_queue = SpiderPriorityQueue()
    
    # 创建Redis队列
    redis_queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:realworld:queue"
    )
    
    try:
        await redis_queue.connect()
        
        # 清理之前的测试数据
        await redis_queue._redis.delete(redis_queue.queue_name)
        await redis_queue._redis.delete(f"{redis_queue.queue_name}:data")
        
        # 创建真实场景的请求
        # 注意：Request构造函数会将传入的priority值取反存储
        # 所以我们要传入负值来获得正值的存储priority
        requests = [
            Request(url="https://urgent-task.com", priority=-200),      # 存储为200
            Request(url="https://high-priority-task.com", priority=-100), # 存储为100
            Request(url="https://normal-task.com", priority=0),         # 存储为0
            Request(url="https://low-priority-task.com", priority=100),  # 存储为-100
            Request(url="https://background-task.com", priority=200)    # 存储为-200
        ]
        
        # 向两个队列添加相同的请求
        print("向队列添加真实场景请求...")
        for req in requests:
            # 内存队列
            await memory_queue.put((req.priority, req))
            # Redis队列
            await redis_queue.put(req, priority=req.priority)
            print(f"  {req.url} (stored priority: {req.priority})")
        
        # 从两个队列获取请求并比较顺序
        print("\n从内存队列获取请求（应该按stored priority从小到大）:")
        memory_results = []
        memory_priorities = []
        for i in range(len(requests)):
            item = await memory_queue.get(timeout=1.0)
            if item:
                request = item[1]
                memory_results.append(request.url)
                memory_priorities.append(request.priority)
                print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
        
        print("\n从Redis队列获取请求（应该与内存队列一致）:")
        redis_results = []
        redis_priorities = []
        for i in range(len(requests)):
            request = await redis_queue.get(timeout=2.0)
            if request:
                redis_results.append(request.url)
                redis_priorities.append(request.priority)
                print(f"  {i+1}. {request.url} (stored priority: {request.priority})")
        
        # 验证一致性
        print("\n真实场景一致性检查:")
        print(f"  内存队列出队顺序: {memory_results}")
        print(f"  内存队列优先级顺序: {memory_priorities}")
        print(f"  Redis队列出队顺序: {redis_results}")
        print(f"  Redis队列优先级顺序: {redis_priorities}")
        
        # 应该按stored priority从小到大出队（-200, -100, 0, 100, 200）
        expected_order = [
            "https://background-task.com",   # stored priority: -200
            "https://low-priority-task.com", # stored priority: -100
            "https://normal-task.com",       # stored priority: 0
            "https://high-priority-task.com", # stored priority: 100
            "https://urgent-task.com"        # stored priority: 200
        ]
        
        expected_priority_order = [-200, -100, 0, 100, 200]
        
        if (memory_results == expected_order and redis_results == expected_order and
            memory_priorities == expected_priority_order and redis_priorities == expected_priority_order):
            print("  ✅ 真实场景优先级行为一致且正确")
            print("  出队顺序: 高优先级 -> 低优先级")
            return True
        else:
            print(f"  ❌ 真实场景优先级行为不一致或不正确")
            print(f"  期望出队顺序: {expected_order}")
            print(f"  期望优先级顺序: {expected_priority_order}")
            return False
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await redis_queue.close()


async def main():
    print("开始测试修复后的队列优先级一致性...")
    
    try:
        # 测试基础一致性
        basic_consistent = await test_priority_consistency_after_fix()
        
        # 测试真实场景
        realworld_consistent = await test_real_world_scenario()
        
        if basic_consistent and realworld_consistent:
            print("\n🎉 修复成功！内存队列和Redis队列优先级行为现在一致")
            print("\n总结:")
            print("1. 修复了Redis队列的score计算方式，从score = -priority改为score = priority")
            print("2. 现在内存队列和Redis队列都遵循'priority数值小优先级高'的原则")
            print("3. 与Request类的优先级设计理念保持一致")
            print("4. 确保了单机模式和分布式模式行为的一致性")
            print("\n注意事项:")
            print("  Request对象构造时会将传入的priority值取反存储")
            print("  所以Request(url='example.com', priority=-200)实际存储的priority为200")
        else:
            print("\n❌ 修复不完全成功，请检查实现")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())