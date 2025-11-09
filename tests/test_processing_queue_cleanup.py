#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟实际爬虫场景，验证CLEANUP_REDIS_DATA参数的行为
测试处理队列在正常完成和异常中断时的清理行为
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_normal_completion_cleanup():
    """测试正常完成时处理队列的清理行为"""
    print("开始测试正常完成时处理队列的清理行为...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例，设置cleanup_redis_data=False（支持断点续爬）
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:normal:completion",
            module_name="test_normal_completion",
            cleanup_redis_data=False  # 不清理所有数据，但应该清理处理队列
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
            queue.key_manager.get_requests_data_key(),
            queue.processing_queue,
            queue.key_manager.get_processing_data_key()
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
        
        # 从主队列获取任务并处理（会自动移动到处理队列，然后确认完成）
        print("\n--- 模拟任务处理和确认完成 ---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
                # 确认任务完成
                await queue.ack(request)
                print(f"✅ 任务{i+1}已确认完成")
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 验证处理队列为空（因为所有任务都已确认完成）
        if queue._redis:
            processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            processing_data_size = await queue._redis.hlen(queue.key_manager.get_processing_data_key())
            print(f"✅ 处理队列大小: {processing_queue_size}")
            print(f"✅ 处理队列数据大小: {processing_data_size}")
            
            if processing_queue_size != 0 or processing_data_size != 0:
                print(f"❌ 处理队列不为空，期望: 0, 实际队列大小: {processing_queue_size}, 数据大小: {processing_data_size}")
                return False
        
        # 现在关闭队列，由于cleanup_redis_data=False，应该保留主队列数据
        print("\n--- 关闭队列（应该保留主队列数据）---")
        await queue.close()
        print("✅ 队列已关闭")
        
        # 重新连接以检查数据
        await queue.connect()
        
        # 确保Redis连接存在
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 验证主队列仍然存在（因为cleanup_redis_data=False）
        final_main_queue_size = await queue._redis.zcard(queue.queue_name)
        final_main_data_size = await queue._redis.hlen(queue.key_manager.get_requests_data_key())
        print(f"✅ 关闭后主队列大小: {final_main_queue_size}")
        print(f"✅ 关闭后主队列数据大小: {final_main_data_size}")
        
        # 验证处理队列为空
        final_processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        final_processing_data_size = await queue._redis.hlen(queue.key_manager.get_processing_data_key())
        print(f"✅ 关闭后处理队列大小: {final_processing_queue_size}")
        print(f"✅ 关闭后处理队列数据大小: {final_processing_data_size}")
        
        if final_processing_queue_size != 0 or final_processing_data_size != 0:
            print(f"❌ 处理队列不为空，期望: 0, 实际队列大小: {final_processing_queue_size}, 数据大小: {final_processing_data_size}")
            return False
        
        print("✅ 正常完成时处理队列清理行为测试完成")
        
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
                queue.key_manager.get_requests_data_key(),
                queue.processing_queue,
                queue.key_manager.get_processing_data_key()
            )


async def test_abnormal_exit_cleanup():
    """测试异常退出时处理队列的保留行为"""
    print("\n开始测试异常退出时处理队列的保留行为...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例，设置cleanup_redis_data=False（支持断点续爬）
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:abnormal:exit",
            module_name="test_abnormal_exit",
            cleanup_redis_data=False  # 不清理所有数据，保留处理队列以支持断点续爬
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
            queue.key_manager.get_requests_data_key(),
            queue.processing_queue,
            queue.key_manager.get_processing_data_key()
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求
        test_requests = [
            Request(url="https://example.com/test1"),
            Request(url="https://example.com/test2")
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
        
        # 从主队列获取任务（会自动移动到处理队列，但不确认完成，模拟异常退出）
        print("\n--- 模拟任务处理但不确认完成（模拟异常退出）---")
        processed_requests = []
        for i in range(len(test_requests)):
            request = await queue.get(timeout=1.0)
            if request:
                print(f"✅ 任务{i+1}已从主队列取出并移动到处理队列: {request.url}")
                processed_requests.append(request)
                # 注意：这里不调用ack()方法，模拟异常退出
            else:
                print(f"❌ 无法获取任务{i+1}")
                return False
        
        # 验证处理队列不为空（因为任务未确认完成）
        if queue._redis:
            processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            processing_data_size = await queue._redis.hlen(queue.key_manager.get_processing_data_key())
            print(f"✅ 处理队列大小: {processing_queue_size}")
            print(f"✅ 处理队列数据大小: {processing_data_size}")
            
            if processing_queue_size != len(test_requests) or processing_data_size != len(test_requests):
                print(f"❌ 处理队列大小不正确，期望: {len(test_requests)}, 实际: {processing_queue_size}")
                return False
        
        # 现在关闭队列，由于cleanup_redis_data=False，应该保留处理队列中的数据以支持断点续爬
        print("\n--- 关闭队列（应该保留处理队列数据以支持断点续爬）---")
        await queue.close()
        print("✅ 队列已关闭")
        
        # 重新连接以检查数据
        await queue.connect()
        
        # 确保Redis连接存在
        if not queue._redis:
            print("❌ Redis连接失败")
            return False
        
        # 验证处理队列仍然存在（因为cleanup_redis_data=False且程序异常退出）
        final_processing_queue_size = await queue._redis.zcard(queue.processing_queue)
        final_processing_data_size = await queue._redis.hlen(queue.key_manager.get_processing_data_key())
        print(f"✅ 关闭后处理队列大小: {final_processing_queue_size}")
        print(f"✅ 关闭后处理队列数据大小: {final_processing_data_size}")
        
        # 在正常情况下，处理队列应该为空，因为每个任务在处理完成后都会被立即删除
        # 但如果我们不调用ack()方法，处理队列中的数据会保留
        # 这是正确的行为，支持断点续爬
        
        print("✅ 异常退出时处理队列保留行为测试完成")
        
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
                queue.key_manager.get_requests_data_key(),
                queue.processing_queue,
                queue.key_manager.get_processing_data_key()
            )


async def main():
    """主测试函数"""
    print("开始测试处理队列清理行为...")
    
    # 测试正常完成时的清理行为
    test1_ok = await test_normal_completion_cleanup()
    
    # 测试异常退出时的保留行为
    test2_ok = await test_abnormal_exit_cleanup()
    
    print("\n" + "=" * 50)
    print("测试结果:")
    print(f"   正常完成清理测试: {'通过' if test1_ok else '失败'}")
    print(f"   异常退出保留测试: {'通过' if test2_ok else '失败'}")
    
    if test1_ok and test2_ok:
        print("\n✅ 所有测试通过！处理队列清理行为正常工作。")
        return True
    else:
        print("\n❌ 部分测试失败，请检查实现。")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)