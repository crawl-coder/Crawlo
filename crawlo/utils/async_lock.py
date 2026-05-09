#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
异步锁工具模块
=============
提供线程安全的异步锁实现，替代 threading.Lock/RLock

问题背景：
在异步爬虫框架中使用 threading.Lock 或 threading.RLock 会导致：
1. 死锁风险: 当协程 A 持有线程锁并执行 await 时，协程 B 如果也需要该锁，会永久阻塞
2. 性能问题: 线程锁会阻塞整个线程，而非单个协程
3. 不可预测行为: 在高并发场景下可能出现竞态条件

解决方案：
提供 AsyncRLock（可重入）和 AsyncLock（不可重入），
使用 asyncio.Lock 替代 threading.Lock，支持协程级别的锁操作
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from collections import deque


class AsyncRLock:
    """
    异步可重入锁
    
    特性：
    - 支持同一协程多次获取（可重入）
    - 非阻塞协程切换
    - 死锁保护
    
    使用示例：
        lock = AsyncRLock()
        
        async def task():
            async with lock:
                # 临界区代码
                await do_something()
    
    或：
        lock = AsyncRLock()
        await lock.acquire()
        try:
            # 临界区代码
            await do_something()
        finally:
            lock.release()
    """
    
    def __init__(self):
        self._lock: asyncio.Lock = asyncio.Lock()
        self._owner: Optional[asyncio.Task] = None
        self._count: int = 0
        self._waiters: deque = deque()
    
    async def acquire(self) -> bool:
        """
        获取锁
        
        Returns:
            bool: 是否成功获取
        """
        current_task = asyncio.current_task()
        
        # 同一协程重入
        if current_task == self._owner:
            self._count += 1
            return True
        
        # 新协程获取锁
        await self._lock.acquire()
        self._owner = current_task
        self._count = 1
        return True
    
    def release(self) -> None:
        """
        释放锁
        
        Raises:
            RuntimeError: 如果尝试释放未持有的锁
        """
        if self._owner != asyncio.current_task():
            raise RuntimeError("Cannot release unheld lock")
        
        self._count -= 1
        if self._count == 0:
            self._owner = None
            self._lock.release()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.release()
        return False
    
    def locked(self) -> bool:
        """检查锁是否被持有"""
        return self._lock.locked()


class AsyncLock:
    """
    异步互斥锁（不可重入）
    
    特性：
    - 简单的互斥锁，不支持重入
    - 非阻塞协程切换
    
    使用示例：
        lock = AsyncLock()
        
        async def task():
            async with lock:
                await do_something()
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    @property
    def underlying_lock(self):
        """Expose underlying asyncio.Lock for interop"""
        return self._lock
    
    async def acquire(self) -> bool:
        """获取锁"""
        await self._lock.acquire()
        return True
    
    def release(self) -> None:
        """释放锁"""
        self._lock.release()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.release()
        return False
    
    def locked(self) -> bool:
        """检查锁是否被持有"""
        return self._lock.locked()


class AsyncSemaphore:
    """
    异步信号量
    
    特性：
    - 控制并发数量
    - 支持获取和释放
    
    使用示例：
        sem = AsyncSemaphore(3)  # 最多3个并发
        
        async def task():
            async with sem:
                await do_something()
    """
    
    def __init__(self, value: int = 1):
        """
        初始化信号量
        
        Args:
            value: 最大并发数
        """
        if value < 1:
            raise ValueError("Semaphore value must be >= 1")
        self._semaphore = asyncio.Semaphore(value)
    
    async def acquire(self) -> bool:
        """获取信号量"""
        await self._semaphore.acquire()
        return True
    
    def release(self) -> None:
        """释放信号量"""
        self._semaphore.release()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.release()
        return False
    
    @property
    def value(self) -> int:
        """获取当前可用信号量数量"""
        return self._semaphore._value


class AsyncEvent:
    """
    异步事件
    
    特性：
    - 支持等待和触发
    - 可重置
    
    使用示例：
        event = AsyncEvent()
        
        async def waiter():
            await event.wait()
            print("Event triggered!")
        
        async def setter():
            event.set()
    """
    
    def __init__(self):
        self._event = asyncio.Event()
    
    async def wait(self) -> None:
        """等待事件触发"""
        await self._event.wait()
    
    def set(self) -> None:
        """触发事件"""
        self._event.set()
    
    def clear(self) -> None:
        """清除事件（重置为未触发状态）"""
        self._event.clear()
    
    def is_set(self) -> bool:
        """检查事件是否已触发"""
        return self._event.is_set()


class AsyncCondition:
    """
    异步条件变量
    
    特性：
    - 支持等待直到条件满足
    - 支持通知
        
    使用示例：
        condition = AsyncCondition()
        
        async def waiter():
            async with condition:
                await condition.wait()
                print("Condition met!")
        
        async def notifier():
            async with condition:
                condition.notify()
    """
    
    def __init__(self, lock: AsyncLock = None):
        self._lock = lock or AsyncLock()
        # Use the underlying_lock property to maintain encapsulation
        self._condition = asyncio.Condition(self._lock.underlying_lock)
    
    async def wait(self) -> bool:
        """等待条件满足"""
        await self._condition.wait()
        return True
    
    def notify(self, n: int = 1) -> None:
        """通知等待者"""
        self._condition.notify(n)
    
    def notify_all(self) -> None:
        """通知所有等待者"""
        self._condition.notify_all()
    
    @asynccontextmanager
    async def __call__(self):
        """上下文管理器支持"""
        async with self._condition:
            yield
