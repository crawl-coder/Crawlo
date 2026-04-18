#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
背压策略接口定义

提供统一的背压策略接口和抽象基类。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from crawlo.queue.interfaces import IQueue


class PressureLevel(Enum):
    """
    背压级别枚举
    
    表示系统负载的严重程度。
    """
    NORMAL = "normal"       # 正常负载
    WARNING = "warning"     # 警告级别
    CRITICAL = "critical"  # 危险级别
    FULL = "full"          # 队列已满


@dataclass
class BackpressureMetrics:
    """
    背压指标数据类
    
    用于收集和传递背压相关的指标数据。
    """
    queue_size: int = 0              # 当前队列大小
    max_queue_size: int = 0          # 最大队列大小
    utilization: float = 0.0          # 使用率 (0-1)
    active: bool = False             # 是否正在应用背压
    level: PressureLevel = PressureLevel.NORMAL  # 当前级别
    delay: float = 0.0               # 计算的延迟（秒）
    timestamp: float = 0.0           # 时间戳
    
    @property
    def utilization_percent(self) -> float:
        """获取使用率百分比"""
        return self.utilization * 100
    
    @property
    def is_critical(self) -> bool:
        """是否处于危险级别"""
        return self.level in (PressureLevel.CRITICAL, PressureLevel.FULL)


class IBackpressureStrategy(ABC):
    """
    背压策略接口
    
    所有背压策略必须实现此接口。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """获取策略名称"""
        pass
    
    @abstractmethod
    async def should_apply(self, queue: 'IQueue') -> bool:
        """
        判断是否应该应用背压
        
        Args:
            queue: 队列实例
            
        Returns:
            bool: 是否应该应用背压
        """
        pass
    
    @abstractmethod
    async def calculate_delay(self, queue: 'IQueue') -> float:
        """
        计算背压延迟
        
        Args:
            queue: 队列实例
            
        Returns:
            float: 延迟时间（秒）
        """
        pass
    
    @abstractmethod
    async def get_level(self, queue: 'IQueue') -> PressureLevel:
        """
        获取当前背压级别
        
        Args:
            queue: 队列实例
            
        Returns:
            PressureLevel: 当前级别
        """
        pass
    
    @abstractmethod
    async def get_metrics(self, queue: 'IQueue') -> BackpressureMetrics:
        """
        获取背压指标
        
        Args:
            queue: 队列实例
            
        Returns:
            BackpressureMetrics: 指标数据
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """重置策略状态"""
        pass


class BackpressureStrategyConfig:
    """
    背压策略配置
    
    用于配置各种背压策略的参数。
    """
    
    def __init__(
        self,
        threshold: float = 0.8,
        warning_threshold: float = 0.7,
        critical_threshold: float = 0.9,
        base_delay: float = 0.1,
        max_delay: float = 5.0,
        check_interval: float = 0.1,
    ):
        """
        初始化配置
        
        Args:
            threshold: 背压触发阈值 (0-1)
            warning_threshold: 警告级别阈值
            critical_threshold: 危险级别阈值
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            check_interval: 检查间隔（秒）
        """
        self.threshold = threshold
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.check_interval = check_interval
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'threshold': self.threshold,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay,
            'check_interval': self.check_interval,
        }


__all__ = [
    'PressureLevel',
    'BackpressureMetrics',
    'IBackpressureStrategy',
    'BackpressureStrategyConfig',
]
