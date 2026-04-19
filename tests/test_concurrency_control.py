#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
并发控制集成测试

测试 TaskManager 的并发控制机制：
- 并发限制
- 监控指标
- 动态调整
"""
import pytest
import asyncio
import time
from unittest.mock import MagicMock

from crawlo.task_manager import TaskManager


class TestConcurrencyControl:
    """测试并发控制"""
    
    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """测试并发数不超过限制"""
        concurrency = 4
        task_manager = TaskManager(total_concurrency=concurrency)
        
        max_concurrent = 0
        current_concurrent = 0
        
        async def sample_task():
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.1)
            current_concurrent -= 1
        
        # 创建 10 个任务
        tasks = []
        for _ in range(10):
            task = await task_manager.create_task(sample_task())
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 验证最大并发数不超过限制
        assert max_concurrent <= concurrency
    
    @pytest.mark.asyncio
    async def test_task_completion_tracking(self):
        """测试任务完成追踪"""
        task_manager = TaskManager(total_concurrency=4)
        
        async def quick_task():
            await asyncio.sleep(0.01)
        
        # 创建并完成任务
        for _ in range(5):
            await task_manager.create_task(quick_task())
            await asyncio.sleep(0.02)  # 等待任务完成
        
        # 验证所有任务已完成
        assert task_manager.all_done() is True
    
    @pytest.mark.asyncio
    async def test_task_done_callback(self):
        """测试任务完成回调"""
        task_manager = TaskManager(total_concurrency=4)
        
        completed_count = 0
        
        async def sample_task():
            nonlocal completed_count
            await asyncio.sleep(0.01)
            completed_count += 1
        
        # 创建多个任务
        tasks = []
        for _ in range(5):
            task = await task_manager.create_task(sample_task())
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)  # 等待回调执行
        
        # 验证所有任务都执行了
        assert completed_count == 5


class TestConcurrencyMonitoring:
    """测试并发监控"""
    
    @pytest.mark.asyncio
    async def test_stats_concurrency_limit(self):
        """测试统计中的并发限制"""
        concurrency = 8
        task_manager = TaskManager(total_concurrency=concurrency)
        
        stats = task_manager.get_stats()
        assert stats['concurrency_limit'] == concurrency
    
    @pytest.mark.asyncio
    async def test_stats_max_concurrent_seen(self):
        """测试峰值并发数统计"""
        concurrency = 4
        task_manager = TaskManager(total_concurrency=concurrency)
        
        async def slow_task():
            await asyncio.sleep(0.1)
        
        # 创建多个任务
        tasks = []
        for _ in range(6):
            task = await task_manager.create_task(slow_task())
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)
        
        stats = task_manager.get_stats()
        assert stats['max_concurrent_seen'] <= concurrency
        assert stats['max_concurrent_seen'] > 0
    
    @pytest.mark.asyncio
    async def test_stats_concurrency_utilization(self):
        """测试并发利用率计算"""
        concurrency = 4
        task_manager = TaskManager(total_concurrency=concurrency)
        
        async def sample_task():
            await asyncio.sleep(0.05)
        
        # 创建任务
        tasks = []
        for _ in range(4):
            task = await task_manager.create_task(sample_task())
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)
        
        stats = task_manager.get_stats()
        assert 'concurrency_utilization' in stats
        assert 0 <= stats['concurrency_utilization'] <= 100
    
    @pytest.mark.asyncio
    async def test_stats_response_time(self):
        """测试响应时间统计"""
        task_manager = TaskManager(total_concurrency=4)
        
        # 记录响应时间
        task_manager.record_response_time(1.5)
        task_manager.record_response_time(2.0)
        task_manager.record_response_time(1.0)
        
        async def sample_task():
            await asyncio.sleep(0.01)
        
        await task_manager.create_task(sample_task())
        await asyncio.sleep(0.05)
        
        stats = task_manager.get_stats()
        assert 'avg_response_time' in stats
        assert stats['avg_response_time'] > 0


class TestDynamicSemaphore:
    """测试动态信号量"""
    
    @pytest.mark.asyncio
    async def test_semaphore_acquire_release(self):
        """测试信号量获取和释放"""
        task_manager = TaskManager(total_concurrency=2)
        
        async def sample_task():
            await asyncio.sleep(0.05)
        
        # 创建 2 个任务（达到并发限制）
        task1 = await task_manager.create_task(sample_task())
        task2 = await task_manager.create_task(sample_task())
        
        # 信号量应该被占用
        assert task_manager.semaphore.current_value <= 2
        
        # 等待任务完成
        await asyncio.gather(task1, task2)
        await asyncio.sleep(0.1)
        
        # 信号量应该被释放
        assert task_manager.semaphore.current_value == 2
    
    @pytest.mark.asyncio
    async def test_semaphore_wait_when_full(self):
        """测试信号量满时等待"""
        task_manager = TaskManager(total_concurrency=1)
        
        start_time = time.time()
        
        async def slow_task():
            await asyncio.sleep(0.2)
        
        # 创建第一个任务
        task1 = await task_manager.create_task(slow_task())
        
        # 创建第二个任务（应该等待）
        task2 = await task_manager.create_task(slow_task())
        
        # 等待完成
        await asyncio.gather(task1, task2)
        
        elapsed = time.time() - start_time
        # 总时间应该 >= 0.4s（两个任务串行执行）
        assert elapsed >= 0.35


class TestTaskManagerEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_create_task_after_close(self):
        """测试关闭后创建任务"""
        task_manager = TaskManager(total_concurrency=4)
        task_manager._closed = True
        
        async def sample_task():
            await asyncio.sleep(0.01)
        
        # 应该抛出 RuntimeError
        with pytest.raises(RuntimeError, match="TaskManager is closed"):
            await task_manager.create_task(sample_task())
    
    @pytest.mark.asyncio
    async def test_all_done_empty(self):
        """测试空任务列表"""
        task_manager = TaskManager(total_concurrency=4)
        assert task_manager.all_done() is True
    
    @pytest.mark.asyncio
    async def test_stats_empty(self):
        """测试空统计"""
        task_manager = TaskManager(total_concurrency=4)
        stats = task_manager.get_stats()
        
        assert 'concurrency_limit' in stats
        assert 'max_concurrent_seen' in stats
        assert 'concurrency_utilization' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
