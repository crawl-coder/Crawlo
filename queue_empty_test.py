#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
队列空状态判断逻辑验证脚本
"""

import asyncio
from unittest.mock import Mock, MagicMock
from crawlo.core.scheduler import Scheduler
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


async def test_queue_empty_logic():
    """
    测试队列空状态判断逻辑
    """
    print("=== 队列空状态判断逻辑验证 ===\n")
    
    # 创建模拟的crawler对象
    crawler = Mock()
    crawler.settings = Mock()
    crawler.settings.get = Mock(return_value='memory')
    
    # 创建dupe_filter模拟对象
    dupe_filter = Mock()
    # 确保没有requested_async属性，这样会走else分支调用requested方法
    # 删除requested_async属性，让其使用common_call方式调用requested
    if hasattr(dupe_filter, 'requested_async'):
        delattr(dupe_filter, 'requested_async')
    dupe_filter.requested = Mock(return_value=False)  # 模拟非重复请求
    
    # 创建stats模拟对象
    stats = Mock()
    
    # 创建Scheduler实例
    scheduler = Scheduler(crawler, dupe_filter, stats, priority=0)
    
    print("1. 测试未初始化队列的情况:")
    print(f"   idle(): {scheduler.idle()}")
    print(f"   len(scheduler): {len(scheduler)}")
    print(f"   async_idle(): {await scheduler.async_idle()}")
    
    print("\n2. 测试内存队列的情况:")
    # 创建内存队列配置
    config = QueueConfig(queue_type=QueueType.MEMORY)
    queue_manager = QueueManager(config)
    
    # 初始化队列管理器
    await queue_manager.initialize()
    scheduler.queue_manager = queue_manager
    
    print(f"   idle(): {scheduler.idle()}")
    print(f"   len(scheduler): {len(scheduler)}")
    print(f"   async_idle(): {await scheduler.async_idle()}")
    
    print("\n3. 模拟添加请求到队列后:")
    # 创建更完整的模拟请求
    from crawlo import Request
    request = Request(url="http://example.com", priority=0)
    
    # 添加请求到队列
    result = await scheduler.enqueue_request(request)
    print(f"   enqueue_request() 返回: {result}")
    print(f"   idle(): {scheduler.idle()}")
    print(f"   len(scheduler): {len(scheduler)}")
    print(f"   async_idle(): {await scheduler.async_idle()}")
    
    print("\n4. 从队列获取请求后:")
    next_req = await scheduler.next_request()
    print(f"   next_request() 返回: {next_req is not None}")
    print(f"   idle(): {scheduler.idle()}")
    print(f"   len(scheduler): {len(scheduler)}")
    print(f"   async_idle(): {await scheduler.async_idle()}")
    
    print("\n5. 测试Redis队列的情况:")
    # 测试Redis队列的idle逻辑（如果Redis可用）
    from crawlo.queue.queue_manager import REDIS_AVAILABLE
    if REDIS_AVAILABLE:
        redis_config = QueueConfig(
            queue_type=QueueType.REDIS,
            redis_url="redis://localhost:6379/0"
        )
        redis_queue_manager = QueueManager(redis_config)
        try:
            await redis_queue_manager.initialize()
            scheduler.queue_manager = redis_queue_manager
            
            print(f"   idle(): {scheduler.idle()}")
            print(f"   len(scheduler): {len(scheduler)}")
            print(f"   async_idle(): {await scheduler.async_idle()}")
            
            # 清理
            await redis_queue_manager.close()
        except Exception as e:
            print(f"   Redis队列初始化失败（这可能是正常的）: {e}")
    else:
        print("   Redis不可用，跳过Redis队列测试")
    
    # 清理
    await queue_manager.close()
    
    print("\n=== 测试完成 ===")


def analyze_queue_empty_logic():
    """
    分析队列空状态判断逻辑
    """
    print("\n=== 队列空状态判断逻辑分析 ===\n")
    
    print("1. Scheduler.idle() 方法:")
    print("   - 同步方法，用于快速判断队列是否为空")
    print("   - 对于内存队列：使用队列管理器的同步empty()方法")
    print("   - 对于Redis队列：返回False（保守策略，避免误判为空）")
    print("   - 依赖 __len__() 方法的结果")
    
    print("\n2. Scheduler.async_idle() 方法:")
    print("   - 异步方法，提供更准确的队列空状态判断")
    print("   - 使用队列管理器的 async_empty() 方法")
    print("   - 对内存队列和Redis队列都有准确的判断逻辑")
    
    print("\n3. Scheduler.__len__() 方法:")
    print("   - 返回队列的大致大小")
    print("   - 修正后：尝试获取实际队列大小，而非简单的0或1")
    
    print("\n4. QueueManager.empty() 方法:")
    print("   - 同步方法，用于内存队列比较准确")
    print("   - 对于Redis队列：由于操作本质是异步的，返回True（保守）")
    
    print("\n5. QueueManager.async_empty() 方法:")
    print("   - 异步方法，对内存队列和Redis队列都提供准确判断")
    
    print("\n6. 优化后的逻辑:")
    print("   - idle() 方法现在根据队列类型采取不同策略")
    print("   - 对内存队列使用可靠的同步检查")
    print("   - 对Redis队列返回False，促使系统使用更准确的异步方法")


if __name__ == "__main__":
    print("队列空状态判断逻辑验证")
    print("=" * 50)
    
    # 分析逻辑
    analyze_queue_empty_logic()
    
    # 运行测试
    try:
        asyncio.run(test_queue_empty_logic())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()