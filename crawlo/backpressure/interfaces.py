#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Backpressure strategy interface definitions

Provides unified backpressure strategy interfaces and abstract base classes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Dict, Any
from enum import Enum

if TYPE_CHECKING:
    from crawlo.queue.interfaces import IQueue


class PressureLevel(Enum):
    """
    Backpressure level enumeration
    
    Represents the severity of system load.
    """
    NORMAL = "normal"       # Normal load
    WARNING = "warning"     # Warning level
    CRITICAL = "critical"  # Critical level
    FULL = "full"          # Queue is full


@dataclass
class BackpressureMetrics:
    """
    Backpressure metrics data class
    
    Used to collect and pass backpressure-related metric data.
    """
    queue_size: int = 0              # Current queue size
    max_queue_size: int = 0          # Maximum queue size
    utilization: float = 0.0          # Utilization ratio (0-1)
    active: bool = False             # Whether backpressure is currently applied
    level: PressureLevel = PressureLevel.NORMAL  # Current level
    delay: float = 0.0               # Calculated delay in seconds
    timestamp: float = 0.0           # Timestamp
    
    @property
    def utilization_percent(self) -> float:
        """Get utilization percentage"""
        return self.utilization * 100
    
    @property
    def is_critical(self) -> bool:
        """Whether at critical level"""
        return self.level in (PressureLevel.CRITICAL, PressureLevel.FULL)


class IBackpressureStrategy(ABC):
    """
    Backpressure strategy interface
    
    All backpressure strategies must implement this interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get strategy name"""
        pass
    
    @abstractmethod
    async def should_apply(self, queue: 'IQueue') -> bool:
        """
        Determine whether backpressure should be applied
        
        Args:
            queue: Queue instance
            
        Returns:
            bool: Whether backpressure should be applied
        """
        pass
    
    @abstractmethod
    async def calculate_delay(self, queue: 'IQueue') -> float:
        """
        Calculate backpressure delay
        
        Args:
            queue: Queue instance
            
        Returns:
            float: Delay time in seconds
        """
        pass
    
    @abstractmethod
    async def get_level(self, queue: 'IQueue') -> PressureLevel:
        """
        Get current backpressure level
        
        Args:
            queue: Queue instance
            
        Returns:
            PressureLevel: Current level
        """
        pass
    
    @abstractmethod
    async def get_metrics(self, queue: 'IQueue') -> BackpressureMetrics:
        """
        Get backpressure metrics
        
        Args:
            queue: Queue instance
            
        Returns:
            BackpressureMetrics: Metric data
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset strategy state"""
        pass


class BackpressureStrategyConfig:
    """
    Backpressure strategy configuration
    
    Used to configure parameters for various backpressure strategies.
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
        Initialize configuration
        
        Args:
            threshold: Backpressure trigger threshold (0-1)
            warning_threshold: Warning level threshold
            critical_threshold: Critical level threshold
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            check_interval: Check interval in seconds
        """
        self.threshold = threshold
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.check_interval = check_interval
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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
