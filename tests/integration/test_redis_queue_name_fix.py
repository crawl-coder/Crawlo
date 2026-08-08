#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis队列名称修复测试脚本
用于验证RedisPriorityQueue中队列名称处理的修复
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入相关模块
from crawlo.queue.redis_priority_queue import RedisPriorityQueue


def test_normalize_queue_name():
    """测试队列名称规范化函数"""
    print("开始测试RedisPriorityQueue队列名称规范化...")
    print("=" * 50)
    
    # 创建一个RedisPriorityQueue实例用于测试
    queue = RedisPriorityQueue(redis_url="redis://127.0.0.1:6379/15")
    
    test_cases = [
        {
            "name": "已经规范化的名称",
            "input": "crawlo:test_project:queue:requests",
            "expected": "crawlo:test_project:queue:requests"
        },
        {
            "name": "双重 crawlo 前缀",
            "input": "crawlo:crawlo:queue:requests",
            "expected": "crawlo:queue:requests"
        },
        {
            "name": "三重 crawlo 前缀",
            "input": "crawlo:crawlo:crawlo:queue:requests",
            "expected": "crawlo:queue:requests"
        },
        {
            "name": "无 crawlo 前缀",
            "input": "test_project:queue:requests",
            "expected": "crawlo:test_project:queue:requests"
        },
        {
            "name": "空队列名称",
            "input": "",
            "expected": "crawlo:requests"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"  输入: {test_case['input']}")
        
        # 测试规范化函数
        result = queue._normalize_queue_name(test_case['input'])
        print(f"  输出: {result}")
        print(f"  期望: {test_case['expected']}")
        
        # 验证结果
        if result == test_case['expected']:
            print("  ✓ 测试通过")
        else:
            print("  ✗ 测试失败")
            all_passed = False
            
        print()
    
    print("=" * 50)
    if all_passed:
        print("所有测试通过！队列名称规范化修复成功")
        return True
    else:
        print("部分测试失败，请检查实现")
        return False


def test_queue_initialization():
    """测试队列初始化时的名称处理"""
    print("开始测试RedisPriorityQueue初始化时的名称处理...")
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
            "expected_queue": "crawlo:queue:requests",
            "expected_processing": "crawlo:queue:processing",
            "expected_failed": "crawlo:queue:failed"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        print(f"  输入队列名称: {test_case['queue_name']}")
        
        try:
            # 创建RedisPriorityQueue实例
            queue = RedisPriorityQueue(
                redis_url="redis://127.0.0.1:6379/15",
                queue_name=test_case['queue_name'],
                module_name="test_project"
            )
            
            print(f"  实际队列名称: {queue.queue_name}")
            print(f"  实际处理队列: {queue.processing_queue}")
            print(f"  实际失败队列: {queue.failed_queue}")
            
            print(f"  期望队列名称: {test_case['expected_queue']}")
            print(f"  期望处理队列: {test_case['expected_processing']}")
            print(f"  期望失败队列: {test_case['expected_failed']}")
            
            # 验证结果
            queue_name_ok = queue.queue_name == test_case['expected_queue']
            processing_queue_ok = queue.processing_queue == test_case['expected_processing']
            failed_queue_ok = queue.failed_queue == test_case['expected_failed']
            
            if queue_name_ok and processing_queue_ok and failed_queue_ok:
                print("  ✓ 测试通过")
            else:
                print("  ✗ 测试失败")
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ 测试异常: {e}")
            all_passed = False
            
        print()
    
    print("=" * 50)
    if all_passed:
        print("队列初始化测试通过！")
        return True
    else:
        print("队列初始化测试失败！")
        return False


def main():
    """主测试函数"""
    print("开始Redis队列名称修复测试...")
    print("=" * 50)
    
    # 测试队列名称规范化函数
    normalize_test_passed = test_normalize_queue_name()
    print()
    
    # 测试队列初始化
    init_test_passed = test_queue_initialization()
    print()
    
    print("=" * 50)
    if normalize_test_passed and init_test_passed:
        print("所有测试通过！Redis队列名称修复完成")
        return 0
    else:
        print("部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)