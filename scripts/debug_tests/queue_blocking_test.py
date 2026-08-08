#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
队列阻塞行为测试脚本
验证队列满时的阻塞行为
"""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.request import Request
from crawlo.queue.queue_manager import QueueConfig, QueueManager


async def test_queue_blocking_behavior():
    """测试队列阻塞行为"""
    print("开始测试队列阻塞行为...")
    
    # 初始化框架
    from crawlo.initialization import initialize_framework
    settings = initialize_framework()
    
    # 创建一个小型队列配置进行测试
    settings.set('SCHEDULER_MAX_QUEUE_SIZE', 5)  # 设置非常小的队列大小
    
    # 创建队列配置
    queue_config = QueueConfig.from_settings(settings)
    queue_config.max_queue_size = 5  # 设置小队列大小进行测试
    
    # 创建队列管理器
    queue_manager = QueueManager(queue_config)
    
    # 初始化队列
    await queue_manager.initialize()
    
    print(f"队列类型: {queue_manager._queue_type}")
    print(f"队列最大大小: {queue_config.max_queue_size}")
    
    # 创建生产者任务
    async def producer(queue_manager, name, count):
        """生产者：向队列添加请求"""
        print(f"生产者 {name} 开始工作，将添加 {count} 个请求")
        start_time = time.time()
        
        for i in range(count):
            request = Request(url=f'https://example.com/page{name}_{i}.html')
            try:
                # 这里应该会阻塞当队列满时
                await queue_manager.put(request)
                print(f"生产者 {name} 成功添加请求 {i}")
            except Exception as e:
                print(f"生产者 {name} 添加请求 {i} 失败: {e}")
        
        end_time = time.time()
        print(f"生产者 {name} 完成工作，耗时 {end_time - start_time:.2f} 秒")
    
    # 创建消费者任务
    async def consumer(queue_manager, name, count):
        """消费者：从队列获取请求"""
        print(f"消费者 {name} 开始工作，将获取 {count} 个请求")
        start_time = time.time()
        
        retrieved_count = 0
        while retrieved_count < count:
            try:
                request = await queue_manager.get(timeout=2.0)
                if request:
                    print(f"消费者 {name} 成功获取请求: {request.url}")
                    retrieved_count += 1
                    # 模拟处理时间
                    await asyncio.sleep(0.1)
                else:
                    print(f"消费者 {name} 超时，没有获取到请求")
                    break
            except Exception as e:
                print(f"消费者 {name} 获取请求失败: {e}")
                break
        
        end_time = time.time()
        print(f"消费者 {name} 完成工作，获取了 {retrieved_count} 个请求，耗时 {end_time - start_time:.2f} 秒")
    
    # 同时运行生产者和消费者
    print("开始并发测试...")
    
    # 生产者尝试添加10个请求到大小为5的队列
    # 消费者会逐渐消费，生产者应该会被阻塞直到有空间
    tasks = [
        asyncio.create_task(producer(queue_manager, "P1", 10)),
        asyncio.create_task(consumer(queue_manager, "C1", 10))
    ]
    
    # 等待所有任务完成
    await asyncio.gather(*tasks, return_exceptions=True)
    
    final_queue_size = await queue_manager.size()
    print(f"队列最终大小: {final_queue_size}")
    
    # 关闭队列
    await queue_manager.close()
    
    print("队列阻塞行为测试完成！")


def main():
    """主函数"""
    print("开始队列阻塞行为测试...")
    asyncio.run(test_queue_blocking_behavior())


if __name__ == "__main__":
    main()