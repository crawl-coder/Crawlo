#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
异步锁测试
"""
import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.utils.async_lock import AsyncRLock, AsyncLock, AsyncSemaphore


class TestAsyncRLock:
    """测试异步可重入锁"""
    
    @pytest.mark.asyncio
    async def test_basic_lock_unlock(self):
        """测试基本获取和释放"""
        lock = AsyncRLock()
        
        assert not lock.locked()
        await lock.acquire()
        assert lock.locked()
        lock.release()
        assert not lock.locked()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        lock = AsyncRLock()
        result = []
        
        async def task():
            async with lock:
                result.append("inside")
        
        await task()
        assert result == ["inside"]
    
    @pytest.mark.asyncio
    async def test_reentrant(self):
        """测试可重入"""
        lock = AsyncRLock()
        results = []
        
        async def outer():
            async with lock:
                results.append("outer_start")
                await inner()
                results.append("outer_end")
        
        async def inner():
            async with lock:  # 重入应该成功
                results.append("inner")
        
        await outer()
        assert results == ["outer_start", "inner", "outer_end"]
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """测试并发访问"""
        lock = AsyncRLock()
        counter = 0
        
        async def increment():
            nonlocal counter
            for _ in range(100):
                async with lock:
                    counter += 1
        
        await asyncio.gather(*[increment() for _ in range(10)])
        
        assert counter == 1000, f"Expected 1000, got {counter}"
    
    @pytest.mark.asyncio
    async def test_release_error(self):
        """测试释放未持有锁的错误"""
        lock = AsyncRLock()
        
        with pytest.raises(RuntimeError, match="Cannot release unheld lock"):
            lock.release()


class TestAsyncLock:
    """测试异步互斥锁"""
    
    @pytest.mark.asyncio
    async def test_basic_lock(self):
        """测试基本获取和释放"""
        lock = AsyncLock()
        
        await lock.acquire()
        assert lock.locked()
        lock.release()
        assert not lock.locked()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        lock = AsyncLock()
        result = []
        
        async def task():
            async with lock:
                result.append("done")
        
        await task()
        assert result == ["done"]
    
    @pytest.mark.asyncio
    async def test_concurrent_exclusion(self):
        """测试互斥"""
        lock = AsyncLock()
        order = []
        
        async def task1():
            async with lock:
                order.append(1)
                await asyncio.sleep(0.01)
                order.append(2)
        
        async def task2():
            await asyncio.sleep(0.005)
            async with lock:
                order.append(3)
        
        await asyncio.gather(task1(), task2())
        
        # task2 应该在 task1 完成后才能获取锁
        assert order.index(3) > order.index(2)


class TestAsyncSemaphore:
    """测试异步信号量"""
    
    @pytest.mark.asyncio
    async def test_basic_semaphore(self):
        """测试基本信号量"""
        sem = AsyncSemaphore(2)
        
        assert sem.value == 2
        
        await sem.acquire()
        assert sem.value == 1
        
        await sem.acquire()
        assert sem.value == 0
        
        sem.release()
        assert sem.value == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """测试并发限制"""
        sem = AsyncSemaphore(3)
        active = []
        max_active = []
        
        async def worker(id):
            async with sem:
                active.append(id)
                max_active.append(len(active))
                await asyncio.sleep(0.01)
                active.remove(id)
        
        await asyncio.gather(*[worker(i) for i in range(10)])
        
        # 最大并发数不应超过信号量值
        assert max(max_active) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
