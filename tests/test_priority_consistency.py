#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试内存队列和Redis队列优先级行为的一致性
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.request import Request
from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo.queue.redis_priority_queue import RedisPriorityQueue


async def test_priority_consistency():
    """测试内存队列和Redis队列优先级行为的一致性"""
    print("=== 测试内存队列和Redis队列优先级行为一致性 ===")
    
    # 创建内存队列
    memory_queue = SpiderPriorityQueue()
    
    # 创建Redis队列
    redis_queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:consistency:queue"
    )
    
    try:
        await redis_queue.connect()
        
        # 清理之前的测试数据
        await redis_queue._redis.delete(redis_queue.queue_name)
        await redis_queue._redis.delete(f"{redis_queue.queue_name}:data")
        
        # 创建相同优先级的请求
        requests = [
            Request(url="https://priority-100.com", priority=100),   # 低优先级
            Request(url="https://priority-0.com", priority=0),       # 正常优先级
            Request(url="https://priority--100.com", priority=-100)  # 高优先级
        ]
        
        # 向内存队列添加请求
        print("向内存队列添加请求...")
        for req in requests:
            # 内存队列直接使用priority值
            await memory_queue.put((req.priority, req))
            print(f"  内存队列: {req.url} (priority: {req.priority})")
        
        # 向Redis队列添加请求
        print("向Redis队列添加请求...")
        for req in requests:
            # Redis队列需要传入priority参数
            await redis_queue.put(req, priority=req.priority)
            print(f"  Redis队列: {req.url} (priority: {req.priority})")
        
        print(f"  内存队列大小: {memory_queue.qsize()}")
        print(f"  Redis队列大小: {await redis_queue.qsize()}")
        
        # 从内存队列获取请求
        print("从内存队列获取请求（应该按priority从小到大）:")
        memory_results = []
        for i in range(len(requests)):
            item = await memory_queue.get(timeout=1.0)
            if item:
                request = item[1]  # 解包(priority, request)元组
                memory_results.append(request.url)
                print(f"  {i+1}. {request.url} (priority: {request.priority})")
        
        # 从Redis队列获取请求
        print("从Redis队列获取请求（当前行为）:")
        redis_results = []
        for i in range(len(requests)):
            request = await redis_queue.get(timeout=2.0)
            if request:
                redis_results.append(request.url)
                print(f"  {i+1}. {request.url} (priority: {request.priority})")
        
        # 验证一致性
        print("\n一致性检查:")
        print(f"  内存队列出队顺序: {memory_results}")
        print(f"  Redis队列出队顺序: {redis_results}")
        
        # 当前行为不一致，需要修复
        if memory_results != redis_results:
            print("  ❌ 当前行为不一致，需要修复Redis队列的优先级处理逻辑")
            print("  原因: Redis队列使用score = -priority，导致优先级行为与内存队列相反")
            return False
        else:
            print("  ✅ 行为一致")
            return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await redis_queue.close()


async def propose_fix():
    """提出修复方案"""
    print("\n=== 修复方案建议 ===")
    print("问题:")
    print("  Redis队列使用score = -priority，导致优先级行为与内存队列不一致")
    print("  内存队列: priority小的先出队")
    print("  Redis队列: priority大的先出队（因为score小的先出队）")
    
    print("\n解决方案:")
    print("  方案1: 修改Redis队列的score计算方式")
    print("    将 score = -priority 改为 score = priority")
    print("    这样priority小的请求score也小，会先出队，与内存队列行为一致")
    
    print("\n  方案2: 修改内存队列的行为")
    print("    将内存队列入队时改为使用(-priority, request)")
    print("    这样priority大的先出队，与Redis队列行为一致")
    
    print("\n推荐方案:")
    print("  推荐方案1，因为:")
    print("    1. 符合用户对优先级的直观理解（数值小优先级高）")
    print("    2. 与Request类的优先级设计理念一致")
    print("    3. 保持向后兼容性更容易")


async def main():
    print("开始测试队列优先级一致性...")
    
    try:
        # 运行一致性测试
        is_consistent = await test_priority_consistency()
        
        # 提出修复方案
        await propose_fix()
        
        if not is_consistent:
            print("\n⚠️  需要修改原系统以确保内存队列和Redis队列行为一致")
        else:
            print("\n✅ 系统行为一致，无需修改")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())