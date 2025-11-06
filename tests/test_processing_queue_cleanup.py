#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试处理队列在爬虫正常结束时的清理行为
模拟实际爬虫场景，验证CLEANUP_REDIS_DATA参数的行为
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_processing_queue_cleanup():
    """测试处理队列在爬虫正常结束时的清理行为"""
    print("开始测试处理队列在爬虫正常结束时的清理行为...")
    print("=" * 60)
    
    queue = None
    redis_conn = None
    try:
        # 创建Redis队列实例，设置cleanup_redis_data=False以保留数据
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:cleanup",
            module_name="test_cleanup",
            timeout=300,  # 设置超时时间为300秒
            cleanup_redis_data=False  # 不自动清理数据以支持断点续爬
        )
        
        # 连接Redis
        await queue.connect()
        print("✅ Redis连接成功")
        
        # 保存Redis连接引用用于后续检查
        redis_conn = queue._redis
        
        # 确保Redis连接存在
        if not redis_conn:
            print("❌ Redis连接失败")
            return False
        
        # 清理可能存在的旧数据
        await redis_conn.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加多个测试请求
        test_requests = [
            Request(url="https://example.com/test1", priority=0),
            Request(url="https://example.com/test2", priority=0),
            Request(url="https://example.com/test3", priority=0),
        ]
        
        print(f"\n--- 添加 {len(test_requests)} 个测试请求 ---")
        for i, request in enumerate(test_requests):
            success = await queue.put(request, priority=0)
            if success:
                print(f"✅ 请求{i+1}已添加到主队列: {request.url}")
            else:
                print(f"❌ 请求{i+1}添加失败")
                return False
        
        # 检查初始状态
        main_queue_size = await redis_conn.zcard(queue.queue_name)
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n初始状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 从主队列获取所有任务（会自动移动到处理队列）
        print(f"\n--- 从主队列获取任务 ---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 检查获取任务后的状态
        main_queue_size = await redis_conn.zcard(queue.queue_name)
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n获取任务后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 部分调用ack方法确认任务完成（模拟部分任务完成）
        print(f"\n--- 调用ack方法确认部分任务完成 ---")
        for i, request in enumerate(processed_requests[:-1]):  # 确认前两个任务完成
            await queue.ack(request)
            print(f"✅ 任务{i+1}已完成并从处理队列移除: {request.url}")
        
        # 检查部分ack后的状态
        main_queue_size = await redis_conn.zcard(queue.queue_name)
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n部分ack后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 模拟调用close方法（模拟爬虫正常结束）
        print(f"\n--- 调用close方法（模拟爬虫正常结束） ---")
        # 由于cleanup_redis_data=False，close方法应该保留处理队列中的数据
        await queue.close()
        print("✅ close方法调用完成")
        
        # 重新连接Redis以检查状态
        await queue.connect()
        redis_conn = queue._redis
        
        # 检查close后的状态
        main_queue_size = await redis_conn.zcard(queue.queue_name)
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\nclose后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 验证结果
        if main_queue_size == 0 and processing_queue_size > 0 and processing_data_size > 0:
            print("\n✅ 处理队列数据被正确保留，支持断点续爬")
            print(f"   未完成的任务数量: {processing_queue_size}")
            return True
        elif main_queue_size == 0 and processing_queue_size == 0 and processing_data_size == 0:
            print("\n❌ 处理队列数据被意外清理")
            return False
        else:
            print(f"\n❓ 意外状态: 主队列={main_queue_size}, 处理队列={processing_queue_size}, 数据={processing_data_size}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        if redis_conn:
            await redis_conn.delete(
                queue.queue_name,
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


async def test_processing_queue_cleanup_with_auto_cleanup():
    """测试处理队列在自动清理模式下的行为"""
    print("\n\n开始测试处理队列在自动清理模式下的行为...")
    print("=" * 60)
    
    queue = None
    redis_conn = None
    try:
        # 创建Redis队列实例，设置cleanup_redis_data=True以自动清理数据
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:auto_cleanup",
            module_name="test_auto_cleanup",
            timeout=300,  # 设置超时时间为300秒
            cleanup_redis_data=True  # 自动清理数据
        )
        
        # 连接Redis
        await queue.connect()
        print("✅ Redis连接成功")
        
        # 保存Redis连接引用用于后续检查
        redis_conn = queue._redis
        
        # 确保Redis连接存在
        if not redis_conn:
            print("❌ Redis连接失败")
            return False
        
        # 清理可能存在的旧数据
        await redis_conn.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求
        test_requests = [
            Request(url="https://example.com/test1", priority=0),
            Request(url="https://example.com/test2", priority=0),
        ]
        
        print(f"\n--- 添加 {len(test_requests)} 个测试请求 ---")
        for i, request in enumerate(test_requests):
            success = await queue.put(request, priority=0)
            if success:
                print(f"✅ 请求{i+1}已添加到主队列: {request.url}")
            else:
                print(f"❌ 请求{i+1}添加失败")
                return False
        
        # 从主队列获取所有任务
        print(f"\n--- 从主队列获取任务 ---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 部分调用ack方法确认任务完成
        print(f"\n--- 调用ack方法确认部分任务完成 ---")
        for i, request in enumerate(processed_requests[:-1]):  # 确认第一个任务完成
            await queue.ack(request)
            print(f"✅ 任务{i+1}已完成并从处理队列移除: {request.url}")
        
        # 检查状态
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\nack后状态:")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 模拟调用close方法（模拟爬虫正常结束）
        print(f"\n--- 调用close方法（模拟爬虫正常结束） ---")
        # 由于cleanup_redis_data=True，close方法应该清理处理队列中的数据
        await queue.close()
        print("✅ close方法调用完成")
        
        # 重新连接Redis以检查状态
        await queue.connect()
        redis_conn = queue._redis
        
        # 检查close后的状态
        main_queue_size = await redis_conn.zcard(queue.queue_name)
        processing_queue_size = await redis_conn.zcard(queue.processing_queue)
        processing_data_size = await redis_conn.hlen(f"{queue.processing_queue}:data")
        
        print(f"\nclose后状态:")
        print(f"  主队列大小: {main_queue_size}")
        print(f"  处理队列大小: {processing_queue_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        # 验证结果
        if main_queue_size == 0 and processing_queue_size == 0 and processing_data_size == 0:
            print("\n✅ 处理队列数据被正确清理")
            return True
        else:
            print(f"\n❌ 处理队列数据未被正确清理: 主队列={main_queue_size}, 处理队列={processing_queue_size}, 数据={processing_data_size}")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        if redis_conn:
            await redis_conn.delete(
                queue.queue_name,
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


if __name__ == "__main__":
    print("测试处理队列清理行为")
    print("=" * 60)
    
    # 测试保留数据模式
    result1 = asyncio.run(test_processing_queue_cleanup())
    
    # 测试自动清理模式
    result2 = asyncio.run(test_processing_queue_cleanup_with_auto_cleanup())
    
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"  保留数据模式测试: {'通过' if result1 else '失败'}")
    print(f"  自动清理模式测试: {'通过' if result2 else '失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过")
    else:
        print("\n💥 部分测试失败")