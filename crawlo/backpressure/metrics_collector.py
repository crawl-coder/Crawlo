"""
多维度背压指标采集器

采集三大类指标：
1. 队列指标：大小、使用率、增长速率
2. 吞吐指标：入队速率、出队速率、速率差
3. 性能指标：响应时间、超时率、成功率

Author: Crawlo Framework Team
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Deque, Callable, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class BackpressureMetrics:
    """背压指标数据类"""
    
    # 队列指标
    queue_size: int = 0
    queue_max_size: int = 0
    queue_usage_ratio: float = 0.0
    queue_growth_rate: float = 0.0  # 每秒增长量
    
    # 吞吐指标
    enqueue_rate: float = 0.0       # 入队速率（个/秒）
    dequeue_rate: float = 0.0       # 出队速率（个/秒）
    rate_difference: float = 0.0     # 速率差（入-出）
    
    # 性能指标
    avg_response_time: float = 0.0   # 平均响应时间（秒）
    timeout_rate: float = 0.0       # 超时率
    success_rate: float = 0.0       # 成功率
    
    # 综合评分
    overall_score: float = 0.0      # 0-100的综合评分
    level: str = 'normal'           # normal/warning/danger/critical
    
    # 时间戳
    timestamp: float = field(default_factory=time.time)


class BackpressureMetricsCollector:
    """
    背压指标采集器
    
    实时采集队列、吞吐、性能三大类指标，
    计算综合评分，为背压决策提供数据支持。
    """
    
    def __init__(
        self,
        window_size: int = 30,
        collect_interval: int = 1,
        queue_weights: tuple = (0.4, 0.3, 0.3),
        score_thresholds: tuple = (50, 70, 85),
        queue_size_func: Optional[Callable[[], Any]] = None,
        queue_max_size_func: Optional[Callable[[], Any]] = None,
        max_history: int = 1000,
        max_response_times: int = 1000
    ):
        """
        初始化采集器
        
        Args:
            window_size: 采样窗口大小（秒）
            collect_interval: 采集间隔（秒）
            queue_weights: (队列权重, 吞吐权重, 性能权重)
            score_thresholds: (警告阈值, 危险阈值, 严重阈值)
            queue_size_func: 获取队列大小的函数
            queue_max_size_func: 获取队列最大大小的函数
            max_history: 最大历史记录数（内存优化，默认1000）
            max_response_times: 最大响应时间记录数（内存优化，默认1000）
        """
        self.window_size = window_size
        self.collect_interval = collect_interval
        self.queue_weight, self.throughput_weight, self.perf_weight = queue_weights
        self.warning_threshold, self.danger_threshold, self.critical_threshold = score_thresholds
        
        # 队列信息获取函数
        self._queue_size_func = queue_size_func
        self._queue_max_size_func = queue_max_size_func
        
        # 指标历史记录（可配置大小）
        self._history: Deque[BackpressureMetrics] = deque(maxlen=max_history)
        
        # 实时计数器
        self._enqueue_count = 0
        self._dequeue_count = 0
        self._timeout_count = 0
        self._success_count = 0
        self._total_count = 0
        self._response_times: Deque[float] = deque(maxlen=max_response_times)
        
        # 采集任务
        self._collect_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        
        # 上次采集的数据
        self._last_metrics: Optional[BackpressureMetrics] = None
        self._last_collect_time: float = time.time()
    
    async def start(self):
        """启动采集器"""
        self._running = True
        self._collect_task = asyncio.create_task(self._collect_loop())
        logger.debug(
            f"背压指标采集器已启动（窗口={self.window_size}s, 间隔={self.collect_interval}s）"
        )
    
    async def stop(self):
        """停止采集器"""
        self._running = False
        if self._collect_task:
            self._collect_task.cancel()
            try:
                await self._collect_task
            except asyncio.CancelledError:
                pass
        logger.debug("背压指标采集器已停止")
    
    async def _collect_loop(self):
        """采集循环"""
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.collect_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指标采集异常: {e}")
    
    async def _collect_metrics(self):
        """采集当前指标"""
        try:
            async with self._lock:
                # 获取队列信息
                queue_size = await self._get_queue_size()
                queue_max_size = await self._get_queue_max_size()
                
                # 防止除零
                if queue_max_size <= 0:
                    queue_max_size = 1
                
                # 计算队列指标
                queue_usage_ratio = queue_size / queue_max_size if queue_max_size > 0 else 0.0
                queue_growth_rate = self._calculate_growth_rate(queue_size)
                
                # 计算吞吐指标
                current_time = time.time()
                elapsed = current_time - self._last_collect_time
                if elapsed > 0:
                    enqueue_rate = self._enqueue_count / elapsed
                    dequeue_rate = self._dequeue_count / elapsed
                    rate_difference = enqueue_rate - dequeue_rate
                else:
                    enqueue_rate = dequeue_rate = rate_difference = 0.0
                
                # 重置计数器
                self._enqueue_count = 0
                self._dequeue_count = 0
                self._last_collect_time = current_time
                
                # 计算性能指标
                avg_response_time = (
                    sum(self._response_times) / len(self._response_times) 
                    if self._response_times else 0.0
                )
                timeout_rate = (
                    self._timeout_count / self._total_count 
                    if self._total_count > 0 else 0.0
                )
                success_rate = (
                    self._success_count / self._total_count 
                    if self._total_count > 0 else 0.0
                )
                
                # 计算综合评分
                queue_score = queue_usage_ratio * 100
                throughput_score = min(abs(rate_difference) * 10, 100)
                perf_score = (1 - timeout_rate) * 50 + success_rate * 50
                
                overall_score = (
                    queue_score * self.queue_weight +
                    throughput_score * self.throughput_weight +
                    perf_score * self.perf_weight
                )
                
                # 确定级别
                if overall_score >= self.critical_threshold:
                    level = 'critical'
                elif overall_score >= self.danger_threshold:
                    level = 'danger'
                elif overall_score >= self.warning_threshold:
                    level = 'warning'
                else:
                    level = 'normal'
                
                # 创建指标对象
                metrics = BackpressureMetrics(
                    queue_size=queue_size,
                    queue_max_size=queue_max_size,
                    queue_usage_ratio=queue_usage_ratio,
                    queue_growth_rate=queue_growth_rate,
                    enqueue_rate=enqueue_rate,
                    dequeue_rate=dequeue_rate,
                    rate_difference=rate_difference,
                    avg_response_time=avg_response_time,
                    timeout_rate=timeout_rate,
                    success_rate=success_rate,
                    overall_score=overall_score,
                    level=level,
                    timestamp=current_time
                )
                
                # 保存历史
                self._history.append(metrics)
                self._last_metrics = metrics
                
                # 记录日志（警告级别以上）
                if level != 'normal':
                    logger.info(
                        f"背压{level.upper()} | 评分:{overall_score:.1f} | "
                        f"队列:{queue_size}/{queue_max_size}({queue_usage_ratio*100:.1f}%) | "
                        f"速率差:{rate_difference:.1f}/s | 超时率:{timeout_rate*100:.1f}%"
                    )
        except Exception as e:
            logger.error(f"指标采集异常: {e}", exc_info=True)
    
    def _calculate_growth_rate(self, current_size: int) -> float:
        """计算队列增长速率"""
        if len(self._history) < 2:
            return 0.0
        
        recent = list(self._history)[-min(10, len(self._history)):]
        if len(recent) < 2:
            return 0.0
        
        time_diff = recent[-1].timestamp - recent[0].timestamp
        size_diff = recent[-1].queue_size - recent[0].queue_size
        
        return size_diff / time_diff if time_diff > 0 else 0.0
    
    async def _get_queue_size(self) -> int:
        """获取队列大小"""
        if self._queue_size_func:
            result = self._queue_size_func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return 0
    
    async def _get_queue_max_size(self) -> int:
        """获取队列最大大小"""
        if self._queue_max_size_func:
            result = self._queue_max_size_func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return 1
    
    # 外部调用接口
    def record_enqueue(self):
        """记录一次入队"""
        self._enqueue_count += 1
    
    def record_dequeue(self):
        """记录一次出队"""
        self._dequeue_count += 1
    
    def record_response(self, response_time: float, is_timeout: bool, is_success: bool):
        """
        记录一次响应
        
        Args:
            response_time: 响应时间（秒）
            is_timeout: 是否超时
            is_success: 是否成功
        """
        self._response_times.append(response_time)
        self._total_count += 1
        if is_timeout:
            self._timeout_count += 1
        if is_success:
            self._success_count += 1
    
    def get_current_metrics(self) -> Optional[BackpressureMetrics]:
        """获取当前指标"""
        return self._last_metrics
    
    def get_score(self) -> float:
        """获取当前综合评分"""
        return self._last_metrics.overall_score if self._last_metrics else 0.0
    
    def get_level(self) -> str:
        """获取当前级别"""
        return self._last_metrics.level if self._last_metrics else 'normal'
    
    def get_history(self) -> list:
        """获取历史指标"""
        return list(self._history)
