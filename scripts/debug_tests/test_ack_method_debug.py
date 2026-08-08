#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACK方法调试测试脚本
用于深入分析为什么ack()方法没有正确清理处理队列
"""
import asyncio
import sys
import os
import traceback
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.backends.redis_priority import RedisPriorityQueue
from crawlo.http.request import Request


async def test_ack_method_debug():
    """调试ACK方法"""
    print("开始调试ACK方法...")
    print("=" * 50)
    
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:ack:debug",
            module_name="test_ack_debug"
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
        
        # 添加测试任务
        test_request = Request(url="https://example.com/debug", priority=1)
        
        # 将任务添加到主队列
        success = await queue.put(test_request, priority=test_request.priority)
        if success:
            print(f"✅ 任务已添加到主队列: {test_request.url}")
        else:
            print(f"❌ 任务添加失败: {test_request.url}")
            return False
        
        # 显示主队列状态
        main_queue_size = await queue.qsize()
        print(f"✅ 主队列大小: {main_queue_size}")
        
        # 从主队列获取任务（会自动移动到处理队列）
        print("\n--- 从主队列获取任务 ---")
        retrieved_request = await queue.get(timeout=1.0)
        if retrieved_request:
            print(f"✅ 任务已从主队列取出: {retrieved_request.url}")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查处理队列状态
        if queue._redis:
            processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            print(f"✅ 处理队列大小: {processing_queue_size}")
            
            # 显示处理队列中的所有key
            keys = await queue._redis.zrange(queue.processing_queue, 0, -1, withscores=True)
            print(f"✅ 处理队列中的key和分数: {keys}")
            
            # 显示处理数据中的内容
            data_keys = await queue._redis.hgetall(f"{queue.processing_queue}:data")
            print(f"✅ 处理数据中的内容: {data_keys}")
        else:
            print("❌ Redis连接丢失")
            return False
        
        # 分析请求key
        request_key = queue._get_request_key(retrieved_request)
        print(f"✅ 请求key: {request_key}")
        
        # 分析处理队列中的key格式
        if keys:
            processing_key = keys[0][0] if isinstance(keys[0], (list, tuple)) else keys[0]
            print(f"✅ 处理队列中的key: {processing_key}")
            print(f"✅ 处理队列中的key类型: {type(processing_key)}")
            
            # 检查是否匹配
            key_str = processing_key.decode('utf-8') if isinstance(processing_key, bytes) else processing_key
            print(f"✅ 处理队列key字符串: {key_str}")
            print(f"✅ 匹配模式: {request_key}:*")
            print(f"✅ 是否匹配: {key_str.startswith(request_key + ':')}")
        
        # 尝试使用zscan查找匹配的key
        print("\n--- 使用zscan查找匹配的key ---")
        if queue._redis:
            cursor = 0
            while True:
                cursor, found_keys = await queue._redis.zscan(queue.processing_queue, cursor, match=f"{request_key}:*")
                print(f"✅ ZSCAN找到的key: {found_keys}")
                if cursor == 0:
                    break
        
        # 尝试手动删除
        print("\n--- 尝试手动删除 ---")
        if queue._redis:
            # 直接删除处理队列中的key
            if keys:
                processing_key = keys[0][0] if isinstance(keys[0], (list, tuple)) else keys[0]
                result1 = await queue._redis.zrem(queue.processing_queue, processing_key)
                print(f"✅ ZREM结果: {result1}")
                
                # 删除数据
                result2 = await queue._redis.hdel(f"{queue.processing_queue}:data", processing_key)
                print(f"✅ HDEL结果: {result2}")
        
        # 最终检查
        if queue._redis:
            final_processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            final_processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
            print(f"✅ 最终处理队列大小: {final_processing_queue_size}")
            print(f"✅ 最终处理数据大小: {final_processing_data_size}")
        
        # 清理测试数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        await queue.close()
        
        print("\n🎉 调试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始ACK方法调试测试...")
    
    try:
        success = await test_ack_method_debug()
        
        if success:
            print("\n✅ 调试完成！")
            return 0
        else:
            print("\n❌ 调试失败！")
            return 1
            
    except Exception as e:
        print(f"\n❌ 调试过程中发生异常: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)