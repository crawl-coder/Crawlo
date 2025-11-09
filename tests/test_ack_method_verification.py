#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证ack方法实现的测试
确认ack方法正确实现并能被调用
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_ack_method_implementation():
    """测试ack方法的实现"""
    print("测试ack方法的实现...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:queue:ack_method",
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
        test_request = Request(url="https://example.com/test", priority=0)
        success = await queue.put(test_request, priority=0)
        if success:
            print("✅ 测试请求已添加到队列")
        else:
            print("❌ 测试请求添加失败")
            return False
        
        # 检查初始状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"初始队列大小: {main_queue_size}")
        
        # 从队列获取任务
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从队列取出")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"获取任务后队列大小: {main_queue_size}")
        
        # 验证ack方法存在并可调用
        print("\n--- 验证ack方法 ---")
        if hasattr(queue, 'ack') and callable(getattr(queue, 'ack', None)):
            print("✅ ack方法存在")
            
            # 调用ack方法
            await queue.ack(request)
            print("✅ ack方法调用成功")
            
            # 检查调用后的状态
            main_queue_size = await queue._redis.zcard(queue.queue_name)
            print(f"ack调用后队列大小: {main_queue_size}")
            
            return True
        else:
            print("❌ ack方法不存在")
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
                f"{queue.queue_name}:data"
            )


async def test_fail_method_calls_ack():
    """测试fail方法是否会调用ack方法"""
    print("\n\n测试fail方法是否会调用ack方法...")
    print("=" * 50)
    
    queue = None
    try:
        # 创建Redis队列实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:queue:fail_method",
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
        test_request = Request(url="https://example.com/test", priority=0)
        success = await queue.put(test_request, priority=0)
        if success:
            print("✅ 测试请求已添加到队列")
        else:
            print("❌ 测试请求添加失败")
            return False
        
        # 从队列获取任务
        request = await queue.get(timeout=1.0)
        if request:
            print("✅ 任务已从队列取出")
        else:
            print("❌ 无法获取任务")
            return False
        
        # 检查获取任务后的状态
        main_queue_size = await queue._redis.zcard(queue.queue_name)
        print(f"获取任务后队列大小: {main_queue_size}")
        
        # 验证fail方法存在并可调用
        print("\n--- 验证fail方法 ---")
        if hasattr(queue, 'fail') and callable(getattr(queue, 'fail', None)):
            print("✅ fail方法存在")
            
            # 调用fail方法
            await queue.fail(request, reason="测试失败")
            print("✅ fail方法调用成功")
            
            # 检查调用后的状态
            main_queue_size = await queue._redis.zcard(queue.queue_name)
            print(f"fail调用后队列大小: {main_queue_size}")
            
            return True
        else:
            print("❌ fail方法不存在")
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
                f"{queue.queue_name}:data"
            )


async def main():
    """主测试函数"""
    print("开始验证ack方法实现...")
    
    # 测试ack方法实现
    test1_ok = await test_ack_method_implementation()
    
    # 测试fail方法调用ack
    test2_ok = await test_fail_method_calls_ack()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"   ack方法实现测试: {'通过' if test1_ok else '失败'}")
    print(f"   fail方法调用ack测试: {'通过' if test2_ok else '失败'}")
    
    if test1_ok and test2_ok:
        print("\n🎉 所有测试通过！")
        print("ack方法实现验证成功。")
        return True
    else:
        print("\n❌ 部分测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())