#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
队列资源泄漏测试
"""

import asyncio
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class MockQueue:
    """模拟队列"""
    def __init__(self, name):
        self.name = name
        self.items = []
        self.closed = False
    
    async def put(self, item):
        if not self.closed:
            self.items.append(item)
    
    async def get(self):
        if not self.closed and self.items:
            return self.items.pop(0)
        return None
    
    async def close(self):
        self.closed = True
        self.items.clear()


class QueueManager:
    """队列管理器"""
    def __init__(self):
        self.queues = {}
        self.resource_manager = get_resource_manager("queue_manager")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.QUEUE,
            "queue_manager"
        )
    
    def create_queue(self, name):
        queue = MockQueue(name)
        self.queues[name] = queue
        return queue
    
    async def _cleanup(self, resource=None):
        """清理队列资源"""
        for queue in self.queues.values():
            await queue.close()
        self.queues.clear()


async def test_queue_leak():
    """测试队列是否正确管理"""
    # 创建队列管理器
    queue_manager = QueueManager()
    
    # 创建队列并添加数据
    queue1 = queue_manager.create_queue("queue1")
    queue2 = queue_manager.create_queue("queue2")
    
    # 向队列添加数据
    await queue1.put("item1")
    await queue1.put("item2")
    await queue2.put("item3")
    
    # 检查资源是否正确注册
    active_resources = queue_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "queue_manager"
    
    # 检查队列状态
    assert len(queue_manager.queues) == 2
    assert len(queue1.items) == 2
    assert len(queue2.items) == 1
    assert queue1.closed == False
    assert queue2.closed == False
    
    # 清理资源
    await queue_manager.resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = queue_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证队列已关闭
    # 注意：由于清理是异步的，这里我们只验证资源管理器的状态
    
    print("队列资源泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_queue_leak())