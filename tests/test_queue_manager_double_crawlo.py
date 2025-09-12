#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
队列管理器双重 crawlo 前缀问题测试脚本
用于验证队列管理器在处理双重 crawlo 前缀时的行为
"""
import sys
import os
import asyncio
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


async def test_queue_manager_naming():
    """测试队列管理器中的项目名称提取"""
    print("🚀 开始测试队列管理器项目名称提取...")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "正常命名",
            "queue_name": "crawlo:test_project:queue:requests",
            "expected_module": "test_project"
        },
        {
            "name": "双重 crawlo 前缀",
            "queue_name": "crawlo:crawlo:queue:requests",
            "expected_module": "queue"  # 第三个部分是项目名称
        },
        {
            "name": "三重 crawlo 前缀",
            "queue_name": "crawlo:crawlo:crawlo:queue:requests",
            "expected_module": "crawlo"  # 第三个部分是项目名称
        },
        {
            "name": "无 crawlo 前缀",
            "queue_name": "test_project:queue:requests",
            "expected_module": "test_project"
        }
    ]
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            print(f"测试 {i}: {test_case['name']}")
            print(f"  输入队列名称: {test_case['queue_name']}")
            
            # 使用优化后的项目名称提取逻辑
            project_name = "default"
            if ':' in test_case['queue_name']:
                parts = test_case['queue_name'].split(':')
                # 跳过所有"crawlo"前缀，取第一个非"crawlo"部分作为项目名称
                for part in parts:
                    if part != "crawlo":
                        project_name = part
                        break
            else:
                project_name = test_case['queue_name'] or "default"
            
            print(f"  提取的项目名称: {project_name}")
            print(f"  期望的项目名称: {test_case['expected_module']}")
            
            # 验证结果
            assert project_name == test_case['expected_module'], \
                f"项目名称不匹配: {project_name} != {test_case['expected_module']}"
            
            print("  ✅ 测试通过")
            print()
        
        print("✅ 队列管理器项目名称提取测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 队列管理器项目名称提取测试失败: {e}")
        traceback.print_exc()
        return False


async def test_queue_manager_create_queue():
    """测试队列管理器创建队列"""
    print("🚀 开始测试队列管理器创建队列...")
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
            "expected_queue": "crawlo:crawlo:queue:requests",
            "expected_processing": "crawlo:crawlo:queue:processing",
            "expected_failed": "crawlo:crawlo:queue:failed"
        }
    ]
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            print(f"测试 {i}: {test_case['name']}")
            print(f"  输入队列名称: {test_case['queue_name']}")
            
            try:
                # 创建队列配置
                config = QueueConfig(
                    queue_type=QueueType.REDIS,
                    redis_url="redis://127.0.0.1:6379/15",
                    queue_name=test_case['queue_name'],
                    max_queue_size=1000,
                    max_retries=3,
                    timeout=300
                )
                
                # 创建队列管理器
                queue_manager = QueueManager(config)
                
                # 使用优化后的项目名称提取逻辑
                project_name = "default"
                if ':' in test_case['queue_name']:
                    parts = test_case['queue_name'].split(':')
                    # 跳过所有"crawlo"前缀，取第一个非"crawlo"部分作为项目名称
                    for part in parts:
                        if part != "crawlo":
                            project_name = part
                            break
                else:
                    project_name = test_case['queue_name'] or "default"
                
                print(f"  提取的项目名称: {project_name}")
                
                # 创建 Redis 队列实例
                from crawlo.queue.redis_priority_queue import RedisPriorityQueue
                queue = RedisPriorityQueue(
                    redis_url=config.redis_url,
                    queue_name=config.queue_name,
                    max_retries=config.max_retries,
                    timeout=config.timeout,
                    module_name=project_name  # 传递项目名称作为module_name
                )
                
                print(f"  创建的队列名称: {queue.queue_name}")
                print(f"  创建的处理队列: {queue.processing_queue}")
                print(f"  创建的失败队列: {queue.failed_queue}")
                
                # 验证结果
                assert queue.queue_name == test_case['expected_queue'], \
                    f"队列名称不匹配: {queue.queue_name} != {test_case['expected_queue']}"
                assert queue.processing_queue == test_case['expected_processing'], \
                    f"处理队列名称不匹配: {queue.processing_queue} != {test_case['expected_processing']}"
                assert queue.failed_queue == test_case['expected_failed'], \
                    f"失败队列名称不匹配: {queue.failed_queue} != {test_case['expected_failed']}"
                
                print("  ✅ 测试通过")
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                traceback.print_exc()
                return False
            
            print()
        
        print("✅ 队列管理器创建队列测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 队列管理器创建队列测试失败: {e}")
        traceback.print_exc()
        return False