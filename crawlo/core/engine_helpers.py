#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine 辅助工具类
================
提供 Engine 使用独立工具类，不改变 Engine 核心结构。

包含：
- GenerationStats: 请求生成统计数据类
- BackpressureController: 背压控制器
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GenerationStats:
    """
    请求生成统计数据类
    
    用于跟踪请求生成的统计信息。
    
    属性：
        total_generated: 已生成的请求总数
        backpressure_events: 背压触发次数
        batches_processed: 已处理的批次数
        start_time: 开始时间
        end_time: 结束时间
    """
    total_generated: int = 0
    backpressure_events: int = 0
    batches_processed: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def increment_generated(self, count: int = 1) -> None:
        """增加生成计数"""
        self.total_generated += count
    
    def increment_backpressure(self) -> None:
        """增加背压事件计数"""
        self.backpressure_events += 1
    
    def increment_batch(self) -> None:
        """增加批次计数"""
        self.batches_processed += 1
    
    def mark_start(self) -> None:
        """标记开始时间"""
        import time
        self.start_time = time.time()
    
    def mark_end(self) -> None:
        """标记结束时间"""
        import time
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """计算持续时间（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def generation_rate(self) -> float:
        """计算生成速率（请求/秒）"""
        duration = self.duration
        if duration > 0:
            return self.total_generated / duration
        return 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'total_generated': self.total_generated,
            'backpressure_events': self.backpressure_events,
            'batches_processed': self.batches_processed,
            'duration': round(self.duration, 2),
            'generation_rate': round(self.generation_rate, 2),
        }
    
    def reset(self) -> None:
        """重置统计"""
        self.total_generated = 0
        self.backpressure_events = 0
        self.batches_processed = 0
        self.start_time = None
        self.end_time = None
    
    def __repr__(self) -> str:
        return (
            f"<GenerationStats: generated={self.total_generated}, "
            f"backpressure={self.backpressure_events}, "
            f"rate={self.generation_rate:.1f}/s>"
        )


class BackpressureController:
    """
    背压控制器
    
    控制请求生成速度，防止系统过载。
    
    使用示例：
        controller = BackpressureController(
            max_queue_size=200,
            backpressure_ratio=0.9
        )
        
        if await controller.should_pause(scheduler, task_manager):
            await controller.wait_for_capacity(scheduler, task_manager)
    """
    
    def __init__(
        self,
        max_queue_size: int = 200,
        backpressure_ratio: float = 0.9,
        initial_wait: float = 0.01,
        max_wait: float = 1.0
    ):
        """
        初始化背压控制器
        
        Args:
            max_queue_size: 最大队列大小
            backpressure_ratio: 背压触发比例
            initial_wait: 初始等待时间（秒）
            max_wait: 最大等待时间（秒）
        """
        self.max_queue_size = max_queue_size
        self.backpressure_ratio = backpressure_ratio
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        
        # 统计
        self._pause_count = 0
        self._total_wait_time = 0.0
    
    @property
    def pause_count(self) -> int:
        """暂停次数"""
        return self._pause_count
    
    @property
    def total_wait_time(self) -> float:
        """总等待时间"""
        return self._total_wait_time
    
    def is_queue_full(self, scheduler) -> bool:
        """
        检查队列是否已满
        
        Args:
            scheduler: 调度器实例
            
        Returns:
            bool: 队列是否已满
        """
        if not scheduler:
            return False
        
        queue_size = len(scheduler)
        threshold = self.max_queue_size * self.backpressure_ratio
        return queue_size >= threshold
    
    def is_overloaded(self, task_manager) -> bool:
        """
        检查任务管理器是否过载
        
        Args:
            task_manager: 任务管理器实例
            
        Returns:
            bool: 是否过载
        """
        if not task_manager:
            return False
        
        current_tasks = len(task_manager.current_task)
        semaphore = getattr(task_manager, 'semaphore', None)
        
        if semaphore:
            max_concurrency = getattr(semaphore, '_initial_value', 8)
            return current_tasks >= max_concurrency * self.backpressure_ratio
        
        return False
    
    def should_pause(self, scheduler, task_manager=None) -> bool:
        """
        检查是否应该暂停
        
        Args:
            scheduler: 调度器实例
            task_manager: 任务管理器实例（可选）
            
        Returns:
            bool: 是否应该暂停
        """
        # 检查队列是否已满
        if self.is_queue_full(scheduler):
            return True
        
        # 检查任务管理器是否过载
        if task_manager and self.is_overloaded(task_manager):
            return True
        
        return False
    
    async def wait_for_capacity(
        self,
        scheduler,
        task_manager=None,
        running_check: callable = None
    ) -> bool:
        """
        等待系统有足够容量
        
        Args:
            scheduler: 调度器实例
            task_manager: 任务管理器实例
            running_check: 检查是否仍在运行的回调函数
            
        Returns:
            bool: 是否成功等到容量（False 表示被中断）
        """
        import asyncio
        import time
        
        self._pause_count += 1
        start_wait = time.time()
        
        wait_time = self.initial_wait
        
        while self.should_pause(scheduler, task_manager):
            # 检查是否仍在运行
            if running_check and not running_check():
                return False
            
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, self.max_wait)
        
        self._total_wait_time += time.time() - start_wait
        return True
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'pause_count': self._pause_count,
            'total_wait_time': round(self._total_wait_time, 3),
            'max_queue_size': self.max_queue_size,
            'backpressure_ratio': self.backpressure_ratio,
        }
    
    def reset(self) -> None:
        """重置统计"""
        self._pause_count = 0
        self._total_wait_time = 0.0
    
    def __repr__(self) -> str:
        return (
            f"<BackpressureController: max_queue={self.max_queue_size}, "
            f"ratio={self.backpressure_ratio}, "
            f"pauses={self._pause_count}>"
        )


__all__ = [
    'GenerationStats',
    'BackpressureController',
]
