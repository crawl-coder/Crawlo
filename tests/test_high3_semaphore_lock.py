#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 HIGH-3: DynamicSemaphore 锁使用不一致的修复

验证点：
1. release() 和 _adjust_semaphore_value() 使用相同的 _wake_waiters() 逻辑
2. _wake_waiters() 方法存在且被两个方法调用
3. 信号量基本功能正常
"""
import asyncio
import inspect
import ast
import textwrap
import pytest


class TestDynamicSemaphoreConsistency:
    """测试 DynamicSemaphore 的锁一致性"""

    def test_wake_waiters_method_exists(self):
        """_wake_waiters() 方法存在"""
        from crawlo.task_manager import DynamicSemaphore
        assert hasattr(DynamicSemaphore, '_wake_waiters'), (
            "DynamicSemaphore should have _wake_waiters() method"
        )

    def test_release_calls_wake_waiters(self):
        """release() 调用 _wake_waiters()"""
        from crawlo.task_manager import DynamicSemaphore
        source = textwrap.dedent(inspect.getsource(DynamicSemaphore.release))
        assert '_wake_waiters' in source, (
            "release() should call _wake_waiters()"
        )

    def test_adjust_semaphore_value_calls_wake_waiters(self):
        """_adjust_semaphore_value() 调用 _wake_waiters()"""
        from crawlo.task_manager import DynamicSemaphore
        source = textwrap.dedent(inspect.getsource(DynamicSemaphore._adjust_semaphore_value))
        assert '_wake_waiters' in source, (
            "_adjust_semaphore_value() should call _wake_waiters()"
        )

    def test_no_duplicate_wake_logic_in_release(self):
        """release() 中不再有重复的唤醒逻辑"""
        from crawlo.task_manager import DynamicSemaphore
        source = textwrap.dedent(inspect.getsource(DynamicSemaphore.release))
        # 不应包含 while not self._waiters.empty() 的重复逻辑
        assert 'while not self._waiters' not in source, (
            "release() should not have inline wake logic, use _wake_waiters() instead"
        )

    def test_no_duplicate_wake_logic_in_adjust(self):
        """_adjust_semaphore_value() 中不再有重复的唤醒逻辑"""
        from crawlo.task_manager import DynamicSemaphore
        source = textwrap.dedent(inspect.getsource(DynamicSemaphore._adjust_semaphore_value))
        assert 'while not self._waiters' not in source, (
            "_adjust_semaphore_value() should not have inline wake logic, use _wake_waiters() instead"
        )


class TestDynamicSemaphoreFunctionality:
    """测试 DynamicSemaphore 基本功能"""

    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """基本的获取和释放"""
        from crawlo.task_manager import DynamicSemaphore
        sem = DynamicSemaphore(initial_value=2)
        
        assert sem.active_count == 0
        
        await sem.acquire()
        assert sem.active_count == 1
        
        await sem.acquire()
        assert sem.active_count == 2
        
        sem.release()
        assert sem.active_count == 1
        
        sem.release()
        assert sem.active_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """并发获取信号量"""
        from crawlo.task_manager import DynamicSemaphore
        sem = DynamicSemaphore(initial_value=3)
        
        acquired = []
        
        async def worker(worker_id):
            await sem.acquire()
            acquired.append(worker_id)
            await asyncio.sleep(0.01)
            sem.release()
        
        tasks = [asyncio.create_task(worker(i)) for i in range(5)]
        await asyncio.gather(*tasks)
        
        assert len(acquired) == 5
