#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的ack方法
验证处理队列能被正确清理
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_ack_method_fix():
    """测试修复后的ack方法"""
    print("开始测试修复后的ack方法...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:ack:fix",
            module_name="test_ack_fix"
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
        test_requests = [
            Request(url="https://example.com/test1"),
            Request(url="https://example.com/test2"),
            Request(url="https://example.com/test3")
        ]
        
        print("\n--- 添加测试请求 ---")
        for i, request in enumerate(test_requests):
            success = await queue.put(request, priority=0)
            if success:
                print(f"✅ 请求{i+1}已添加到队列: {request.url}")
            else:
                print(f"❌ 请求{i+1}添加失败")
                return False
        
        # 验证主队列大小
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"✅ 主队列大小: {main_queue_size}")
        
        # 从主队列获取任务（会自动移动到处理队列）
        print("\n--- 模拟任务处理 ---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 验证处理队列不为空
        if queue._redis:
            processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
            print(f"✅ 处理队列大小: {processing_queue_size}")
            print(f"✅ 处理队列数据大小: {processing_data_size}")
            
            if processing_queue_size != len(test_requests) or processing_data_size != len(test_requests):
                print(f"❌ 处理队列大小不正确，期望: {len(test_requests)}, 实际: {processing_queue_size}")
                return False
        
        # 现在调用ack方法确认任务完成
        print("\n--- 调用ack方法确认任务完成 ---")
        for i, request in enumerate(processed_requests):
            await queue.ack(request)
            print(f"✅ 任务{i+1}已确认完成: {request.url}")
        
        # 验证处理队列是否为空
        final_processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        final_processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        print(f"✅ ack调用后处理队列大小: {final_processing_queue_size}")
        print(f"✅ ack调用后处理队列数据大小: {final_processing_data_size}")
        
        if final_processing_queue_size == 0 and final_processing_data_size == 0:
            print("✅ 处理队列已正确清理")
        else:
            print(f"❌ 处理队列清理失败，队列大小: {final_processing_queue_size}, 数据大小: {final_processing_data_size}")
            return False
        
        print("\n✅ 修复后的ack方法测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
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
    asyncio.run(test_ack_method_fix())