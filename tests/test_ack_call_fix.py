#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试在任务完成时调用ack()方法的解决方案
模拟在请求处理完成后正确调用ack()方法
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
            module_name="test_task_completion",
            timeout=300,  # 设置超时时间为300秒
            cleanup_redis_data=False  # 不自动清理数据
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
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n初始状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 从主队列获取任务（会自动移动到处理队列）
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从主队列取出并移动到处理队列")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n获取任务后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
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
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\nack()调用后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 验证结果
        if main_queue_size == 0 and processing_queue_size == 0 and processing_data_size == 0:
            print("\n✅ 所有队列数据都被正确清理")
            print("   这证明了在任务完成时调用ack()方法是正确的解决方案")
            return True
        else:
            print("\n❌ 队列数据未被正确清理")
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
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
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
            module_name="test_task_failure",
            timeout=300,  # 设置超时时间为300秒
            cleanup_redis_data=False  # 不自动清理数据
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
        
        # 添加测试请求
        test_request = Request(url="https://example.com/test", priority=0)
        success = await queue.put(test_request, priority=0)
        if success:
            print("✅ 测试请求已添加到主队列")
        else:
            print("❌ 测试请求添加失败")
            return False
        
        # 从主队列获取任务（会自动移动到处理队列）
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从主队列取出并移动到处理队列")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n获取任务后状态:")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
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
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\nfail()调用后状态:")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 验证结果
        if processing_queue_size == 0 and processing_data_size == 0:
            print("\n✅ 处理队列数据被正确清理")
            print("   这证明了在任务失败时调用fail()方法（内部调用ack()）是正确的")
            return True
        else:
            print("\n❌ 处理队列数据未被正确清理")
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
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


if __name__ == "__main__":
    print("测试在任务完成时调用ack()方法的解决方案")
    print("=" * 60)
    
    # 测试任务成功完成时调用ack()方法
    result1 = asyncio.run(test_ack_call_on_task_completion())
    
    # 测试任务失败时调用fail()方法（内部调用ack()方法）
    result2 = asyncio.run(test_ack_call_on_task_failure())
    
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"  任务成功完成时调用ack()方法: {'通过' if result1 else '失败'}")
    print(f"  任务失败时调用fail()方法: {'通过' if result2 else '失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过")
        print("\n结论:")
        print("1. 在任务处理完成后，应该正确调用ack()方法来清理处理队列")
        print("2. 在任务处理失败时，应该调用fail()方法，它内部会调用ack()方法")
        print("3. 这样可以避免依赖close()方法中的清理逻辑")
        print("4. 处理队列的生命周期管理应该与主队列保持一致")
    else:
        print("\n💥 部分测试失败")