#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
背压控制模块

提供统一的背压控制入口。
"""
from typing import Optional

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
    背压控制器
    
    统一管理背压策略，提供简洁的背压控制接口。
    
    使用示例：
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
        初始化控制器
        
        Args:
            strategy: 背压策略
            enabled: 是否启用背压
        """
        self._strategy = strategy or QueueSizeStrategy()
        self._enabled = enabled
        self._active = False
        
        # 统计信息
        self._apply_count = 0
        self._total_delay = 0.0
        self._last_apply_time = 0.0
    
    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置启用状态"""
        self._enabled = value
    
    @property
    def active(self) -> bool:
        """当前是否正在应用背压"""
        return self._active
    
    @property
    def strategy(self) -> IBackpressureStrategy:
        """获取当前策略"""
        return self._strategy
    
    @strategy.setter
    def strategy(self, value: IBackpressureStrategy) -> None:
        """设置策略"""
        self._strategy = value
    
    async def should_apply(self, queue) -> bool:
        """
        判断是否应该应用背压
        
        Args:
            queue: 队列实例
            
        Returns:
            bool: 是否应该应用背压
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
        计算背压延迟
        
        Args:
            queue: 队列实例
            
        Returns:
            float: 延迟时间（秒）
        """
        if not self._enabled:
            return 0.0
        
        delay = await self._strategy.calculate_delay(queue)
        
        if delay > 0:
            self._total_delay += delay
        
        return delay
    
    async def wait_for_capacity(self, queue, max_wait: float = 30.0) -> bool:
        """
        等待系统有足够容量
        
        Args:
            queue: 队列实例
            max_wait: 最大等待时间（秒）
            
        Returns:
            bool: 是否成功等到容量
        """
        import asyncio
        import time
        
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
        获取背压指标
        
        Args:
            queue: 队列实例
            
        Returns:
            BackpressureMetrics: 指标数据
        """
        return await self._strategy.get_metrics(queue)
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息
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
        """重置状态"""
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
