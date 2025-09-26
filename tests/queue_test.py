#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
队列系统测试脚本
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.request import Request
from crawlo.queue.queue_manager import QueueConfig, QueueManager


async def test_queue_system():
    """测试队列系统"""
    print("开始测试队列系统...")
    
    # 初始化框架
    from crawlo.initialization import initialize_framework
    settings = initialize_framework()
    
    # 创建一个小型队列配置进行测试
    settings.set('SCHEDULER_MAX_QUEUE_SIZE', 10)
    
    # 创建队列配置
    queue_config = QueueConfig.from_settings(settings)
    queue_config.max_queue_size = 10  # 设置小队列大小进行测试
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    
    # 初始化队列
    await queue_manager.initialize()
    
    print(f"队列类型: {queue_manager._queue_type}")
    print(f"队列最大大小: {queue_config.max_queue_size}")
    
    # 测试添加请求到队列
    print("测试添加请求到队列...")
    tasks = []
    for i in range(15):  # 尝试添加15个请求，超过队列大小
        request = Request(url=f'https://example.com/page{i}.html')
        task = asyncio.create_task(queue_manager.put(request))
        tasks.append(task)
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for result in results if result is True)
    print(f"成功添加 {success_count} 个请求到队列")
    
    queue_size = await queue_manager.size()
    print(f"队列当前大小: {queue_size}")
    
    # 测试从队列获取请求
    print("测试从队列获取请求...")
    retrieved_count = 0
    while retrieved_count < 15:
        try:
            request = await queue_manager.get(timeout=1.0)
            if request:
                print(f"成功获取请求: {request.url}")
                retrieved_count += 1
            else:
                break
        except Exception as e:
            print(f"获取请求失败: {e}")
            break
    
    print(f"总共获取了 {retrieved_count} 个请求")
    
    final_queue_size = await queue_manager.size()
    print(f"队列最终大小: {final_queue_size}")
    
    # 关闭队列
    await queue_manager.close()
    
    print("队列系统测试完成！")


def main():
    """主函数"""
    print("开始队列系统测试...")
    asyncio.run(test_queue_system())


if __name__ == "__main__":
    main()