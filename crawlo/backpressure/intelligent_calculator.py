"""Intelligent backpressure delay calculator

Calculates optimal backpressure delay based on multi-dimensional metrics:
1. Base delay: Based on comprehensive score
2. Adjustment factors: Based on detailed metrics
3. Predictive compensation: Based on growth trend

Author: Crawlo Framework Team
"""

import time
import asyncio
from typing import Optional, Dict, Any
from collections import deque
from .metrics_collector import BackpressureMetricsCollector, BackpressureMetrics


class IntelligentBackpressureCalculator:
    """
    Intelligent backpressure delay calculator
    
    Calculates optimal delay based on multi-dimensional metrics:
    - Base delay: Based on comprehensive score level
    - Adjustment factors: Based on detailed metrics (queue utilization, rate difference, timeout rate, success rate)
    - Predictive compensation: Based on queue growth trend
    - Smoothing: Avoids drastic delay fluctuations
    """
    
    def __init__(
        self,
        metrics_collector: Optional[BackpressureMetricsCollector] = None,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        levels_config: Optional[Dict[str, Any]] = None,
        enable_prediction: bool = True,
        enable_smoothing: bool = True,
        max_history_len: int = 5,
        cache_ttl: float = 0.1
    ):
        """
        初始化计算器
        
        Args:
            metrics_collector: 指标采集器
            base_delay: 基础延迟
            max_delay: 最大延迟
            levels_config: 分级配置
            enable_prediction: 是否启用预测补偿
            enable_smoothing: 是否启用平滑处理
            max_history_len: 历史延迟记录长度
            cache_ttl: 缓存有效期（秒），避免频繁计算（默认0.1s）
        """
        self.metrics_collector = metrics_collector
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.enable_prediction = enable_prediction
        self.enable_smoothing = enable_smoothing
        self.levels_config = levels_config or self._default_levels_config()
        
        # Historical delay records for smoothing (using bounded deque)
        self._delay_history: deque = deque(maxlen=max_history_len)
        self._max_history_len = max_history_len
        
        # Caching mechanism (optimizes CPU overhead)
        self._cache_ttl = cache_ttl
        self._cached_delay: float = 0.0
        self._cache_timestamp: float = 0.0
    
    def _default_levels_config(self) -> Dict[str, Any]:
        """Default level configuration"""
        return {
            'normal': {
                'score_range': (0, 50),
                'delay_range': (0, 0.3),
                'actions': []
            },
            'warning': {
                'score_range': (50, 70),
                'delay_range': (0.3, 1.0),
                'actions': ['log']
            },
            'danger': {
                'score_range': (70, 85),
                'delay_range': (1.0, 2.5),
                'actions': ['log', 'reduce_concurrency']
            },
            'critical': {
                'score_range': (85, 100),
                'delay_range': (2.5, 5.0),
                'actions': ['log', 'reduce_concurrency', 'pause_enqueuing']
            }
        }
    
    async def calculate_delay(self) -> float:
        """
        Calculate backpressure delay (with cache optimization)
        
        Returns:
            float: Delay time in seconds
        """
        # Return 0 if no metrics collector
        if not self.metrics_collector:
            return 0.0
        
        # Check if cache is still valid (optimization: avoid frequent calculations)
        # time already imported at top
        current_time = time.time()
        if current_time - self._cache_timestamp < self._cache_ttl:
            return self._cached_delay
        
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics:
            return 0.0
        
        # 1. Base delay: Based on level
        base_delay = self._calculate_base_delay(metrics.level)
        
        # 2. Adjustment factor: Based on detailed metrics
        adjustment = self._calculate_adjustment(metrics)
        
        # 3. Predictive compensation: Based on growth trend
        prediction = await self._calculate_prediction() if self.enable_prediction else 0.0
        
        # Combined calculation
        delay = base_delay * adjustment + prediction
        
        # Limit range
        delay = max(0.0, min(delay, self.max_delay))
        
        # Smoothing
        if self.enable_smoothing:
            delay = self._smooth_delay(delay)
        
        # Update cache
        self._cached_delay = delay
        self._cache_timestamp = current_time
        
        return delay
    
    def _calculate_base_delay(self, level: str) -> float:
        """
        Calculate base delay based on level
        
        Args:
            level: Level (normal/warning/danger/critical)
            
        Returns:
            float: Base delay
        """
        level_config = self.levels_config.get(level, self.levels_config['normal'])
        delay_range = level_config['delay_range']
        
        # Use middle value of range as base delay
        return (delay_range[0] + delay_range[1]) / 2
    
    def _calculate_adjustment(self, metrics: BackpressureMetrics) -> float:
        """
        Calculate adjustment factor based on detailed metrics
        
        Adjustment factor range: 0.5-2.0
        - Queue utilization > 90%: 1.5x
        - Rate difference > 50/s: 1.5x
        - Timeout rate > 30%: 1.3x
        - Success rate < 70%: 1.4x
        
        Args:
            metrics: Current metrics
            
        Returns:
            float: Adjustment factor
        """
        adjustment = 1.0
        
        # Queue utilization adjustment
        if metrics.queue_usage_ratio > 0.9:
            adjustment *= 1.5
        elif metrics.queue_usage_ratio > 0.8:
            adjustment *= 1.2
        
        # Rate difference adjustment
        if metrics.rate_difference > 50:
            adjustment *= 1.5
        elif metrics.rate_difference > 20:
            adjustment *= 1.2
        
        # Timeout rate adjustment
        if metrics.timeout_rate > 0.3:
            adjustment *= 1.3
        elif metrics.timeout_rate > 0.2:
            adjustment *= 1.1
        
        # Success rate adjustment (increase delay when success rate is low)
        if metrics.success_rate < 0.7:
            adjustment *= 1.4
        elif metrics.success_rate < 0.85:
            adjustment *= 1.1
        
        return adjustment
    
    async def _calculate_prediction(self) -> float:
        """
        Calculate predictive compensation delay based on growth trend
        
        Increases additional delay when queue is growing rapidly
        
        Returns:
            float: Predictive compensation delay
        """
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics or metrics.queue_growth_rate <= 0:
            return 0.0
        
        # Growth rate tiered compensation
        if metrics.queue_growth_rate > 100:  # Growth > 100 per second
            return 0.5
        elif metrics.queue_growth_rate > 50:  # Growth > 50 per second
            return 0.3
        elif metrics.queue_growth_rate > 20:  # Growth > 20 per second
            return 0.1
        
        return 0.0
    
    def _smooth_delay(self, delay: float) -> float:
        """
        Smooth delay changes
        
        Avoids drastic delay fluctuations by limiting single change amplitude
        
        Args:
            delay: Raw delay
            
        Returns:
            float: Smoothed delay
        """
        self._delay_history.append(delay)
        # Note: deque(maxlen=N) automatically manages length, no need to manually pop
        
        # If there's history, limit change amplitude
        if len(self._delay_history) >= 2:
            prev_delay = self._delay_history[-2]
            max_change = 0.5  # Maximum change 0.5 seconds
            
            if abs(delay - prev_delay) > max_change:
                direction = 1 if delay > prev_delay else -1
                return prev_delay + direction * max_change
        
        return delay
    
    def get_delay_history(self) -> list:
        """Get delay history"""
        return self._delay_history.copy()
    
    def reset_history(self) -> None:
        """Reset history"""
        self._delay_history.clear()
