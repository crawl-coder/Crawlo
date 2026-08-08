#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
队列命名测试脚本
用于验证Redis队列命名修复
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue


class MockRequest:
    def __init__(self, url):
        self.url = url
        self.priority = 0
        self.meta = {}


def test_queue_naming():
    """测试队列命名"""
    print("开始测试Redis队列命名...")
    print("=" * 50)
    
    # 测试用例
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
        
        # 创建RedisPriorityQueue实例
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/0",
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
            
        print()
    
    return all_passed


async def test_queue_operations():
    """测试队列操作"""
    print("开始测试Redis队列操作...")
    print("=" * 50)
    
    # 创建一个RedisPriorityQueue实例
    queue = RedisPriorityQueue(
        redis_url='redis://127.0.0.1:6379/0',
        queue_name='crawlo:test_project:queue:requests',
        module_name='test_project'
    )
    
    # 连接Redis
    await queue.connect()
    
    print('队列名称:', queue.queue_name)
    print('处理队列:', queue.processing_queue)
    print('失败队列:', queue.failed_queue)
    
    # 清理之前的测试数据
    await queue._redis.delete(queue.queue_name)
    await queue._redis.delete(f'{queue.queue_name}:data')
    await queue._redis.delete(queue.processing_queue)
    await queue._redis.delete(f'{queue.processing_queue}:data')
    await queue._redis.delete(queue.failed_queue)
    
    # 添加一个测试任务
    request = MockRequest('https://example.com')
    
    # 测试放入队列
    result = await queue.put(request, priority=1)
    print('放入队列结果:', result)
    
    # 检查队列大小
    size = await queue.qsize()
    print('队列大小:', size)
    
    # 测试获取任务
    retrieved = await queue.get(timeout=1.0)
    print('获取请求:', retrieved.url if retrieved else None)
    
    if retrieved:
        # 测试确认任务完成
        await queue.ack(retrieved)
        print('任务确认完成')
    
    # 关闭连接
    await queue.close()
    print("队列操作测试完成")


async def main():
    """主测试函数"""
    print("开始Redis队列命名和操作测试...")
    print("=" * 50)
    
    # 测试队列命名
    naming_test_passed = test_queue_naming()
    
    # 测试队列操作
    await test_queue_operations()
    
    print("=" * 50)
    if naming_test_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败！")
    print("测试完成！")


if __name__ == "__main__":
    asyncio.run(main())