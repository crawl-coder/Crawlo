#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Key 命名规范测试脚本
用于验证新的统一Redis key命名规范是否正确实现
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.backends.redis_priority import RedisPriorityQueue
from crawlo.filters.aioredis_filter import AioRedisFilter
import redis.asyncio as aioredis


class MockSettings:
    """模拟设置类"""
    def __init__(self, project_name="test_project"):
        self.project_name = project_name
        self.REDIS_URL = "redis://127.0.0.1:6379/15"  # 使用测试数据库
        self.REDIS_TTL = 0
        self.CLEANUP_FP = 0
        self.FILTER_DEBUG = True
        self.LOG_LEVEL = "INFO"
        self.DECODE_RESPONSES = True
    
    def get(self, key, default=None):
        if key == 'PROJECT_NAME':
            return self.project_name
        elif key == 'REDIS_URL':
            return self.REDIS_URL
        elif key == 'FILTER_DEBUG':
            return self.FILTER_DEBUG
        elif key == 'LOG_LEVEL':
            return self.LOG_LEVEL
        elif key == 'DECODE_RESPONSES':
            return self.DECODE_RESPONSES
        return default
    
    def get_bool(self, key, default=False):
        if key == 'FILTER_DEBUG':
            return self.FILTER_DEBUG
        elif key == 'DECODE_RESPONSES':
            return self.DECODE_RESPONSES
        elif key == 'CLEANUP_FP':
            return self.CLEANUP_FP
        return default
    
    def get_int(self, key, default=0):
        if key == 'REDIS_TTL':
            return self.REDIS_TTL
        return default


class MockCrawler:
    """模拟爬虫类"""
    def __init__(self, project_name="test_project"):
        self.settings = MockSettings(project_name)
        self.stats = {}


async def test_redis_key_naming():
    """测试Redis key命名规范"""
    print("🔍 测试Redis key命名规范...")
    
    project_name = "test_redis_naming"
    
    try:
        # 1. 测试RedisPriorityQueue的key命名
        print("   1. 测试RedisPriorityQueue的key命名...")
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            module_name=project_name
        )
        
        expected_queue_name = f"crawlo:{project_name}:queue:requests"
        expected_processing_queue = f"crawlo:{project_name}:queue:processing"
        expected_failed_queue = f"crawlo:{project_name}:queue:failed"
        
        assert queue.queue_name == expected_queue_name, f"队列名称不匹配: {queue.queue_name} != {expected_queue_name}"
        assert queue.processing_queue == expected_processing_queue, f"处理中队列名称不匹配: {queue.processing_queue} != {expected_processing_queue}"
        assert queue.failed_queue == expected_failed_queue, f"失败队列名称不匹配: {queue.failed_queue} != {expected_failed_queue}"
        
        print(f"      队列名称: {queue.queue_name}")
        print(f"      处理中队列名称: {queue.processing_queue}")
        print(f"      失败队列名称: {queue.failed_queue}")
        
        # 2. 测试AioRedisFilter的key命名
        print("   2. 测试AioRedisFilter的key命名...")
        mock_crawler = MockCrawler(project_name)
        filter_instance = AioRedisFilter.create_instance(mock_crawler)
        
        expected_filter_key = f"crawlo:{project_name}:filter:fingerprint"
        assert filter_instance.redis_key == expected_filter_key, f"过滤器key不匹配: {filter_instance.redis_key} != {expected_filter_key}"
        
        print(f"      过滤器key: {filter_instance.redis_key}")
        
        # 3. 测试实际的Redis连接和基本操作
        print("   3. 测试实际的Redis连接...")
        await queue.connect()
        
        # 为AioRedisFilter创建Redis连接
        redis_client = aioredis.from_url(
            "redis://127.0.0.1:6379/15",
            decode_responses=False,
            max_connections=20,
            encoding='utf-8'
        )
        filter_instance.redis = redis_client
        
        # 确保连接正常
        await queue._redis.ping()
        await filter_instance.redis.ping()
        
        # 清理可能存在的旧数据
        await queue._redis.delete(queue.queue_name, queue.processing_queue, queue.failed_queue)
        await filter_instance.redis.delete(filter_instance.redis_key)
        
        # 验证Redis中key的命名格式
        print("   4. 验证Redis中key的命名格式...")
        # 检查key是否符合命名规范
        assert queue.queue_name.startswith("crawlo:"), "队列名称未使用crawlo前缀"
        assert ":queue:requests" in queue.queue_name, "队列名称未包含queue:requests"
        
        assert queue.processing_queue.startswith("crawlo:"), "处理中队列名称未使用crawlo前缀"
        assert ":queue:processing" in queue.processing_queue, "处理中队列名称未包含queue:processing"
        
        assert queue.failed_queue.startswith("crawlo:"), "失败队列名称未使用crawlo前缀"
        assert ":queue:failed" in queue.failed_queue, "失败队列名称未包含queue:failed"
        
        assert filter_instance.redis_key.startswith("crawlo:"), "过滤器key未使用crawlo前缀"
        assert ":filter:fingerprint" in filter_instance.redis_key, "过滤器key未包含filter:fingerprint"
        
        print("      所有key都符合命名规范")
        
        # 5. 清理测试数据
        print("   5. 清理测试数据...")
        await queue._redis.delete(queue.queue_name, queue.processing_queue, queue.failed_queue)
        await filter_instance.redis.delete(filter_instance.redis_key)
        await queue.close()
        await filter_instance.redis.close()
        
        print("Redis key命名规范测试通过！")
        return True
        
    except Exception as e:
        print(f"Redis key命名规范测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始Redis key命名规范测试...")
    print("=" * 50)
    
    try:
        success = await test_redis_key_naming()
        
        print("=" * 50)
        if success:
            print("所有测试通过！新的Redis key命名规范工作正常")
        else:
            print("测试失败，请检查实现")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"测试过程中发生异常: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)