#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的处理队列测试
验证Redis队列的基本功能
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_basic_queue_operations():
    """测试基本队列操作"""
    print("测试基本队列操作...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:queue:basic_ops",
            timeout=300
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
            f"{queue.queue_name}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 测试1: 添加请求
        print("\n--- 测试1: 添加请求 ---")
        request1 = Request(url="https://example.com/test1", priority=0)
        request2 = Request(url="https://example.com/test2", priority=1)
        request3 = Request(url="https://example.com/test3", priority=2)
        
        # 添加请求到队列
        await queue.put(request1, priority=0)
        await queue.put(request2, priority=1)
        await queue.put(request3, priority=2)
        print("✅ 所有请求已添加到队列")
        
        # 检查队列大小
        queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"队列大小: {queue_size}")
        
        # 测试2: 获取请求（按优先级）
        print("\n--- 测试2: 获取请求 ---")
        # 应该按优先级顺序获取请求（高优先级先获取）
        request = await queue.get(timeout=1.0)
        if request and request.url == "https://example.com/test3":
            print("✅ 正确获取到高优先级请求")
        else:
            print("❌ 优先级排序可能有问题")
            return False
            
        request = await queue.get(timeout=1.0)
        if request and request.url == "https://example.com/test2":
            print("✅ 正确获取到中优先级请求")
        else:
            print("❌ 优先级排序可能有问题")
            return False
            
        request = await queue.get(timeout=1.0)
        if request and request.url == "https://example.com/test1":
            print("✅ 正确获取到低优先级请求")
        else:
            print("❌ 优先级排序可能有问题")
            return False
            
        # 测试3: 队列为空时的行为
        print("\n--- 测试3: 空队列行为 ---")
        request = await queue.get(timeout=1.0)
        if request is None:
            print("✅ 空队列正确返回None")
        else:
            print("❌ 空队列应该返回None")
            return False
            
        print("\n✅ 所有基本队列操作测试通过")
        return True
        
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


async def test_request_ack_operations():
    """测试请求确认操作"""
    print("\n\n测试请求确认操作...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:queue:ack_ops",
            timeout=300
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
            f"{queue.queue_name}:data"
        )
        print("✅ 旧数据清理完成")
        
        # 添加测试请求
        test_request = Request(url="https://example.com/test_ack", priority=0)
        await queue.put(test_request, priority=0)
        print("✅ 测试请求已添加到队列")
        
        # 获取请求
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 请求已从队列取出")
        else:
            print("❌ 无法获取请求")
            return False
            
        # 调用ack确认请求完成
        await queue.ack(request)
        print("✅ 已调用ack()方法确认请求完成")
        
        # 检查队列状态
        queue_size = await queue._redis.zcard(queue.queue_name)
        if queue_size == 0:
            print("✅ 请求已正确从队列中移除")
        else:
            print(f"❌ 队列中仍有 {queue_size} 个请求")
            return False
            
        print("\n✅ 请求确认操作测试通过")
        return True
        
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
    print("开始简单的处理队列测试...")
    
    # 测试基本队列操作
    test1_ok = await test_basic_queue_operations()
    
    # 测试请求确认操作
    test2_ok = await test_request_ack_operations()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"   基本队列操作测试: {'通过' if test1_ok else '失败'}")
    print(f"   请求确认操作测试: {'通过' if test2_ok else '失败'}")
    
    if test1_ok and test2_ok:
        print("\n🎉 所有测试通过！")
        print("简单的处理队列功能验证成功。")
        return True
    else:
        print("\n❌ 部分测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())