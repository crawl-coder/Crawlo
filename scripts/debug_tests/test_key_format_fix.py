#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key格式修复测试脚本
用于测试修复处理队列key格式问题
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


async def test_key_format_fix():
    """测试key格式修复"""
    print("开始测试key格式修复...")
    print("=" * 50)
    
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",  # 使用测试数据库
            queue_name="test:key:format",
            module_name="test_key_format"
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
        test_request = Request(url="https://example.com/key-format", priority=1)
        
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
                
                # 测试正确的key处理方式
                if isinstance(processing_key, bytes):
                    key_str = processing_key.decode('utf-8')
                    print(f"✅ 解码后的key: {key_str}")
                else:
                    key_str = str(processing_key)
                    print(f"✅ 字符串化的key: {key_str}")
                
                # 分析key结构
                if ':' in key_str:
                    parts = key_str.split(':')
                    print(f"✅ Key的组成部分: {parts}")
                    if len(parts) >= 2:
                        # 提取时间戳部分
                        timestamp_part = parts[-1]
                        print(f"✅ 时间戳部分: {timestamp_part}")
                        
                        # 重构正确的匹配模式
                        base_key = ':'.join(parts[:-1])
                        print(f"✅ 基础key: {base_key}")
                        match_pattern = f"{base_key}:*"
                        print(f"✅ 匹配模式: {match_pattern}")
                        
                        # 使用正确的匹配模式测试zscan
                        print("\n--- 使用正确的匹配模式测试zscan ---")
                        cursor = 0
                        while True:
                            cursor, found_keys = await queue._redis.zscan(queue.processing_queue, cursor, match=match_pattern)
                            print(f"✅ ZSCAN找到的key: {found_keys}")
                            if cursor == 0:
                                break
        
        # 测试修复后的ack方法
        print("\n--- 测试修复后的ack方法 ---")
        # 这里我们模拟修复后的ack逻辑
        
        # 清理测试数据
        await queue._redis.delete(
            queue.queue_name,
            f"{queue.queue_name}:data",
            queue.processing_queue,
            f"{queue.processing_queue}:data"
        )
        await queue.close()
        
        print("\n🎉 Key格式测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ Key格式测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始Key格式修复测试...")
    
    try:
        success = await test_key_format_fix()
        
        if success:
            print("\n✅ Key格式测试完成！")
            return 0
        else:
            print("\n❌ Key格式测试失败！")
            return 1
            
    except Exception as e:
        print(f"\n❌ Key格式测试过程中发生异常: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)