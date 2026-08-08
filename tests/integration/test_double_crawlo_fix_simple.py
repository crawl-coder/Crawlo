#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双重 crawlo 前缀问题修复简单测试脚本
用于验证 Redis 队列名称中双重 crawlo 前缀问题的修复，不依赖于实际的 Redis 连接
"""
import sys
import os
import asyncio
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.queue.redis_priority_queue import RedisPriorityQueue


def test_redis_queue_naming():
    """测试 Redis 队列命名修复"""
    print("开始测试 Redis 队列命名修复...")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "正常命名",
            "queue_name": "crawlo:test_project:queue:requests",
            "expected_queue": "crawlo:test_project:queue:requests",
            "expected_processing": "crawlo:test_project:queue:processing",
            "expected_failed": "crawlo:test_project:queue:failed"
        },
        {
            "name": "双重 crawlo 前缀",
            "queue_name": "crawlo:crawlo:queue:requests",
            "expected_queue": "crawlo:crawlo:queue:requests",  # 保持原始名称不变
            "expected_processing": "crawlo:crawlo:queue:processing",  # 保持一致的双重前缀
            "expected_failed": "crawlo:crawlo:queue:failed"
        },
        {
            "name": "三重 crawlo 前缀",
            "queue_name": "crawlo:crawlo:crawlo:queue:requests",
            "expected_queue": "crawlo:crawlo:crawlo:queue:requests",  # 保持原始名称不变
            "expected_processing": "crawlo:crawlo:crawlo:queue:processing",  # 保持一致的前缀
            "expected_failed": "crawlo:crawlo:crawlo:queue:failed"
        },
        {
            "name": "无 crawlo 前缀",
            "queue_name": "test_project:queue:requests",
            "expected_queue": "test_project:queue:requests",  # 保持原始名称不变
            "expected_processing": "test_project:queue:processing",
            "expected_failed": "test_project:queue:failed"
        }
    ]
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            print(f"测试 {i}: {test_case['name']}")
            print(f"  输入队列名称: {test_case['queue_name']}")
            
            # 测试 RedisPriorityQueue 初始化
            try:
                queue = RedisPriorityQueue(
                    redis_url="redis://127.0.0.1:6379/15",
                    queue_name=test_case['queue_name'],
                    module_name="test_project"
                )
                
                print(f"  修复后队列名称: {queue.queue_name}")
                print(f"  修复后处理队列: {queue.processing_queue}")
                print(f"  修复后失败队列: {queue.failed_queue}")
                
                # 验证结果
                assert queue.queue_name == test_case['expected_queue'], \
                    f"队列名称不匹配: {queue.queue_name} != {test_case['expected_queue']}"
                assert queue.processing_queue == test_case['expected_processing'], \
                    f"处理队列名称不匹配: {queue.processing_queue} != {test_case['expected_processing']}"
                assert queue.failed_queue == test_case['expected_failed'], \
                    f"失败队列名称不匹配: {queue.failed_queue} != {test_case['expected_failed']}"
                
                print("  测试通过")
            except Exception as e:
                print(f"  测试失败: {e}")
                traceback.print_exc()
                return False
            
            print()
        
        print("Redis 队列命名修复测试通过！")
        return True
        
    except Exception as e:
        print(f"Redis 队列命名修复测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始双重 crawlo 前缀问题修复测试...")
    print("=" * 50)
    
    try:
        # 测试 Redis 队列命名修复
        redis_test_success = test_redis_queue_naming()
        print()
        
        print("=" * 50)
        if redis_test_success:
            print("Redis 队列命名修复测试通过！双重 crawlo 前缀问题已修复")
        else:
            print("Redis 队列命名修复测试失败，请检查实现")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"测试过程中发生异常: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)