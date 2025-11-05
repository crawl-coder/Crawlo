#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QueueManager Redis Key测试脚本
用于验证QueueManager创建Redis队列时是否正确传递module_name参数
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


class MockSettings:
    """模拟设置类"""
    def __init__(self):
        self.REDIS_HOST = '127.0.0.1'
        self.REDIS_PORT = 6379
        self.REDIS_PASSWORD = ''
        self.REDIS_DB = 0
        self.REDIS_URL = 'redis://127.0.0.1:6379/0'
        self.REDIS_TTL = 0
        self.SCHEDULER_MAX_QUEUE_SIZE = 1000
        self.QUEUE_MAX_RETRIES = 3
        self.QUEUE_TIMEOUT = 300
    
    def get(self, key, default=None):
        if key == 'REDIS_HOST':
            return self.REDIS_HOST
        elif key == 'REDIS_PASSWORD':
            return self.REDIS_PASSWORD
        elif key == 'REDIS_URL':
            return self.REDIS_URL
        elif key == 'REDIS_TTL':
            return self.REDIS_TTL
        return default
    
    def get_int(self, key, default=0):
        if key == 'REDIS_TTL':
            return self.REDIS_TTL
        elif key == 'REDIS_PORT':
            return 6379
        elif key == 'REDIS_DB':
            return 0
        elif key == 'SCHEDULER_MAX_QUEUE_SIZE':
            return 1000
        elif key == 'QUEUE_MAX_RETRIES':
            return 3
        elif key == 'QUEUE_TIMEOUT':
            return 300
        return default


async def test_queue_manager_redis_key():
    """测试QueueManager创建Redis队列时的key命名"""
    print("测试QueueManager创建Redis队列时的key命名...")
    
    try:
        # 测试不同的队列名称配置
        test_cases = [
            {
                "queue_name": "crawlo:books_distributed:queue:requests",
                "expected_module_name": "books_distributed",
                "expected_queue_name": "crawlo:books_distributed:queue:requests",
                "expected_processing_queue": "crawlo:books_distributed:queue:processing",
                "expected_failed_queue": "crawlo:books_distributed:queue:failed",
                "description": "标准项目名称"
            },
            {
                "queue_name": "crawlo:api_data_collection:queue:requests",
                "expected_module_name": "api_data_collection",
                "expected_queue_name": "crawlo:api_data_collection:queue:requests",
                "expected_processing_queue": "crawlo:api_data_collection:queue:processing",
                "expected_failed_queue": "crawlo:api_data_collection:queue:failed",
                "description": "API数据采集项目"
            },
            {
                "queue_name": "crawlo:test_project:queue:requests",
                "expected_module_name": "test_project",
                "expected_queue_name": "crawlo:test_project:queue:requests",
                "expected_processing_queue": "crawlo:test_project:queue:processing",
                "expected_failed_queue": "crawlo:test_project:queue:failed",
                "description": "测试项目"
            },
            {
                "queue_name": "simple_queue_name",
                "expected_module_name": "simple_queue_name",
                "expected_queue_name": "crawlo:simple_queue_name",  # RedisPriorityQueue会规范化名称
                "expected_processing_queue": "crawlo:simple_queue_name:processing",
                "expected_failed_queue": "crawlo:simple_queue_name:failed",
                "description": "简单队列名称"
            },
            {
                "queue_name": "",
                "expected_module_name": "default",
                "expected_queue_name": "crawlo:",  # 空字符串会规范化为"crawlo:"
                "expected_processing_queue": "crawlo::processing",
                "expected_failed_queue": "crawlo::failed",
                "description": "空队列名称"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"   {i}. 测试 {test_case['description']}...")
            
            # 创建QueueConfig
            config = QueueConfig(
                queue_type=QueueType.REDIS,
                redis_url="redis://127.0.0.1:6379/15",
                queue_name=test_case["queue_name"],
                max_queue_size=1000,
                max_retries=3,
                timeout=300
            )
            
            # 创建QueueManager
            queue_manager = QueueManager(config)
            
            # 创建队列实例
            queue = await queue_manager._create_queue(QueueType.REDIS)
            
            # 验证module_name是否正确设置
            assert hasattr(queue, 'module_name'), "RedisPriorityQueue缺少module_name属性"
            assert queue.module_name == test_case["expected_module_name"], \
                f"module_name不匹配: {queue.module_name} != {test_case['expected_module_name']}"
            
            # 验证队列名称是否符合规范
            assert queue.queue_name == test_case["expected_queue_name"], \
                f"队列名称不匹配: {queue.queue_name} != {test_case['expected_queue_name']}"
            assert queue.processing_queue == test_case["expected_processing_queue"], \
                f"处理中队列名称不匹配: {queue.processing_queue} != {test_case['expected_processing_queue']}"
            assert queue.failed_queue == test_case["expected_failed_queue"], \
                f"失败队列名称不匹配: {queue.failed_queue} != {test_case['expected_failed_queue']}"
            
            print(f"      module_name: {queue.module_name}")
            print(f"      队列名称: {queue.queue_name}")
            print(f"      处理中队列名称: {queue.processing_queue}")
            print(f"      失败队列名称: {queue.failed_queue}")
        
        print("QueueManager Redis key命名测试通过！")
        return True
        
    except Exception as e:
        print(f"QueueManager Redis key命名测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始QueueManager Redis key命名测试...")
    print("=" * 50)
    
    try:
        success = await test_queue_manager_redis_key()
        
        print("=" * 50)
        if success:
            print("所有测试通过！QueueManager正确传递module_name参数")
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