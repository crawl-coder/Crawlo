#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
任务管理器
==========
管理 Crawlo 框架的异步任务，提供并发控制和动态调频功能。

核心特性：
1. 动态信号量：根据响应时间自动调整并发数
2. 任务超时：支持单任务超时控制
3. 优雅关闭：支持等待任务完成或强制取消
4. 统计监控：提供详细的任务执行统计

使用示例：
    from crawlo.task_manager import TaskManager
    
    # 创建管理器（初始并发数 8）
    tm = TaskManager(total_concurrency=8)
    
    # 创建任务（带超时）
    task = await tm.create_task(coroutine(), timeout=30.0)
    
    # 记录响应时间（用于动态调频）
    tm.record_response_time(0.15)
    
    # 优雅关闭
    await tm.close(timeout=30.0)
"""
import time
import asyncio
from typing import Set, Final, Optional, TypeVar, Generic, Dict, Any
from collections import deque
from asyncio import Task, Future, Semaphore
from dataclasses import dataclass, field

from crawlo.utils.py314_compat import get_task_info
from crawlo.logging import get_logger


T = TypeVar('T')


@dataclass
class TaskStats:
    """任务统计信息"""
    active_tasks: int = 0
    total_tasks: int = 0
    exception_count: int = 0
    cancelled_count: int = 0
    timeout_count: int = 0
    current_concurrency: int = 0
    avg_response_time: float = 0.0
    tasks_per_second: float = 0.0
    _start_time: Optional[float] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        success_count = self.total_tasks - self.exception_count - self.cancelled_count - self.timeout_count
        success_rate = (success_count / max(1, self.total_tasks)) * 100
        
        return {
            'active_tasks': self.active_tasks,
            'total_tasks': self.total_tasks,
            'exception_count': self.exception_count,
            'cancelled_count': self.cancelled_count,
            'timeout_count': self.timeout_count,
            'success_rate': round(success_rate, 2),
            'current_concurrency': self.current_concurrency,
            'avg_response_time': round(self.avg_response_time, 3),
            'tasks_per_second': round(self.tasks_per_second, 2),
        }


class DynamicSemaphore:
    """
    支持动态调整的信号量
    
    根据响应时间自动调整并发数：
    - 响应快 (< 0.2s)：增加并发 (+5，最大 3 倍初始值)
    - 响应慢 (> 1.0s)：减少并发 (-5，最小 1/3 初始值或 1)
    """
    
    def __init__(self, initial_value: int = 8):
        super().__init__()
        self._initial_value = max(1, initial_value)
        self._current_value = self._initial_value
        self._target_value = self._initial_value  # 目标并发数
        self._active_count = 0  # 当前活跃任务数
        self._response_times: deque[float] = deque(maxlen=10)
        self._last_adjust_time = time.time()
        self._lock = asyncio.Lock()
        self._waiters: asyncio.Queue = asyncio.Queue()
        
    async def acquire(self) -> bool:
        """获取信号量，支持动态调整"""
        async with self._lock:
            # 如果当前活跃数 < 目标值，直接获取
            if self._active_count < self._target_value:
                self._active_count += 1
                return True
        
        # 否则等待
        event = asyncio.Event()
        await self._waiters.put(event)
        await event.wait()
        return True
    
    def release(self) -> None:
        """释放信号量
        
        注意：此方法在 done_callback 中调用（同步回调），在 asyncio
        单线程事件循环中是安全的。唤醒逻辑统一使用 _wake_waiters()。
        """
        self._active_count = max(0, self._active_count - 1)
        self._wake_waiters()
    
    def _wake_waiters(self) -> None:
        """安全唤醒等待者
        
        统一的唤醒逻辑，被 release() 和 _adjust_semaphore_value() 共用。
        在 asyncio 单线程模型中，此方法是安全的，因为：
        1. release() 在 done_callback 中调用（事件循环内）
        2. _adjust_semaphore_value() 在 asyncio.Lock 保护下调用
        3. 两者不会同时执行
        """
        try:
            while not self._waiters.empty() and self._active_count < self._target_value:
                event = self._waiters.get_nowait()
                self._active_count += 1
                event.set()
        except asyncio.QueueEmpty:
            pass
        
    def record_response_time(self, response_time: float) -> None:
        """记录响应时间"""
        self._response_times.append(response_time)
        
    async def adjust_concurrency(self) -> None:
        """根据响应时间动态调整并发数"""
        async with self._lock:
            current_time = time.time()
            # 限制调整频率，至少间隔 1 秒
            if current_time - self._last_adjust_time < 1:
                return
                
            self._last_adjust_time = current_time
            
            if len(self._response_times) < 2:
                return
                
            # 计算平均响应时间
            avg_response_time = sum(self._response_times) / len(self._response_times)
            
            # 根据响应时间调整并发数
            if avg_response_time < 0.2:  # 响应很快，增加并发
                new_concurrency = min(
                    self._current_value + 5, 
                    self._initial_value * 3
                )
            elif avg_response_time > 1.0:  # 响应较慢，减少并发
                new_concurrency = max(
                    self._current_value - 5, 
                    max(1, self._initial_value // 3)
                )
            else:
                return  # 保持当前并发数
                
            # 只有当变化较大时才调整
            if abs(new_concurrency - self._current_value) > 1:
                await self._adjust_semaphore_value(new_concurrency)
    
    async def _adjust_semaphore_value(self, new_value: int) -> None:
        """调整信号量的值"""
        old_value = self._current_value
        self._current_value = new_value
        self._target_value = new_value
        
        # 如果新值更大，唤醒等待的任务
        if new_value > old_value:
            self._wake_waiters()
    
    @property
    def current_value(self) -> int:
        """当前并发数"""
        return self._current_value
    
    @property
    def active_count(self) -> int:
        """当前活跃任务数"""
        return self._active_count


class TaskManager(Generic[T]):
    """
    任务管理器
    
    统一管理异步任务的创建、执行和监控。
    """

    def __init__(self, total_concurrency: int = 8):
        self.current_task: Final[Set[Task[T]]] = set()
        self.semaphore: DynamicSemaphore = DynamicSemaphore(total_concurrency)
        self.logger = get_logger(self.__class__.__name__)
        self._stats = TaskStats()
        self._stats._start_time = time.time()
        self._closed = False
        
        # 并发监控
        self._max_concurrent_seen = 0  # 峰值并发数
        self._concurrency_limit = total_concurrency  # 并发限制
        
        # 全部任务完成事件（替代忙轮询）
        self._all_done_event = asyncio.Event()
        
    async def create_task(
        self, 
        coroutine, 
        timeout: Optional[float] = None
    ) -> Task[T]:
        """
        创建受控的异步任务
        
        Args:
            coroutine: 协程对象
            timeout: 任务超时时间（秒），None 表示不超时
            
        Returns:
            Task 对象
            
        Raises:
            RuntimeError: 如果 TaskManager 已关闭
        """
        if self._closed:
            raise RuntimeError("TaskManager is closed")
            
        # 等待信号量，控制并发数
        await self.semaphore.acquire()
        
        # 如果设置了超时，包装协程
        if timeout is not None:
            coroutine = self._wrap_with_timeout(coroutine, timeout)
        
        task = asyncio.create_task(coroutine)
        # 首次添加任务时清除完成事件
        if not self.current_task:
            self._all_done_event.clear()
        self.current_task.add(task)
        self._stats.active_tasks = len(self.current_task)
        self._stats.total_tasks += 1
        
        # 更新峰值并发数
        self._max_concurrent_seen = max(self._max_concurrent_seen, self._stats.active_tasks)

        def done_callback(_future: Future[T]) -> None:
            try:
                self.current_task.discard(task)
                self._stats.active_tasks = len(self.current_task)
                
                # 所有任务完成时通知等待者
                if not self.current_task:
                    self._all_done_event.set()
                
                # 获取任务结果或异常
                try:
                    result = _future.result()
                except asyncio.TimeoutError:
                    self._stats.timeout_count += 1
                    self.logger.warning(f"Task timed out after {timeout}s")
                except asyncio.CancelledError:
                    self._stats.cancelled_count += 1
                    # 只打印一次，避免重复
                    if not getattr(self, '_cancel_logged', False):
                        self.logger.info("Task was cancelled")
                        self._cancel_logged = True
                except Exception as exception:
                    self._stats.exception_count += 1
                    task_info = get_task_info(task)
                    self.logger.error(
                        f"Task completed with exception: {type(exception).__name__}: {exception} | "
                        f"Task: {task_info['name']}, active: {task_info.get('coroutine', 'N/A')}"
                    )
                    self.logger.debug("Task exception details:", exc_info=exception)
                    
            except Exception as e:
                # 防止回调函数本身出现异常
                self.logger.error(f"Error in task done callback: {e}")
            finally:
                # 确保信号量始终被释放
                self.semaphore.release()
                
                # 定期调整并发数
                if self._stats.total_tasks % 2 == 0:
                    asyncio.create_task(self.semaphore.adjust_concurrency())

        task.add_done_callback(done_callback)
        return task
    
    async def _wrap_with_timeout(self, coroutine, timeout: float):
        """包装协程添加超时控制，超时后取消内部协程防止资源泄漏"""
        task = asyncio.ensure_future(coroutine)
        try:
            async with asyncio.timeout(timeout):
                return await task
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise

    def all_done(self) -> bool:
        """检查所有任务是否完成"""
        return len(self.current_task) == 0
    
    def record_response_time(self, response_time: float) -> None:
        """
        记录任务的响应时间，用于动态调整并发数
        
        Args:
            response_time: 响应时间（秒）
        """
        self.semaphore.record_response_time(response_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取任务管理器统计信息
        
        Returns:
            统计信息字典
        """
        # 计算平均响应时间
        if self.semaphore._response_times:
            self._stats.avg_response_time = (
                sum(self.semaphore._response_times) / len(self.semaphore._response_times)
            )
        
        # 计算每秒任务数
        if self._stats._start_time:
            elapsed = time.time() - self._stats._start_time
            self._stats.tasks_per_second = self._stats.total_tasks / max(1, elapsed)
        
        self._stats.current_concurrency = self.semaphore.current_value
        
        # 构建完整的统计信息
        stats = self._stats.to_dict()
        stats.update({
            'concurrency_limit': self._concurrency_limit,
            'max_concurrent_seen': self._max_concurrent_seen,
            'concurrency_utilization': round(
                self._max_concurrent_seen / max(1, self._concurrency_limit) * 100, 2
            ),
        })
        return stats
    
    async def close(self, timeout: float = 30.0, cancel_pending: bool = False) -> None:
        """
        优雅关闭 TaskManager
        
        Args:
            timeout: 等待任务完成的最大时间（秒）
            cancel_pending: 是否取消未完成的任务（默认 False，等待完成）
            
        Raises:
            TimeoutError: 如果等待超时且 cancel_pending=False
        """
        if self._closed:
            return
            
        self._closed = True
        
        if not self.current_task:
            self.logger.info("No active tasks, closing immediately")
            return
        
        self.logger.info(f"Waiting for {len(self.current_task)} tasks to complete...")
        
        if cancel_pending:
            # 强制取消所有任务
            for task in list(self.current_task):
                task.cancel()
            # 等待取消完成
            if self.current_task:
                await asyncio.gather(*self.current_task, return_exceptions=True)
        else:
            # 等待任务完成
            try:
                async with asyncio.timeout(timeout):
                    await self._wait_all_done()
                self.logger.info("All tasks completed gracefully")
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout waiting for tasks ({timeout}s), cancelling remaining...")
                for task in list(self.current_task):
                    task.cancel()
                if self.current_task:
                    await asyncio.gather(*self.current_task, return_exceptions=True)
    
    async def _wait_all_done(self) -> None:
        """等待所有任务完成（通过 Event 避免忙轮询）"""
        await self._all_done_event.wait()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if not self._closed:
            # 同步上下文需要异步关闭，这里只标记
            self.logger.warning("Use 'async with' or manually call close() for proper cleanup")
        return False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        return False
