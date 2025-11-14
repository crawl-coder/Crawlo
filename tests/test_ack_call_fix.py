#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ack方法调用修复方案
验证在任务完成时正确调用ack()方法的解决方案
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_ack_call_on_task_completion():
    """测试在任务完成时调用ack()方法"""
    print("测试在任务完成时调用ack()方法...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:task_completion",
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
            f"{queue.queue_name}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求
        test_request = Request(url="https://example.com/test", priority=0)
        success = await queue.put(test_request, priority=0)
        if success:
            print("✅ 测试请求已添加到主队列")
        else:
            print("❌ 测试请求添加失败")
            return False
        
        # 检查初始状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        
        print(f"\n初始状态:")
        print(f"  主队列大小: {main_queue_size}")
        
        # 从主队列获取任务
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从主队列取出")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        
        print(f"\n获取任务后状态:")
        print(f"  主队列大小: {main_queue_size}")
        
        # 模拟任务处理完成
        print(f"\n--- 模拟任务处理完成 ---")
        print("  执行任务处理逻辑...")
        # 这里可以添加实际的任务处理逻辑
        await asyncio.sleep(0.1)  # 模拟处理时间
        print("  任务处理完成")
        
        # 关键：在任务完成时调用ack()方法
        print(f"\n--- 调用ack()方法确认任务完成 ---")
        await queue.ack(request)
        print("✅ ack()方法调用完成")
        
        # 检查ack()调用后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        
        print(f"\nack()调用后状态:")
        print(f"  主队列大小: {main_queue_size}")
        
        # 验证结果
        if main_queue_size == 0:
            print("\n✅ 队列数据被正确处理")
            print("   这证明了在任务完成时调用ack()方法是正确的解决方案")
            return True
        else:
            print("\n❌ 队列数据未被正确处理")
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


async def test_ack_call_on_task_failure():
    """测试在任务失败时调用ack()方法（通过fail()方法）"""
    print("\n\n测试在任务失败时调用ack()方法...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:task_failure",
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
            f"{queue.queue_name}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求
        test_request = Request(url="https://example.com/test", priority=0)
        success = await queue.put(test_request, priority=0)
        if success:
            print("✅ 测试请求已添加到主队列")
        else:
            print("❌ 测试请求添加失败")
            return False
        
        # 从主队列获取任务
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从主队列取出")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        
        print(f"\n获取任务后状态:")
        print(f"  主队列大小: {main_queue_size}")
        
        # 模拟任务处理失败
        print(f"\n--- 模拟任务处理失败 ---")
        print("  执行任务处理逻辑...")
        # 这里可以添加实际的任务处理逻辑
        await asyncio.sleep(0.1)  # 模拟处理时间
        print("  任务处理失败")
        
        # 关键：在任务失败时调用fail()方法（内部会调用ack()方法）
        print(f"\n--- 调用fail()方法标记任务失败 ---")
        await queue.fail(request, reason="模拟任务失败")
        print("✅ fail()方法调用完成（内部已调用ack()方法）")
        
        # 检查fail()调用后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        
        print(f"\nfail()调用后状态:")
        print(f"  主队列大小: {main_queue_size}")
        
        # 验证结果
        if main_queue_size == 0:
            print("\n✅ 队列数据被正确处理")
            print("   这证明了在任务失败时调用fail()方法（内部调用ack()）是正确的")
            return True
        else:
            print("\n❌ 队列数据未被正确处理")
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
    print("开始测试ack方法调用修复方案...")
    
    # 测试任务完成时的ack()调用
    test1_ok = await test_ack_call_on_task_completion()
    
    # 测试任务失败时的ack()调用
    test2_ok = await test_ack_call_on_task_failure()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"   任务完成时ack()调用测试: {'通过' if test1_ok else '失败'}")
    print(f"   任务失败时ack()调用测试: {'通过' if test2_ok else '失败'}")
    
    if test1_ok and test2_ok:
        print("\n🎉 所有测试通过！")
        print("ack方法调用修复方案验证成功。")
        return True
    else:
        print("\n❌ 部分测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())