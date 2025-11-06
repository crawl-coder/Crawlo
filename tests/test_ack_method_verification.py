#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ack方法是否被正确调用
验证处理队列在正常流程中是否被正确清理
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_ack_method():
    """测试ack方法是否被正确调用"""
    print("开始测试ack方法是否被正确调用...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:queue:ack",
            module_name="test_ack",
            timeout=300,  # 设置超时时间为300秒
            cleanup_redis_data=True  # 确保清理数据
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
        
        # 检查主队列状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"主队列大小: {main_queue_size}")
        
        # 从主队列获取任务（会自动移动到处理队列）
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从主队列取出并移动到处理队列")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查队列状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"主队列大小: {main_queue_size}")
        print(f"处理队列大小: {processing_queue_size}")
        print(f"处理队列数据大小: {processing_data_size}")
        
        # 调用ack方法确认任务完成
        print("\n--- 调用ack方法 ---")
        await queue.ack(request)
        print("✅ ack方法调用完成")
        
        # 再次检查队列状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"主队列大小: {main_queue_size}")
        print(f"处理队列大小: {processing_queue_size}")
        print(f"处理队列数据大小: {processing_data_size}")
        
        # 验证处理队列是否被正确清理
        if processing_queue_size == 0 and processing_data_size == 0:
            print("\n✅ 处理队列已被正确清理，ack方法工作正常")
            return True
        else:
            print("\n❌ 处理队列未被正确清理，ack方法可能存在问题")
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
    result = asyncio.run(test_ack_method())
    if result:
        print("\n🎉 测试通过：ack方法被正确调用")
    else:
        print("\n💥 测试失败：ack方法未被正确调用")