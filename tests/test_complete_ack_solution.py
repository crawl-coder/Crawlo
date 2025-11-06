#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的ack()方法调用解决方案
展示如何在Crawlo框架中正确调用ack()方法
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def demonstrate_processing_queue_lifecycle():
    """演示处理队列的生命周期管理"""
    print("演示处理队列的生命周期管理...")
    print("=" * 50)
    
    # 创建Redis队列实例
    queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:lifecycle",
        module_name="test_lifecycle",
        timeout=300,
        cleanup_redis_data=False
    )
    
    try:
        await queue.connect()
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 清理旧数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        
        print("1. 初始状态：所有队列为空")
        main_size = await queue._redis.zcard(queue.queue_name)
        processing_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        print(f"   主队列: {main_size}, 处理队列: {processing_size}, 处理数据: {processing_data_size}")
        
        # 添加请求
        request = Request(url="https://example.com/lifecycle", priority=0)
        await queue.put(request, priority=0)
        print("\n2. 添加请求后：请求在主队列中")
        main_size = await queue._redis.zcard(queue.queue_name)
        processing_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        print(f"   主队列: {main_size}, 处理队列: {processing_size}, 处理数据: {processing_data_size}")
        
        # 获取请求（移动到处理队列）
        retrieved_request = await queue.get(timeout=1.0)
        if not retrieved_request:
            print("❌ 无法获取请求")
            return False
        print("\n3. 获取请求后：请求在处理队列中")
        main_size = await queue._redis.zcard(queue.queue_name)
        processing_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        print(f"   主队列: {main_size}, 处理队列: {processing_size}, 处理数据: {processing_data_size}")
        
        # 调用ack()方法（处理完成）
        await queue.ack(retrieved_request)
        print("\n4. 调用ack()后：处理队列被清理")
        main_size = await queue._redis.zcard(queue.queue_name)
        processing_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        print(f"   主队列: {main_size}, 处理队列: {processing_size}, 处理数据: {processing_data_size}")
        
        # 验证结果
        if main_size == 0 and processing_size == 0 and processing_data_size == 0:
            print("\n✅ 处理队列的生命周期管理与主队列保持一致")
            print("   这证明了正确的解决方案：")
            print("   1. 请求从主队列原子性移除")
            print("   2. 请求在处理队列中暂存")
            print("   3. 处理完成后通过ack()方法从处理队列移除")
            return True
        else:
            print("\n❌ 处理队列生命周期管理不正确")
            return False
            
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理数据
        if queue._redis:
            await queue._redis.delete(
                queue.queue_name,
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


async def compare_with_main_queue():
    """与主队列处理逻辑进行对比"""
    print("\n\n与主队列处理逻辑进行对比...")
    print("=" * 50)
    
    # 创建Redis队列实例
    queue = RedisPriorityQueue(
        redis_url="redis://127.0.0.1:6379/15",
        queue_name="test:queue:comparison",
        module_name="test_comparison",
        timeout=300,
        cleanup_redis_data=False
    )
    
    try:
        await queue.connect()
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 清理旧数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        
        print("主队列处理逻辑:")
        print("1. 请求添加到主队列 -> queue:requests 和 queue:requests:data")
        print("2. 请求被zpopmin原子性取出 -> 主队列和数据哈希同时被清理")
        print("3. 爬虫结束后，主队列自然为空")
        
        print("\n处理队列处理逻辑:")
        print("1. 请求从主队列移动到处理队列 -> queue:processing 和 queue:processing:data")
        print("2. 请求在处理过程中一直存在于处理队列")
        print("3. 请求处理完成后应该调用ack()方法 -> 处理队列和数据哈希被清理")
        print("4. 爬虫结束后，处理队列应该为空（如果正确调用了ack()方法）")
        
        # 添加多个请求进行演示
        requests = [
            Request(url="https://example.com/test1", priority=0),
            Request(url="https://example.com/test2", priority=0),
        ]
        
        print(f"\n添加 {len(requests)} 个请求到主队列...")
        for req in requests:
            await queue.put(req, priority=0)
        
        print("获取并处理所有请求...")
        processed_requests = []
        while True:
            req = await queue.get(timeout=1.0)
            if not req:
                break
            processed_requests.append(req)
        
        print(f"处理了 {len(processed_requests)} 个请求")
        
        # 对每个处理完成的请求调用ack()方法
        print("对每个处理完成的请求调用ack()方法...")
        for req in processed_requests:
            await queue.ack(req)
        
        # 检查最终状态
        main_size = await queue._redis.zcard(queue.queue_name)
        processing_size = await queue._redis.zcard(queue.processing_queue)
        processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
        
        print(f"\n最终状态:")
        print(f"  主队列大小: {main_size}")
        print(f"  处理队列大小: {processing_size}")
        print(f"  处理队列数据大小: {processing_data_size}")
        
        if main_size == 0 and processing_size == 0 and processing_data_size == 0:
            print("\n✅ 处理队列的生命周期与主队列保持一致")
            return True
        else:
            print("\n❌ 处理队列生命周期与主队列不一致")
            return False
            
    except Exception as e:
        print(f"❌ 对比失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理数据
        if queue._redis:
            await queue._redis.delete(
                queue.queue_name,
                f"{queue.queue_name}:data",
                queue.processing_queue,
                f"{queue.processing_queue}:data"
            )


if __name__ == "__main__":
    print("完整的ack()方法调用解决方案")
    print("=" * 60)
    
    # 演示处理队列生命周期
    result1 = asyncio.run(demonstrate_processing_queue_lifecycle())
    
    # 与主队列处理逻辑对比
    result2 = asyncio.run(compare_with_main_queue())
    
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"  生命周期演示: {'通过' if result1 else '失败'}")
    print(f"  逻辑对比: {'通过' if result2 else '失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过")
        print("\n结论和建议:")
        print("1. 在Crawlo框架中，应该在请求处理成功完成后立即调用ack()方法")
        print("2. ack()方法的调用应该在任务完成的回调函数中进行")
        print("3. 处理队列的生命周期应该与主队列保持一致")
        print("4. 不应该依赖close()方法中的清理逻辑来清理处理队列")
        print("5. 这样可以确保在爬虫正常结束时，处理队列为空")
        print("\n实现建议:")
        print("- 在Engine类的_crawl方法中，在请求处理成功完成后调用ack()方法")
        print("- 在Downloader类中，在请求下载和处理完成后调用ack()方法")
        print("- 在TaskManager的任务完成回调中调用ack()方法")
    else:
        print("\n💥 部分测试失败")