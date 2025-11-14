#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key格式修复验证测试脚本
用于验证修复后的处理队列key格式是否正确
"""
import asyncio
import sys
import os
import traceback
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_key_format_fix_verification():
    """验证key格式修复"""
    print("开始验证key格式修复...")
    print("=" * 50)
    
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:key:format:fix",
            module_name="test_key_format_fix"
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
        test_request = Request(url="https://example.com/key-format-fix", priority=1)
        
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
            
            if keys:
                processing_key = keys[0][0] if isinstance(keys[0], (list, tuple)) else keys[0]
                print(f"✅ 处理队列中的原始key: {processing_key}")
                print(f"✅ 处理队列中的key类型: {type(processing_key)}")
                
                # 解析key
                if isinstance(processing_key, bytes):
                    key_str = processing_key.decode('utf-8')
                else:
                    key_str = str(processing_key)
                print(f"✅ 解析后的key: {key_str}")
                
                # 验证key格式是否正确（不应该包含嵌套引号）
                if "b'" in key_str or 'b"' in key_str:
                    print("❌ Key格式仍然不正确，包含嵌套引号")
                    return False
                else:
                    print("✅ Key格式正确，不包含嵌套引号")
                
                # 测试ack方法是否能正确匹配
                print("\n--- 测试ack方法匹配 ---")
                request_key = queue._get_request_key(retrieved_request)
                print(f"✅ 请求key: {request_key}")
                
                # 使用zscan查找匹配的key
                cursor = 0
                found_keys = []
                while True:
                    cursor, scan_keys = await queue._redis.zscan(queue.processing_queue, cursor, match=f"{request_key}:*")
                    found_keys.extend(scan_keys)
                    if cursor == 0:
                        break
                print(f"✅ ZSCAN找到的匹配key: {found_keys}")
                
                if found_keys:
                    print("✅ ack方法应该能正确匹配并清理任务")
                else:
                    print("❌ ack方法无法匹配任务")
        
        # 测试ack方法
        print("\n--- 测试ack方法 ---")
        await queue.ack(retrieved_request)
        
        # 检查处理队列是否被清理
        if queue._redis:
            final_processing_queue_size = await queue._redis.zcard(queue.processing_queue)
            final_processing_data_size = await queue._redis.hlen(f"{queue.processing_queue}:data")
            print(f"✅ ACK后处理队列大小: {final_processing_queue_size}")
            print(f"✅ ACK后处理数据大小: {final_processing_data_size}")
            
            if final_processing_queue_size == 0 and final_processing_data_size == 0:
                print("✅ ACK方法正常工作，处理队列已正确清理")
            else:
                print("❌ ACK方法未正确工作，处理队列仍有残留数据")
        
        # 清理测试数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        await queue.close()
        
        print("\n🎉 Key格式修复验证完成！")
        return True
        
    except Exception as e:
        print(f"❌ Key格式修复验证失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始Key格式修复验证测试...")
    
    try:
        success = await test_key_format_fix_verification()
        
        if success:
            print("\n✅ Key格式修复验证通过！")
            return 0
        else:
            print("\n❌ Key格式修复验证失败！")
            return 1
            
    except Exception as e:
        print(f"\n❌ Key格式修复验证过程中发生异常: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)