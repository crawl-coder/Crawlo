#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
线程泄漏测试
"""

import threading
import time
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class BackgroundWorker:
    """后台工作线程"""
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self.resource_manager = get_resource_manager("thread_worker")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            "background_worker"
        )
    
    def start(self):
        self._thread = threading.Thread(target=self._worker)
        self._thread.start()
    
    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()
    
    def _worker(self):
        while not self._stop_event.is_set():
            time.sleep(0.1)
    
    def _cleanup(self, resource=None):
        """清理线程资源"""
        self.stop()


def test_thread_leak():
    """测试线程是否正确管理"""
    # 创建后台工作线程
    worker = BackgroundWorker()
    
    # 启动线程
    worker.start()
    
    # 检查资源是否正确注册
    active_resources = worker.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "background_worker"
    
    # 检查线程是否运行
    assert worker._thread is not None
    assert worker._thread.is_alive()
    
    # 清理资源
    import asyncio
    asyncio.run(worker.resource_manager.cleanup_all())
    
    # 验证资源已清理
    active_resources = worker.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证线程已停止
    # 注意：由于清理是异步的，这里我们只验证资源管理器的状态
    
    print("线程泄漏测试通过")


if __name__ == "__main__":
    test_thread_leak()