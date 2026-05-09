"""Backpressure monitoring system

Provides real-time monitoring, alerting, and diagnostics:
1. Real-time backpressure state monitoring
2. Tiered alerting (warning/danger/critical)
3. Alert history
4. Alert callback support

Author: Crawlo Framework Team
"""

import asyncio
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from crawlo.logging import get_logger
from .metrics_collector import BackpressureMetricsCollector, BackpressureMetrics

logger = get_logger(__name__)


@dataclass
class BackpressureAlert:
    """背压告警"""
    level: str                           # normal/warning/danger/critical
    score: float                         # 综合评分
    message: str                         # 告警消息
    timestamp: datetime                   # 发生时间
    metrics: Dict[str, Any]              # 相关指标
    actions: List[str]                   # 建议动作


class BackpressureMonitor:
    """
    背压监控器
    
    监控背压状态变化，触发告警，提供诊断信息
    """
    
    def __init__(
        self,
        metrics_collector: Optional[BackpressureMetricsCollector] = None,
        alert_callback: Optional[Callable[[BackpressureAlert], Any]] = None,
        check_interval: int = 10,
        max_alerts: int = 100,
        enable_logging: bool = True
    ):
        """
        初始化监控器
        
        Args:
            metrics_collector: 指标采集器
            alert_callback: 告警回调函数
            check_interval: 检查间隔（秒）
            max_alerts: 最大告警历史数量
            enable_logging: 是否启用日志记录
        """
        self.metrics_collector = metrics_collector
        self.alert_callback = alert_callback
        self.check_interval = check_interval
        self.max_alerts = max_alerts
        self.enable_logging = enable_logging
        
        # 告警历史
        self._alert_history: deque = deque(maxlen=max_alerts)
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 上次告警级别
        self._last_alert_level = 'normal'
        
        # 级别计数器（用于统计）
        self._level_counts: Dict[str, int] = {
            'normal': 0,
            'warning': 0,
            'danger': 0,
            'critical': 0
        }
    
    async def start(self):
        """启动监控"""
        if not self.metrics_collector:
            logger.warning("未提供指标采集器，监控系统无法启动")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.debug("背压监控系统已启动")
    
    async def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.debug("背压监控系统已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_and_alert()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控异常: {e}")
    
    async def _check_and_alert(self):
        """检查并告警"""
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics:
            return
        
        # 更新级别计数
        self._level_counts[metrics.level] = self._level_counts.get(metrics.level, 0) + 1
        
        # 检测级别变化
        if metrics.level != self._last_alert_level:
            alert = self._create_alert(metrics)
            
            # 记录告警
            self._alert_history.append(alert)
            
            # 触发回调
            if self.alert_callback:
                try:
                    result = self.alert_callback(alert)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"告警回调异常: {e}")
            
            # 记录日志
            if self.enable_logging and metrics.level != 'normal':
                logger.info(f"背压告警: {alert.message}")
            
            self._last_alert_level = metrics.level
    
    def _create_alert(self, metrics: BackpressureMetrics) -> BackpressureAlert:
        """
        创建告警对象
        
        Args:
            metrics: 当前指标
            
        Returns:
            BackpressureAlert: 告警对象
        """
        level_actions = {
            'normal': [],
            'warning': ['log'],
            'danger': ['log', 'reduce_concurrency'],
            'critical': ['log', 'reduce_concurrency', 'pause_enqueuing']
        }
        
        return BackpressureAlert(
            level=metrics.level,
            score=metrics.overall_score,
            message=self._generate_message(metrics),
            timestamp=datetime.now(),
            metrics={
                'queue_usage': round(metrics.queue_usage_ratio, 3),
                'queue_size': metrics.queue_size,
                'queue_max_size': metrics.queue_max_size,
                'enqueue_rate': round(metrics.enqueue_rate, 2),
                'dequeue_rate': round(metrics.dequeue_rate, 2),
                'rate_diff': round(metrics.rate_difference, 2),
                'timeout_rate': round(metrics.timeout_rate, 3),
                'success_rate': round(metrics.success_rate, 3),
                'avg_response_time': round(metrics.avg_response_time, 3)
            },
            actions=level_actions.get(metrics.level, [])
        )
    
    def _generate_message(self, metrics: BackpressureMetrics) -> str:
        """
        生成告警消息
        
        Args:
            metrics: 当前指标
            
        Returns:
            str: 告警消息
        """
        level_zh = {
            'normal': '正常',
            'warning': '警告',
            'danger': '危险',
            'critical': '严重'
        }
        
        parts = [
            f"背压{level_zh.get(metrics.level, metrics.level)}",
            f"评分:{metrics.overall_score:.1f}",
            f"队列:{metrics.queue_usage_ratio*100:.1f}%",
            f"速率差:{metrics.rate_difference:.1f}/s",
            f"超时率:{metrics.timeout_rate*100:.1f}%"
        ]
        
        return " | ".join(parts)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        获取告警摘要
        
        Returns:
            dict: 告警摘要
        """
        if not self._alert_history:
            return {
                'total': 0,
                'by_level': {},
                'latest': None,
                'level_counts': self._level_counts
            }
        
        by_level = {}
        for alert in self._alert_history:
            by_level[alert.level] = by_level.get(alert.level, 0) + 1
        
        latest = self._alert_history[-1]
        
        return {
            'total': len(self._alert_history),
            'by_level': by_level,
            'latest': {
                'level': latest.level,
                'score': latest.score,
                'message': latest.message,
                'timestamp': latest.timestamp.isoformat(),
                'actions': latest.actions
            },
            'level_counts': self._level_counts
        }
    
    def get_alert_history(self) -> List[BackpressureAlert]:
        """
        获取告警历史
        
        Returns:
            list: 告警历史列表
        """
        return list(self._alert_history)
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            dict: 当前状态
        """
        if not self.metrics_collector:
            return {'status': 'not_initialized'}
        
        metrics = self.metrics_collector.get_current_metrics()
        
        if not metrics:
            return {'status': 'no_data'}
        
        return {
            'status': 'running',
            'level': metrics.level,
            'score': metrics.overall_score,
            'queue_usage': metrics.queue_usage_ratio,
            'last_check': datetime.fromtimestamp(metrics.timestamp).isoformat()
        }
    
    def clear_history(self):
        """清除告警历史"""
        self._alert_history.clear()
        self._level_counts = {
            'normal': 0,
            'warning': 0,
            'danger': 0,
            'critical': 0
        }
