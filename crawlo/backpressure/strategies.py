#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Backpressure strategy implementations

Provides multiple backpressure strategy implementations.
"""
import time
import asyncio
from typing import TYPE_CHECKING, Dict, Optional, List

from crawlo.backpressure.interfaces import (
    IBackpressureStrategy,
    BackpressureStrategyConfig,
    BackpressureMetrics,
    PressureLevel,
)

if TYPE_CHECKING:
    from crawlo.queue.interfaces import IQueue


# Delay calculation threshold constants
CRITICAL_UTILIZATION_THRESHOLD = 0.95
HIGH_UTILIZATION_THRESHOLD = 0.90
DELAY_MULTIPLIER_CRITICAL = 4
DELAY_MULTIPLIER_MAX_RATIO = 3


class QueueSizeStrategy(IBackpressureStrategy):
    """
    Queue size-based backpressure strategy
    
    Determines whether to apply backpressure and how much delay based on queue utilization.
    """
    
    def __init__(self, config: Optional[BackpressureStrategyConfig] = None):
        """
        Initialize strategy
        
        Args:
            config: Strategy configuration
        """
        self._config = config or BackpressureStrategyConfig()
        self._last_check_time = 0.0
        self._current_level = PressureLevel.NORMAL
    
    @property
    def name(self) -> str:
        return "queue_size"
    
    async def should_apply(self, queue: 'IQueue') -> bool:
        """Determine whether backpressure should be applied"""
        utilization = await self._get_utilization(queue)
        return utilization >= self._config.threshold
    
    async def calculate_delay(self, queue: 'IQueue') -> float:
        """
        Calculate backpressure delay
        
        Utilization    Delay
        80%-90%       base_delay * (1-3)
        90%-95%       base_delay * (3-5)
        95%-100%      max_delay
        """
        utilization = await self._get_utilization(queue)
        
        if utilization >= CRITICAL_UTILIZATION_THRESHOLD:
            return self._config.max_delay
        elif utilization >= HIGH_UTILIZATION_THRESHOLD:
            return self._config.base_delay * DELAY_MULTIPLIER_CRITICAL
        elif utilization >= self._config.threshold:
            ratio = (utilization - self._config.threshold) / (CRITICAL_UTILIZATION_THRESHOLD - self._config.threshold)
            return self._config.base_delay * (1 + ratio * DELAY_MULTIPLIER_MAX_RATIO)
        else:
            return 0.0
    
    async def get_level(self, queue: 'IQueue') -> PressureLevel:
        """获取当前背压级别"""
        utilization = await self._get_utilization(queue)
        
        if utilization >= 1.0:
            return PressureLevel.FULL
        elif utilization >= self._config.critical_threshold:
            return PressureLevel.CRITICAL
        elif utilization >= self._config.warning_threshold:
            return PressureLevel.WARNING
        else:
            return PressureLevel.NORMAL
    
    async def get_metrics(self, queue: 'IQueue') -> BackpressureMetrics:
        """获取背压指标"""
        queue_size = await queue.size()
        max_size = queue.max_size
        utilization = queue_size / max_size if max_size > 0 else 0.0
        level = await self.get_level(queue)
        delay = await self.calculate_delay(queue)
        
        return BackpressureMetrics(
            queue_size=queue_size,
            max_queue_size=max_size,
            utilization=utilization,
            active=utilization >= self._config.threshold,
            level=level,
            delay=delay,
            timestamp=time.time(),
        )
    
    async def _get_utilization(self, queue: 'IQueue') -> float:
        """获取队列使用率"""
        if queue.max_size <= 0:
            return 0.0
        
        queue_size = await queue.size()
        return queue_size / queue.max_size
    
    def reset(self) -> None:
        """重置策略状态"""
        self._current_level = PressureLevel.NORMAL


class AdaptiveStrategy(IBackpressureStrategy):
    """
    自适应背压策略
    
    根据历史数据动态调整背压参数。
    """
    
    def __init__(
        self,
        config: Optional[BackpressureStrategyConfig] = None,
        learning_window: int = 100,
        adaptation_rate: float = 0.1,
    ):
        """
        初始化策略
        
        Args:
            config: 策略配置
            learning_window: 学习窗口大小
            adaptation_rate: 适应速率 (0-1)
        """
        self._config = config or BackpressureStrategyConfig()
        self._learning_window = learning_window
        self._adaptation_rate = adaptation_rate
        
        # 历史数据
        self._delay_history: List[float] = []
        self._utilization_history: List[float] = []
        
        # 动态阈值
        self._dynamic_threshold = self._config.threshold
        self._last_update_time = time.time()
    
    @property
    def name(self) -> str:
        return "adaptive"
    
    async def should_apply(self, queue: 'IQueue') -> bool:
        """判断是否应该应用背压"""
        utilization = await self._get_utilization(queue)
        
        # 更新动态阈值
        await self._update_dynamic_threshold()
        
        return utilization >= self._dynamic_threshold
    
    async def calculate_delay(self, queue: 'IQueue') -> float:
        """计算背压延迟"""
        utilization = await self._get_utilization(queue)
        
        # 基础延迟基于使用率
        if utilization >= 0.95:
            base_delay = self._config.max_delay
        elif utilization >= 0.90:
            base_delay = self._config.base_delay * 4
        elif utilization >= self._config.threshold:
            ratio = (utilization - self._config.threshold) / (0.95 - self._config.threshold)
            base_delay = self._config.base_delay * (1 + ratio * 3)
        else:
            base_delay = 0.0
        
        # 根据历史数据调整延迟
        adjusted_delay = await self._adjust_delay_based_on_history(base_delay)
        
        return adjusted_delay
    
    async def get_level(self, queue: 'IQueue') -> PressureLevel:
        """获取当前背压级别"""
        utilization = await self._get_utilization(queue)
        
        if utilization >= 1.0:
            return PressureLevel.FULL
        elif utilization >= self._config.critical_threshold:
            return PressureLevel.CRITICAL
        elif utilization >= self._config.warning_threshold:
            return PressureLevel.WARNING
        else:
            return PressureLevel.NORMAL
    
    async def get_metrics(self, queue: 'IQueue') -> BackpressureMetrics:
        """获取背压指标"""
        queue_size = await queue.size()
        max_size = queue.max_size
        utilization = queue_size / max_size if max_size > 0 else 0.0
        level = await self.get_level(queue)
        delay = await self.calculate_delay(queue)
        
        return BackpressureMetrics(
            queue_size=queue_size,
            max_queue_size=max_size,
            utilization=utilization,
            active=utilization >= self._dynamic_threshold,
            level=level,
            delay=delay,
            timestamp=time.time(),
        )
    
    async def _get_utilization(self, queue: 'IQueue') -> float:
        """获取队列使用率"""
        if queue.max_size <= 0:
            return 0.0
        
        queue_size = await queue.size()
        return queue_size / queue.max_size
    
    async def _update_dynamic_threshold(self) -> None:
        """更新动态阈值"""
        # 限制更新频率
        current_time = time.time()
        if current_time - self._last_update_time < 1.0:
            return
        
        self._last_update_time = current_time
        
        if not self._delay_history:
            return
        
        # 计算平均延迟
        avg_delay = sum(self._delay_history) / len(self._delay_history)
        
        # 根据平均延迟调整阈值
        # 如果平均延迟较高，降低阈值（更积极地应用背压）
        # 如果平均延迟较低，提高阈值（更宽松）
        if avg_delay > self._config.base_delay * 3:
            self._dynamic_threshold = min(
                self._dynamic_threshold * (1 - self._adaptation_rate),
                self._config.threshold
            )
        elif avg_delay < self._config.base_delay:
            self._dynamic_threshold = max(
                self._dynamic_threshold * (1 + self._adaptation_rate),
                self._config.threshold * 0.8
            )
    
    async def _adjust_delay_based_on_history(self, base_delay: float) -> float:
        """根据历史数据调整延迟"""
        if not self._delay_history:
            return base_delay
        
        # 计算最近几次延迟的平均值
        recent_delays = self._delay_history[-min(10, len(self._delay_history)):]
        avg_recent_delay = sum(recent_delays) / len(recent_delays)
        
        # 如果最近延迟较高，说明系统需要更长的延迟
        if avg_recent_delay > base_delay:
            factor = min(avg_recent_delay / base_delay, 2.0)
            return min(base_delay * factor, self._config.max_delay)
        else:
            return base_delay
    
    def record_delay(self, delay: float) -> None:
        """记录延迟数据"""
        self._delay_history.append(delay)
        if len(self._delay_history) > self._learning_window:
            self._delay_history = self._delay_history[-self._learning_window:]
    
    def reset(self) -> None:
        """重置策略状态"""
        self._delay_history.clear()
        self._utilization_history.clear()
        self._dynamic_threshold = self._config.threshold


class CompositeStrategy(IBackpressureStrategy):
    """
    组合背压策略
    
    组合多个策略，根据优先级选择最严格的结果。
    """
    
    def __init__(self, strategies: Optional[List[IBackpressureStrategy]] = None):
        """
        初始化策略
        
        Args:
            strategies: 策略列表
        """
        self._strategies = strategies or []
        self._active_strategy: Optional[IBackpressureStrategy] = None
    
    @property
    def name(self) -> str:
        return "composite"
    
    def add_strategy(self, strategy: IBackpressureStrategy) -> None:
        """添加策略"""
        self._strategies.append(strategy)
    
    async def should_apply(self, queue: 'IQueue') -> bool:
        """判断是否应该应用背压"""
        # 任何策略认为应该应用背压就应用
        for strategy in self._strategies:
            if await strategy.should_apply(queue):
                self._active_strategy = strategy
                return True
        return False
    
    async def calculate_delay(self, queue: 'IQueue') -> float:
        """计算背压延迟 - 使用最严格策略的结果"""
        if not self._strategies:
            return 0.0
        
        max_delay = 0.0
        for strategy in self._strategies:
            delay = await strategy.calculate_delay(queue)
            if delay > max_delay:
                max_delay = delay
                self._active_strategy = strategy
        
        return max_delay
    
    async def get_level(self, queue: 'IQueue') -> PressureLevel:
        """获取当前背压级别 - 使用最严格的级别"""
        if not self._strategies:
            return PressureLevel.NORMAL
        
        max_level = PressureLevel.NORMAL
        level_priority = {
            PressureLevel.NORMAL: 0,
            PressureLevel.WARNING: 1,
            PressureLevel.CRITICAL: 2,
            PressureLevel.FULL: 3,
        }
        
        for strategy in self._strategies:
            level = await strategy.get_level(queue)
            if level_priority.get(level, 0) > level_priority.get(max_level, 0):
                max_level = level
        
        return max_level
    
    async def get_metrics(self, queue: 'IQueue') -> BackpressureMetrics:
        """获取背压指标"""
        metrics_list = []
        for strategy in self._strategies:
            metrics_list.append(await strategy.get_metrics(queue))
        
        # 合并指标 - 使用最严格的
        max_queue_size = max(m.metrics.queue_size for m in metrics_list) if metrics_list else 0
        max_utilization = max(m.utilization for m in metrics_list) if metrics_list else 0.0
        active = any(m.active for m in metrics_list) if metrics_list else False
        max_delay = max(m.delay for m in metrics_list) if metrics_list else 0.0
        
        level = PressureLevel.NORMAL
        for m in metrics_list:
            if m.level == PressureLevel.FULL:
                level = PressureLevel.FULL
                break
            elif m.level == PressureLevel.CRITICAL:
                level = PressureLevel.CRITICAL
            elif m.level == PressureLevel.WARNING and level != PressureLevel.CRITICAL:
                level = PressureLevel.WARNING
        
        return BackpressureMetrics(
            queue_size=max_queue_size,
            max_queue_size=queue.max_size,
            utilization=max_utilization,
            active=active,
            level=level,
            delay=max_delay,
            timestamp=time.time(),
        )
    
    def reset(self) -> None:
        """重置策略状态"""
        for strategy in self._strategies:
            strategy.reset()
        self._active_strategy = None


__all__ = [
    'QueueSizeStrategy',
    'AdaptiveStrategy',
    'CompositeStrategy',
]
