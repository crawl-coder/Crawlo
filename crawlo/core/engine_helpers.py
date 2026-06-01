#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""Engine helper utilities for statistics and backpressure control"""
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Dict

from crawlo.backpressure.interfaces import BackpressureStrategyConfig, IBackpressureStrategy
from crawlo.backpressure.strategies import QueueSizeStrategy, AdaptiveStrategy
from crawlo.backpressure import BackpressureController as _UnifiedController


@dataclass
class GenerationStats:
    """
    Request generation statistics tracker
    
    Tracks statistics for request generation.
    
    Attributes:
        total_generated: Total number of requests generated
        backpressure_events: Number of backpressure trigger events
        batches_processed: Number of batches processed
        start_time: Start time
        end_time: End time
    """
    total_generated: int = 0
    backpressure_events: int = 0
    batches_processed: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def increment_generated(self, count: int = 1) -> None:
        """Increment generation count"""
        self.total_generated += count
    
    def increment_backpressure(self) -> None:
        """Increment backpressure event count"""
        self.backpressure_events += 1
    
    def increment_batch(self) -> None:
        """Increment batch count"""
        self.batches_processed += 1
    
    def mark_start(self) -> None:
        """Mark generation start time"""
        self.start_time = time.time()
    
    def mark_end(self) -> None:
        """Mark generation end time"""
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def generation_rate(self) -> float:
        """Calculate generation rate (requests/second)"""
        duration = self.duration
        if duration > 0:
            return self.total_generated / duration
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'total_generated': self.total_generated,
            'backpressure_events': self.backpressure_events,
            'batches_processed': self.batches_processed,
            'duration': round(self.duration, 2),
            'generation_rate': round(self.generation_rate, 2),
        }
    
    def reset(self) -> None:
        """Reset statistics"""
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


class EngineBackpressureAdapter:
    """
    Engine-level backpressure adapter — bridges Engine primitives (scheduler,
    task_manager) to the generic backpressure strategy module.

    Controls request generation speed by checking both queue capacity
    and task concurrency. Internally delegates to crawlo.backpressure module
    for unified strategy management.

    Example:
        adapter = EngineBackpressureAdapter(
            max_queue_size=200,
            backpressure_ratio=0.9,
            strategy='queue_size'
        )

        if adapter.should_pause(scheduler, task_manager):
            await adapter.wait_for_capacity(scheduler, task_manager)
    """

    def __init__(
        self,
        max_queue_size: int = 200,
        backpressure_ratio: float = 0.9,
        initial_wait: float = 0.01,
        max_wait: float = 1.0,
        strategy: str = 'queue_size',
    ):
        """
        Initialize backpressure adapter

        Args:
            max_queue_size: Maximum queue size
            backpressure_ratio: Backpressure trigger ratio
            initial_wait: Initial wait time in seconds
            max_wait: Maximum wait time in seconds
            strategy: Strategy name ('queue_size' | 'adaptive')
        """
        self.max_queue_size = max_queue_size
        self.backpressure_ratio = backpressure_ratio
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.strategy_name = strategy

        # Statistics
        self._pause_count = 0
        self._total_wait_time = 0.0

        # Internal: create backpressure strategy from config
        config = BackpressureStrategyConfig(
            threshold=backpressure_ratio,
            base_delay=initial_wait,
            max_delay=max_wait,
        )
        strategy_cls = self._resolve_strategy(strategy)(config=config)
        self._unified = _UnifiedController(strategy=strategy_cls)

    @staticmethod
    def _resolve_strategy(name: str) -> type:
        """Resolve strategy class from name"""
        _map = {
            'queue_size': QueueSizeStrategy,
            'adaptive': AdaptiveStrategy,
        }
        return _map.get(name, QueueSizeStrategy)
    
    @property
    def pause_count(self) -> int:
        """Number of pauses"""
        return self._pause_count
    
    @property
    def total_wait_time(self) -> float:
        """Total wait time"""
        return self._total_wait_time
    
    def is_queue_full(self, scheduler) -> bool:
        """
        Check if queue is full (delegates to unified backpressure strategy)
        
        Args:
            scheduler: Scheduler instance
            
        Returns:
            bool: True if queue utilization >= strategy threshold
        """
        if not scheduler:
            return False
        
        queue_size = len(scheduler)
        # Use unified controller's strategy threshold for consistency with QueueManager
        threshold = self.max_queue_size * self._unified.strategy._config.threshold
        return queue_size >= threshold
    
    def is_overloaded(self, task_manager) -> bool:
        """
        Check if task manager is overloaded
        
        Args:
            task_manager: Task manager instance
            
        Returns:
            bool: True if overloaded
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
        Check if should pause
        
        Args:
            scheduler: Scheduler instance
            task_manager: Task manager instance (optional)
            
        Returns:
            bool: True if should pause
        """
        # Check if queue is full
        if self.is_queue_full(scheduler):
            return True
        
        # Check if task manager is overloaded
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
        Wait for system to have enough capacity
        
        Args:
            scheduler: Scheduler instance
            task_manager: Task manager instance
            running_check: Callback to check if still running
            
        Returns:
            bool: True if capacity was successfully waited for (False if interrupted)
        """
        import asyncio
        
        self._pause_count += 1
        start_wait = time.time()
        
        wait_time = self.initial_wait
        
        while self.should_pause(scheduler, task_manager):
            # Check if still running
            if running_check and not running_check():
                return False
            
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, self.max_wait)
        
        self._total_wait_time += time.time() - start_wait
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            'pause_count': self._pause_count,
            'total_wait_time': round(self._total_wait_time, 3),
            'max_queue_size': self.max_queue_size,
            'backpressure_ratio': self.backpressure_ratio,
        }
    
    def reset(self) -> None:
        """Reset statistics"""
        self._pause_count = 0
        self._total_wait_time = 0.0
    
    def __repr__(self) -> str:
        return (
            f"<EngineBackpressureAdapter: max_queue={self.max_queue_size}, "
            f"ratio={self.backpressure_ratio}, "
            f"strategy={self.strategy_name}, "
            f"pauses={self._pause_count}>"
        )


__all__ = [
    'GenerationStats',
    'EngineBackpressureAdapter',
]
