#!/usr/bin/python
# -*- coding:UTF-8 -*-
import asyncio
from asyncio import Task, Future, Semaphore
from typing import Set, Final
from crawlo.utils.log import get_logger


class TaskManager:

    def __init__(self, total_concurrency: int = 8):
        self.current_task: Final[Set] = set()
        self.semaphore: Semaphore = Semaphore(total_concurrency)
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
                self.current_task.remove(task)
                
                # 获取任务结果或异常 - 这是关键，必须调用result()或exception()来"获取"异常
                try:
                    # 尝试获取结果，如果有异常会被抛出
                    result = _future.result()
                    # 如果成功完成，可以在这里记录成功统计
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

        task.add_done_callback(done_callback)

        return task

    def all_done(self) -> bool:
        return len(self.current_task) == 0
    
    def get_stats(self) -> dict:
        """获取任务管理器统计信息"""
        return {
            'active_tasks': len(self.current_task),
            'total_tasks': self._total_tasks,
            'exception_count': self._exception_count,
            'success_rate': (self._total_tasks - self._exception_count) / max(1, self._total_tasks) * 100
        }
