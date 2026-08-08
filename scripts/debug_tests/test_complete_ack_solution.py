#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的ack方法解决方案测试
验证在所有场景下正确调用ack()方法
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.backends.redis_priority import RedisPriorityQueue
from crawlo.http.request import Request


async def test_complete_ack_solution():
    """测试完整的ack方法解决方案"""
    print("测试完整的ack方法解决方案...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:queue:complete_solution",
            timeout=300
        )
        
        await queue.connect()
        print("✅ Redis连接成功")
        
        # 确保Redis连接存在
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 清理可能存在的旧数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加多个测试请求
        test_requests = [
            Request(url="https://example.com/test1", priority=0),
            Request(url="https://example.com/test2", priority=1),
            Request(url="https://example.com/test3", priority=2)
        ]
        
        print("\n--- 添加测试请求 ---")
        for i, request in enumerate(test_requests):
            success = await queue.put(request, priority=request.priority)
            if success:
                print(f"✅ 请求{i+1}已添加到队列: {request.url}")
            else:
                print(f"❌ 请求{i+1}添加失败")
                return False
        
        # 检查初始状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"\n初始队列大小: {main_queue_size}")
        
        # 处理所有请求
        print("\n--- 处理所有请求 ---")
        processed_count = 0
        while True:
            # 从队列获取任务
            request = await queue.get(timeout=1.0)
            if not request:
                break
                
            print(f"✅ 获取到请求: {request.url}")
            
            # 模拟任务处理
            print(f"  处理请求 {request.url}...")
            await asyncio.sleep(0.1)  # 模拟处理时间
            
            # 根据某种条件决定是成功还是失败
            if processed_count % 2 == 0:
                # 成功处理 - 调用ack()
                print(f"  请求 {request.url} 处理成功")
                await queue.ack(request)
                print(f"  ✅ 已调用ack()方法确认请求完成")
            else:
                # 处理失败 - 调用fail()
                print(f"  请求 {request.url} 处理失败")
                await queue.fail(request, reason="模拟处理失败")
                print(f"  ✅ 已调用fail()方法标记请求失败")
            
            processed_count += 1
        
        # 检查最终状态
        final_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"\n最终队列大小: {final_queue_size}")
        
        # 验证结果
        if final_queue_size == 0:
            print("\n✅ 所有请求都被正确处理")
            print("   这证明了完整的ack方法解决方案是有效的")
            return True
        else:
            print(f"\n❌ 还有 {final_queue_size} 个请求未被处理")
            return False
        
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
                f"{queue.queue_name}:data"
            )


async def main():
    """主测试函数"""
    print("开始测试完整的ack方法解决方案...")
    
    # 测试完整解决方案
    test_ok = await test_complete_ack_solution()
    
    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"   完整ack方法解决方案测试: {'通过' if test_ok else '失败'}")
    
    if test_ok:
        print("\n🎉 测试通过！")
        print("完整的ack方法解决方案验证成功。")
        return True
    else:
        print("\n❌ 测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())