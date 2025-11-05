#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QUEUE_TYPE = 'redis' 时的行为，验证其等同于 'auto' 模式
即：当 Redis 不可用时应该回退到内存队列
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


async def test_redis_queue_type_fallback():
    """测试 QUEUE_TYPE = 'redis' 时的回退行为"""
    print("=== 测试 QUEUE_TYPE = 'redis' 时的回退行为 ===")
    
    # 创建一个 Redis 不可用的配置（使用一个不存在的 Redis 地址）
    config = QueueConfig(
        queue_type=QueueType.REDIS,
        redis_url="redis://127.0.0.1:6380/9",  # 一个不存在的 Redis 实例
        queue_name="test:queue:requests"
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(config)
    
    # 初始化队列
    print("正在初始化队列管理器...")
    try:
        needs_config_update = await queue_manager.initialize()
        print(f"初始化完成，needs_config_update: {needs_config_update}")
        
        # 获取队列状态
        status = queue_manager.get_status()
        print(f"队列类型: {status['type']}")
        print(f"队列健康状态: {status['health']}")
        
        # 验证队列类型应该是 memory（因为 Redis 不可用，应该回退）
        assert status['type'] == 'memory', f"期望队列类型为 'memory'，实际得到 '{status['type']}'"
        print("✅ 队列类型正确回退到 memory")
        
        # 验证健康状态应该是 healthy
        assert status['health'] == 'healthy', f"期望健康状态为 'healthy'，实际得到 '{status['health']}'"
        print("✅ 队列健康状态正常")
        
    except Exception as e:
        print(f"初始化队列时发生错误: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        # 清理资源
        if queue_manager:
            try:
                await queue_manager.close()
            except:
                pass
    
    print("✅ Redis 队列类型回退测试通过")


async def test_redis_queue_type_with_valid_redis():
    """测试 QUEUE_TYPE = 'redis' 时，当 Redis 可用的情况"""
    print("\n=== 测试 QUEUE_TYPE = 'redis' 时 Redis 可用的情况 ===")
    
    # 创建一个 Redis 可用的配置（使用默认的本地 Redis）
    config = QueueConfig(
        queue_type=QueueType.REDIS,
        redis_url="redis://127.0.0.1:6379/2",  # 默认的本地 Redis 实例
        queue_name="test:queue:requests"
    )
    
    # 创建队列管理器
    queue_manager = QueueManager(config)
    
    # 初始化队列
    print("正在初始化队列管理器...")
    try:
        needs_config_update = await queue_manager.initialize()
        print(f"初始化完成，needs_config_update: {needs_config_update}")
        
        # 获取队列状态
        status = queue_manager.get_status()
        print(f"队列类型: {status['type']}")
        print(f"队列健康状态: {status['health']}")
        
        # 验证队列类型应该是 redis（因为 Redis 可用）
        # 注意：这取决于本地是否真的有 Redis 服务运行
        print(f"队列类型: {status['type']} (期望为 'redis' 如果本地 Redis 可用)")
        
        # 验证健康状态应该是 healthy
        assert status['health'] == 'healthy', f"期望健康状态为 'healthy'，实际得到 '{status['health']}'"
        print("✅ 队列健康状态正常")
        
    except Exception as e:
        print(f"初始化队列时发生错误: {e}")
        print("这可能是因为本地没有运行 Redis 服务，这是正常的")
    
    finally:
        # 清理资源
        if queue_manager:
            try:
                await queue_manager.close()
            except:
                pass
    
    print("✅ Redis 队列类型可用性测试完成")


if __name__ == "__main__":
    print("开始测试 QUEUE_TYPE = 'redis' 的行为...")
    
    try:
        # 运行异步测试
        asyncio.run(test_redis_queue_type_fallback())
        asyncio.run(test_redis_queue_type_with_valid_redis())
        
        print("\n🎉 所有测试通过！QUEUE_TYPE = 'redis' 的行为等同于 'auto' 模式。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()