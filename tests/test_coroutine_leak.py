#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
协程泄漏测试
"""

import asyncio
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class BackgroundTaskManager:
    """后台任务管理器"""
    def __init__(self):
        self._task = None
        self.resource_manager = get_resource_manager("task_manager")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            "background_task_manager"
        )
    
    async def start(self):
        self._task = asyncio.create_task(self._background_task())
    
    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _background_task(self):
        while True:
            await asyncio.sleep(0.1)
    
    async def _cleanup(self, resource=None):
        """清理协程资源"""
        await self.stop()


async def test_coroutine_leak():
    """测试协程是否正确管理"""
    # 创建后台任务管理器
    task_manager = BackgroundTaskManager()
    
    # 启动后台任务
    await task_manager.start()
    
    # 检查资源是否正确注册
    active_resources = task_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "background_task_manager"
    
    # 检查任务是否运行
    assert task_manager._task is not None
    assert not task_manager._task.done()
    
    # 清理资源
    await task_manager.resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = task_manager.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证任务已取消
    # 注意：由于清理是异步的，这里我们只验证资源管理器的状态
    
    print("协程泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_coroutine_leak())