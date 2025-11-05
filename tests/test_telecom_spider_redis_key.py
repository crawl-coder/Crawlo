#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电信设备许可证爬虫Redis Key测试脚本
用于验证分布式爬虫是否符合新的Redis key命名规范
"""
import sys
import os
import asyncio
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType
from crawlo.filters.aioredis_filter import AioRedisFilter
from crawlo.pipelines.redis_dedup_pipeline import RedisDedupPipeline


class MockSettings:
    """模拟设置类"""
    def __init__(self, project_name="telecom_licenses_distributed"):
        self.project_name = project_name
        self.REDIS_HOST = '127.0.0.1'
        self.REDIS_PORT = 6379
        self.REDIS_PASSWORD = ''
        self.REDIS_DB = 2
        self.REDIS_URL = f'redis://127.0.0.1:6379/{self.REDIS_DB}'
        self.REDIS_TTL = 0
        self.CLEANUP_FP = 0
        self.FILTER_DEBUG = True
        self.LOG_LEVEL = "INFO"
        self.DECODE_RESPONSES = True
        self.SCHEDULER_QUEUE_NAME = f'crawlo:{project_name}:queue:requests'
    
    def get(self, key, default=None):
        if key == 'PROJECT_NAME':
            return self.project_name
        elif key == 'REDIS_HOST':
            return self.REDIS_HOST
        elif key == 'REDIS_PASSWORD':
            return self.REDIS_PASSWORD
        elif key == 'REDIS_URL':
            return self.REDIS_URL
        elif key == 'FILTER_DEBUG':
            return self.FILTER_DEBUG
        elif key == 'LOG_LEVEL':
            return self.LOG_LEVEL
        elif key == 'DECODE_RESPONSES':
            return self.DECODE_RESPONSES
        elif key == 'SCHEDULER_QUEUE_NAME':
            return self.SCHEDULER_QUEUE_NAME
        return default
    
    def get_bool(self, key, default=False):
        if key == 'FILTER_DEBUG':
            return self.FILTER_DEBUG
        elif key == 'DECODE_RESPONSES':
            return self.DECODE_RESPONSES
        elif key == 'CLEANUP_FP':
            return self.CLEANUP_FP
        return default
    
    def get_int(self, key, default=0):  # 修复方法名
        if key == 'REDIS_TTL':
            return self.REDIS_TTL
        elif key == 'REDIS_PORT':
            return self.REDIS_PORT
        elif key == 'REDIS_DB':
            return self.REDIS_DB
        elif key == 'SCHEDULER_MAX_QUEUE_SIZE':
            return 1000
        elif key == 'QUEUE_MAX_RETRIES':
            return 3
        elif key == 'QUEUE_TIMEOUT':
            return 300
        return default


class MockCrawler:
    """模拟爬虫类"""
    def __init__(self, project_name="telecom_licenses_distributed"):
        self.settings = MockSettings(project_name)
        self.stats = {}


async def test_telecom_spider_redis_key():
    """测试电信设备许可证爬虫Redis key命名规范"""
    print("🔍 测试电信设备许可证爬虫Redis key命名规范...")
    
    project_name = "telecom_licenses_distributed"
    expected_prefix = f"crawlo:{project_name}"
    
    try:
        # 1. 测试QueueManager和RedisPriorityQueue
        print("   1. 测试队列管理器...")
        queue_config = QueueConfig(
            queue_type=QueueType.REDIS,
            redis_url="redis://127.0.0.1:6379/2",
            queue_name=f"crawlo:{project_name}:queue:requests",  # 使用统一命名规范
            max_queue_size=1000,
            max_retries=3,
            timeout=300
        )
        
        queue_manager = QueueManager(queue_config)
        queue = await queue_manager._create_queue(QueueType.REDIS)
        
        # 验证队列名称是否符合规范
        expected_queue_name = f"{expected_prefix}:queue:requests"
        expected_processing_queue = f"{expected_prefix}:queue:processing"
        expected_failed_queue = f"{expected_prefix}:queue:failed"
        
        assert queue.queue_name == expected_queue_name, f"队列名称不匹配: {queue.queue_name} != {expected_queue_name}"
        assert queue.processing_queue == expected_processing_queue, f"处理中队列名称不匹配: {queue.processing_queue} != {expected_processing_queue}"
        assert queue.failed_queue == expected_failed_queue, f"失败队列名称不匹配: {queue.failed_queue} != {expected_failed_queue}"
        
        print(f"      请求队列: {queue.queue_name}")
        print(f"      处理中队列: {queue.processing_queue}")
        print(f"      失败队列: {queue.failed_queue}")
        
        # 2. 测试AioRedisFilter
        print("   2. 测试请求去重过滤器...")
        mock_crawler = MockCrawler(project_name)
        filter_instance = AioRedisFilter.create_instance(mock_crawler)
        
        expected_filter_key = f"{expected_prefix}:filter:fingerprint"
        assert filter_instance.redis_key == expected_filter_key, f"过滤器key不匹配: {filter_instance.redis_key} != {expected_filter_key}"
        
        print(f"      请求去重key: {filter_instance.redis_key}")
        
        # 3. 测试RedisDedupPipeline
        print("   3. 测试数据项去重管道...")
        dedup_pipeline = RedisDedupPipeline.from_crawler(mock_crawler)
        
        expected_item_key = f"{expected_prefix}:item:fingerprint"
        assert dedup_pipeline.redis_key == expected_item_key, f"数据项去重key不匹配: {dedup_pipeline.redis_key} != {expected_item_key}"
        
        print(f"      数据项去重key: {dedup_pipeline.redis_key}")
        
        # 4. 验证所有key都使用统一前缀
        print("   4. 验证统一前缀...")
        all_keys = [
            queue.queue_name,
            queue.processing_queue,
            queue.failed_queue,
            filter_instance.redis_key,
            dedup_pipeline.redis_key
        ]
        
        for key in all_keys:
            assert key.startswith(expected_prefix), f"Key未使用统一前缀: {key}"
            print(f"      {key}")
        
        print("电信设备许可证爬虫Redis key命名规范测试通过！")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        try:
            if 'queue' in locals():
                await queue.close()
            if 'filter_instance' in locals() and hasattr(filter_instance, 'redis'):
                await filter_instance.redis.close()
            if 'dedup_pipeline' in locals() and hasattr(dedup_pipeline, 'redis_client'):
                dedup_pipeline.redis_client.close()
        except:
            pass


async def main():
    """主测试函数"""
    print("开始电信设备许可证爬虫Redis key命名规范测试...")
    print("=" * 60)
    
    try:
        success = await test_telecom_spider_redis_key()
        
        print("=" * 60)
        if success:
            print("所有测试通过！电信设备许可证爬虫符合新的Redis key命名规范")
        else:
            print("测试失败，请检查实现")
            return 1
            
    except Exception as e:
        print("=" * 60)
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)