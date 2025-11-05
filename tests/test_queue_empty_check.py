#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试队列空检查功能
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.pqueue import SpiderPriorityQueue


async def test_queue_empty_check():
    """测试队列空检查功能"""
    print("🚀 开始测试队列空检查功能...")
    
    # 创建队列实例
    queue = SpiderPriorityQueue()
    
    # 检查空队列
    print(f"空队列大小: {queue.qsize()}")
    print(f"空队列是否为空: {queue.qsize() == 0}")
    
    # 添加一个元素
    await queue.put((1, "test"))
    print(f"添加元素后队列大小: {queue.qsize()}")
    print(f"添加元素后队列是否为空: {queue.qsize() == 0}")
    
    # 获取元素
    item = await queue.get()
    print(f"获取元素: {item}")
    print(f"获取元素后队列大小: {queue.qsize()}")
    print(f"获取元素后队列是否为空: {queue.qsize() == 0}")
    
    print("✅ 队列空检查功能测试完成!")


if __name__ == '__main__':
    asyncio.run(test_queue_empty_check())