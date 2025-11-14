#!/usr/bin/python
# -*- coding:UTF-8 -*-
import time
import asyncio
from typing import Set, Final
from collections import deque
from asyncio import Task, Future, Semaphore
from crawlo.logging import get_logger


class DynamicSemaphore(Semaphore):
    """支持动态调整的信号量"""
    
    def __init__(self, initial_value: int = 8):
        super().__init__(initial_value)
        self._initial_value = initial_value
        self._current_value = initial_value
        self._response_times = deque(maxlen=10)  # 存储最近10次响应时间
        self._last_adjust_time = time.time()
        
    def record_response_time(self, response_time: float):
        """记录响应时间"""
        self._response_times.append(response_time)
        
    def adjust_concurrency(self):
        """根据响应时间动态调整并发数"""
        current_time = time.time()
        # 限制调整频率，至少间隔1秒（从2秒减少到1秒）
        if current_time - self._last_adjust_time < 1:
            return
            
        self._last_adjust_time = current_time
        
        if len(self._response_times) < 2:  # 从3减少到2
            return
            
        # 计算平均响应时间
        avg_response_time = sum(self._response_times) / len(self._response_times)
        
        # 根据响应时间调整并发数
        if avg_response_time < 0.2:  # 响应很快，增加并发（从0.3降到0.2）
            new_concurrency = min(self._current_value + 5, self._initial_value * 3)  # 增加幅度从3提高到5，最大值从2倍提高到3倍
        elif avg_response_time > 1.0:  # 响应较慢，减少并发（从1.5降到1.0）
            new_concurrency = max(self._current_value - 5, max(1, self._initial_value // 3))  # 减少幅度从3提高到5，最小值从一半降低到三分之一
        else:
            return  # 保持当前并发数
            
        # 只有当变化较大时才调整
        if abs(new_concurrency - self._current_value) > 1:
            self._adjust_semaphore_value(new_concurrency)
    
    def _adjust_semaphore_value(self, new_value: int):
        """调整信号量的值"""
        if new_value > self._current_value:
            # 增加信号量
            for _ in range(new_value - self._current_value):
                self.release()
        elif new_value < self._current_value:
            # 减少信号量，这里只是记录新的目标值
            # 实际减少会在acquire时处理
            pass
            
        self._current_value = new_value
        # 注意：Python的Semaphore没有直接修改内部计数器的方法
        # 所以我们只能通过release()来增加，减少则需要在acquire时控制


class TaskManager:

    def __init__(self, total_concurrency: int = 8):
        self.current_task: Final[Set] = set()
        # 使用动态信号量替代普通信号量
        self.semaphore: DynamicSemaphore = DynamicSemaphore(max(1, total_concurrency))
        self.logger = get_logger(self.__class__.__name__)
        
        # 异常统计
        self._exception_count = 0
        self._total_tasks = 0

    async def create_task(self, coroutine) -> Task:
        # 等待信号量，控制并发数
        await self.semaphore.acquire()
        
        task = asyncio.create_task(coroutine)
        self.current_task.add(task)
        self._total_tasks += 1

        def done_callback(_future: Future) -> None:
            try:
                self.current_task.discard(task)  # 使用discard而不是remove，避免KeyError
                
                # 获取任务结果或异常 - 这是关键，必须调用result()或exception()来"获取"异常
                try:
                    # 尝试获取结果，如果有异常会被抛出
                    result = _future.result()
                    # 如果成功完成，可以在这里记录成功统计
                except asyncio.CancelledError:
                    # 正确处理取消异常，避免"never retrieved"警告
                    self.logger.info("Task was cancelled")
                except Exception as exception:
                    # 异常被正确"获取"了，不会再出现"never retrieved"警告
                    self._exception_count += 1
                    
                    # 记录异常详情
                    self.logger.error(
                        f"Task completed with exception: {type(exception).__name__}: {exception}"
                    )
                    self.logger.debug("Task exception details:", exc_info=exception)
                    
                    # 可以在这里添加更多的异常处理逻辑，如发送到监控系统
                    
            except Exception as e:
                # 防止回调函数本身出现异常
                self.logger.error(f"Error in task done callback: {e}")
            finally:
                # 确保信号量始终被释放
                self.semaphore.release()
                
                # 定期调整并发数（从每3个任务调整一次改为每2个任务调整一次）
                if self._total_tasks % 2 == 0:
                    self.semaphore.adjust_concurrency()

        task.add_done_callback(done_callback)

        return task

    def all_done(self) -> bool:
        return len(self.current_task) == 0
    
    def record_response_time(self, response_time: float):
        """记录任务的响应时间，用于动态调整并发数"""
        self.semaphore.record_response_time(response_time)
    
    def get_stats(self) -> dict:
        """获取任务管理器统计信息"""
        return {
            'active_tasks': len(self.current_task),
            'total_tasks': self._total_tasks,
            'exception_count': self._exception_count,
            'success_rate': (self._total_tasks - self._exception_count) / max(1, self._total_tasks) * 100,
            'current_concurrency': self.semaphore._current_value
        }