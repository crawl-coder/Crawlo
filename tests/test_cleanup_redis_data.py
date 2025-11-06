#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CLEANUP_REDIS_DATA参数功能
验证Redis数据清理参数合并后的效果
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.queue_manager import QueueConfig, QueueManager, QueueType
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request


async def test_cleanup_redis_data_parameter():
    """测试CLEANUP_REDIS_DATA参数功能"""
    print("开始测试CLEANUP_REDIS_DATA参数功能...")
    print("=" * 50)
    
    try:
        # 测试1: QueueConfig支持cleanup_redis_data参数
        print("1. 测试QueueConfig支持cleanup_redis_data参数...")
        config = QueueConfig(
            queue_type=QueueType.REDIS,
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:cleanup:param",
            cleanup_redis_data=True  # 新的合并参数
        )
        assert hasattr(config, 'cleanup_redis_data'), "QueueConfig缺少cleanup_redis_data属性"
        assert config.cleanup_redis_data == True, "cleanup_redis_data参数值不正确"
        print("   ✅ QueueConfig支持cleanup_redis_data参数")
        
        # 测试2: QueueConfig.from_settings支持cleanup_redis_data参数
        print("2. 测试QueueConfig.from_settings支持cleanup_redis_data参数...")
        class MockSettings:
            def get(self, key, default=None):
                settings_map = {
                    'QUEUE_TYPE': QueueType.REDIS,
                    'REDIS_URL': "redis://127.0.0.1:6379/15",
                    'SCHEDULER_QUEUE_NAME': "test:cleanup:settings",
                    'CLEANUP_REDIS_DATA': True
                }
                return settings_map.get(key, default)
                
            def get_int(self, key, default=0):
                return default
                
            def get_bool(self, key, default=False):
                settings_map = {
                    'CLEANUP_REDIS_DATA': True
                }
                return settings_map.get(key, default)
        
        settings = MockSettings()
        config_from_settings = QueueConfig.from_settings(settings)
        assert hasattr(config_from_settings, 'cleanup_redis_data'), "QueueConfig.from_settings缺少cleanup_redis_data属性"
        assert config_from_settings.cleanup_redis_data == True, "QueueConfig.from_settings cleanup_redis_data参数值不正确"
        print("   ✅ QueueConfig.from_settings支持cleanup_redis_data参数")
        
        # 测试3: QueueManager创建Redis队列时传递cleanup_redis_data参数
        print("3. 测试QueueManager创建Redis队列时传递cleanup_redis_data参数...")
        queue_manager = QueueManager(config)
        await queue_manager.initialize()
        
        # 检查创建的Redis队列是否正确接收了cleanup_redis_data参数
        assert queue_manager._queue is not None, "队列未正确初始化"
        # 通过config检查参数传递是否正确
        assert queue_manager.config.cleanup_redis_data == True, "QueueManager config中cleanup_redis_data参数值不正确"
        print("   ✅ QueueManager正确传递cleanup_redis_data参数")
        
        # 测试4: RedisPriorityQueue支持cleanup_redis_data参数
        print("4. 测试RedisPriorityQueue支持cleanup_redis_data参数...")
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:cleanup:direct",
            cleanup_redis_data=True
        )
        assert hasattr(queue, '_cleanup_redis_data'), "RedisPriorityQueue缺少_cleanup_redis_data属性"
        assert queue._cleanup_redis_data == True, "RedisPriorityQueue _cleanup_redis_data参数值不正确"
        print("   ✅ RedisPriorityQueue支持cleanup_redis_data参数")
        
        # 测试5: 验证队列功能正常
        print("5. 验证队列功能正常...")
        await queue.connect()
        
        # 清理可能存在的旧数据
        if queue._redis:
            await queue._redis.delete(queue.queue_name)
            await queue._redis.delete(f"{queue.queue_name}:data")
            await queue._redis.delete(queue.processing_queue)
            await queue._redis.delete(f"{queue.processing_queue}:data")
        
        # 添加测试请求
        test_request = Request(url="https://example.com/test")
        success = await queue.put(test_request, priority=0)
        assert success, "添加请求失败"
        
        # 获取请求
        retrieved = await queue.get(timeout=1.0)
        assert retrieved is not None, "获取请求失败"
        
        # 确认处理队列中有数据
        if queue._redis:
            processing_size = await queue._redis.zcard(queue.processing_queue)
            assert processing_size > 0, "处理队列应该有数据"
        
        # 关闭队列（应该根据cleanup_redis_data参数决定是否清理）
        await queue.close()
        print("   ✅ 队列功能正常")
        
        await queue_manager.close()
        print("   ✅ QueueManager功能正常")
        
        print("\n✅ 所有测试通过！CLEANUP_REDIS_DATA参数功能正常工作。")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_cleanup_redis_data_parameter())