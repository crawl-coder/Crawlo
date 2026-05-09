#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Backpressure control module

Provides unified backpressure control entry point.
"""
import asyncio
import time
from typing import Optional, Dict, Any

from crawlo.backpressure.interfaces import (
    PressureLevel,
    BackpressureMetrics,
    IBackpressureStrategy,
    BackpressureStrategyConfig,
)
from crawlo.backpressure.strategies import (
    QueueSizeStrategy,
    AdaptiveStrategy,
    CompositeStrategy,
)
from crawlo.backpressure.metrics_collector import (
    BackpressureMetricsCollector,
    BackpressureMetrics,
)
from crawlo.backpressure.intelligent_calculator import (
    IntelligentBackpressureCalculator,
)
from crawlo.backpressure.monitor import (
    BackpressureMonitor,
)


class BackpressureController:
    """
    Backpressure controller
    
    Manages backpressure strategies, provides concise backpressure control interface.
    
    Example:
        controller = BackpressureController(
            strategy=QueueSizeStrategy()
        )
        
        if await controller.should_apply(queue):
            delay = await controller.calculate_delay(queue)
            await asyncio.sleep(delay)
    """
    
    def __init__(
        self,
        strategy: Optional[IBackpressureStrategy] = None,
        enabled: bool = True,
    ):
        """
        Initialize controller
        
        Args:
            strategy: Backpressure strategy
            enabled: Whether to enable backpressure
        """
        self._strategy = strategy or QueueSizeStrategy()
        self._enabled = enabled
        self._active = False
        
        # Statistics
        self._apply_count = 0
        self._total_delay = 0.0
        self._last_apply_time = 0.0
    
    @property
    def enabled(self) -> bool:
        """Whether enabled"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled status"""
        self._enabled = value
    
    @property
    def active(self) -> bool:
        """Whether backpressure is currently being applied"""
        return self._active
    
    @property
    def strategy(self) -> IBackpressureStrategy:
        """Get current strategy"""
        return self._strategy
    
    @strategy.setter
    def strategy(self, value: IBackpressureStrategy) -> None:
        """Set strategy"""
        self._strategy = value
    
    async def should_apply(self, queue) -> bool:
        """
        Determine whether backpressure should be applied
        
        Args:
            queue: Queue instance
            
        Returns:
            bool: Whether backpressure should be applied
        """
        if not self._enabled:
            return False
        
        result = await self._strategy.should_apply(queue)
        
        if result != self._active:
            self._active = result
            self._last_apply_time = 0.0
        
        if result:
            self._apply_count += 1
        
        return result
    
    async def calculate_delay(self, queue) -> float:
        """
        Calculate backpressure delay
        
        Args:
            queue: Queue instance
            
        Returns:
            float: Delay time in seconds
        """
        if not self._enabled:
            return 0.0
        
        delay = await self._strategy.calculate_delay(queue)
        
        if delay > 0:
            self._total_delay += delay
        
        return delay
    
    async def wait_for_capacity(self, queue, max_wait: float = 30.0) -> bool:
        """
        Wait for system to have enough capacity
        
        Args:
            queue: Queue instance
            max_wait: Maximum wait time in seconds
            
        Returns:
            bool: Whether capacity was successfully waited for
        """
        start_time = time.time()
        wait_time = 0.01
        
        while await self.should_apply(queue):
            if time.time() - start_time > max_wait:
                return False
            
            delay = await self.calculate_delay(queue)
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(wait_time)
            
            wait_time = min(wait_time * 1.1, 1.0)
        
        return True
    
    async def get_metrics(self, queue):
        """
        Get backpressure metrics
        
        Args:
            queue: Queue instance
            
        Returns:
            BackpressureMetrics: Metric data
        """
        return await self._strategy.get_metrics(queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics
        
        Returns:
            dict: Statistics
        """
        return {
            'enabled': self._enabled,
            'active': self._active,
            'strategy': self._strategy.name,
            'apply_count': self._apply_count,
            'total_delay': round(self._total_delay, 3),
            'avg_delay': round(self._total_delay / self._apply_count, 3) if self._apply_count > 0 else 0.0,
        }
    
    def reset(self) -> None:
        """Reset status"""
        self._active = False
        self._strategy.reset()
        self._apply_count = 0
        self._total_delay = 0.0


__all__ = [
    'BackpressureController',
    'PressureLevel',
    'BackpressureMetrics',
    'IBackpressureStrategy',
    'BackpressureStrategyConfig',
    'QueueSizeStrategy',
    'AdaptiveStrategy',
    'CompositeStrategy',
    # 智能背压组件
    'BackpressureMetricsCollector',
    'IntelligentBackpressureCalculator',
    'BackpressureMonitor',
]
