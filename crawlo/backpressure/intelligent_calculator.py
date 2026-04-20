"""
智能背压延迟计算器

基于多维度指标计算最优背压延迟：
1. 基础延迟：根据综合评分
2. 调整因子：根据各项细分指标
3. 预测补偿：根据增长趋势

Author: Crawlo Framework Team
"""

import asyncio
from typing import Optional, Dict, Any
from .metrics_collector import BackpressureMetricsCollector, BackpressureMetrics


class IntelligentBackpressureCalculator:
    """
    智能背压延迟计算器
    
    根据多维度指标计算最优延迟：
    - 基础延迟：根据综合评分级别
    - 调整因子：根据细分指标（队列使用率、速率差、超时率、成功率）
    - 预测补偿：根据队列增长趋势
    - 平滑处理：避免延迟剧烈波动
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
        
        # 历史延迟记录（用于平滑）
        self._delay_history = []
        self._max_history_len = max_history_len
        
        # 缓存机制（优化CPU开销）
        self._cache_ttl = cache_ttl
        self._cached_delay: float = 0.0
        self._cache_timestamp: float = 0.0
    
    def _default_levels_config(self) -> Dict[str, Any]:
        """默认分级配置"""
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
        计算背压延迟（带缓存优化）
        
        Returns:
            float: 延迟时间（秒）
        """
        # 如果没有指标采集器，返回0
        if not self.metrics_collector:
            return 0.0
        
        # 检查缓存是否有效（优化：避免频繁计算）
        import time
        current_time = time.time()
        if current_time - self._cache_timestamp < self._cache_ttl:
            return self._cached_delay
        
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics:
            return 0.0
        
        # 1. 基础延迟：根据级别
        base_delay = self._calculate_base_delay(metrics.level)
        
        # 2. 调整因子：根据细分指标
        adjustment = self._calculate_adjustment(metrics)
        
        # 3. 预测补偿：根据增长趋势
        prediction = await self._calculate_prediction() if self.enable_prediction else 0.0
        
        # 综合计算
        delay = base_delay * adjustment + prediction
        
        # 限制范围
        delay = max(0.0, min(delay, self.max_delay))
        
        # 平滑处理
        if self.enable_smoothing:
            delay = self._smooth_delay(delay)
        
        # 更新缓存
        self._cached_delay = delay
        self._cache_timestamp = current_time
        
        return delay
    
    def _calculate_base_delay(self, level: str) -> float:
        """
        根据级别计算基础延迟
        
        Args:
            level: 级别（normal/warning/danger/critical）
            
        Returns:
            float: 基础延迟
        """
        level_config = self.levels_config.get(level, self.levels_config['normal'])
        delay_range = level_config['delay_range']
        
        # 取范围中间值作为基础延迟
        return (delay_range[0] + delay_range[1]) / 2
    
    def _calculate_adjustment(self, metrics: BackpressureMetrics) -> float:
        """
        根据细分指标计算调整因子
        
        调整因子范围：0.5-2.0
        - 队列使用率 > 90%：1.5倍
        - 速率差 > 50/s：1.5倍
        - 超时率 > 30%：1.3倍
        - 成功率 < 70%：1.4倍
        
        Args:
            metrics: 当前指标
            
        Returns:
            float: 调整因子
        """
        adjustment = 1.0
        
        # 队列使用率调整
        if metrics.queue_usage_ratio > 0.9:
            adjustment *= 1.5
        elif metrics.queue_usage_ratio > 0.8:
            adjustment *= 1.2
        
        # 速率差调整
        if metrics.rate_difference > 50:
            adjustment *= 1.5
        elif metrics.rate_difference > 20:
            adjustment *= 1.2
        
        # 超时率调整
        if metrics.timeout_rate > 0.3:
            adjustment *= 1.3
        elif metrics.timeout_rate > 0.2:
            adjustment *= 1.1
        
        # 成功率调整（成功率低时增加延迟）
        if metrics.success_rate < 0.7:
            adjustment *= 1.4
        elif metrics.success_rate < 0.85:
            adjustment *= 1.1
        
        return adjustment
    
    async def _calculate_prediction(self) -> float:
        """
        根据增长趋势预测额外延迟
        
        如果队列增长很快，增加额外延迟来抑制
        
        Returns:
            float: 预测补偿延迟
        """
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics or metrics.queue_growth_rate <= 0:
            return 0.0
        
        # 增长速率分级补偿
        if metrics.queue_growth_rate > 100:  # 每秒增长>100
            return 0.5
        elif metrics.queue_growth_rate > 50:  # 每秒增长>50
            return 0.3
        elif metrics.queue_growth_rate > 20:  # 每秒增长>20
            return 0.1
        
        return 0.0
    
    def _smooth_delay(self, delay: float) -> float:
        """
        平滑延迟变化
        
        避免延迟剧烈波动，限制单次变化幅度
        
        Args:
            delay: 原始延迟
            
        Returns:
            float: 平滑后的延迟
        """
        self._delay_history.append(delay)
        
        if len(self._delay_history) > self._max_history_len:
            self._delay_history.pop(0)
        
        # 如果有历史记录，限制变化幅度
        if len(self._delay_history) >= 2:
            prev_delay = self._delay_history[-2]
            max_change = 0.5  # 最大变化0.5秒
            
            if abs(delay - prev_delay) > max_change:
                direction = 1 if delay > prev_delay else -1
                return prev_delay + direction * max_change
        
        return delay
    
    def get_delay_history(self) -> list:
        """获取延迟历史"""
        return self._delay_history.copy()
    
    def reset_history(self):
        """重置历史记录"""
        self._delay_history = []
