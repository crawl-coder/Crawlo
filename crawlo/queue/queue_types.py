#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
队列类型枚举定义
"""
from enum import Enum


class QueueType(Enum):
    """
    队列类型枚举
    
    支持的队列类型：
    - MEMORY: 内存队列，适用于单机小规模爬虫
    - REDIS: Redis 队列，适用于分布式爬虫
    - AUTO: 自动选择，根据环境自动选择合适的队列类型
    
    注：DiskQueue 仍存在于 crawlo.queue.disk_queue 模块中，
    但已不在框架中集成，可单独导入使用。
    """
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"  # 保留用于兼容，但不在框架中使用
    AUTO = "auto"
    
    @classmethod
    def from_string(cls, value: str) -> 'QueueType':
        """
        从字符串创建队列类型枚举
        
        Args:
            value: 字符串值
            
        Returns:
            QueueType: 队列类型枚举
        """
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"不支持的队列类型: {value}")
    
    def supports_distributed(self) -> bool:
        """
        检查该队列类型是否支持分布式部署
        
        Returns:
            bool: 是否支持分布式
        """
        return self == QueueType.REDIS
    
    def requires_external_service(self) -> bool:
        """
        检查该队列类型是否需要外部服务
        
        Returns:
            bool: 是否需要外部服务
        """
        return self == QueueType.REDIS


class QueuePriority(Enum):
    """
    队列优先级枚举
    
    用于定义请求的优先级级别
    """
    CRITICAL = 100  # 关键请求
    HIGH = 75       # 高优先级
    NORMAL = 50     # 普通优先级
    LOW = 25        # 低优先级
    BACKGROUND = 0  # 后台任务


class QueueStats:
    """
    队列统计信息
    
    用于收集和报告队列性能指标
    """
    
    def __init__(self):
        self.enqueued_count = 0      # 入队总数
        self.dequeued_count = 0      # 出队总数
        self.rejected_count = 0      # 拒绝总数
        self.overflow_count = 0     # 溢出总数
        self.total_wait_time = 0.0   # 总等待时间
        self.max_queue_size = 0      # 最大队列大小
        self.start_time = None       # 开始时间
        self.end_time = None         # 结束时间
    
    def record_enqueue(self, wait_time: float = 0.0) -> None:
        """记录入队操作"""
        self.enqueued_count += 1
        self.total_wait_time += wait_time
    
    def record_dequeue(self) -> None:
        """记录出队操作"""
        self.dequeued_count += 1
    
    def record_reject(self) -> None:
        """记录拒绝操作"""
        self.rejected_count += 1
    
    def record_overflow(self) -> None:
        """记录溢出操作"""
        self.overflow_count += 1
    
    def update_max_size(self, size: int) -> None:
        """更新最大队列大小"""
        if size > self.max_queue_size:
            self.max_queue_size = size
    
    def mark_start(self) -> None:
        """标记开始时间"""
        import time
        if self.start_time is None:
            self.start_time = time.time()
    
    def mark_end(self) -> None:
        """标记结束时间"""
        import time
        self.end_time = time.time()
    
    @property
    def duration(self) -> float:
        """获取运行时长"""
        import time
        end = self.end_time or time.time()
        start = self.start_time or end
        return end - start
    
    @property
    def throughput(self) -> float:
        """获取吞吐量 (items/second)"""
        duration = self.duration
        if duration > 0:
            return self.dequeued_count / duration
        return 0.0
    
    @property
    def avg_wait_time(self) -> float:
        """获取平均等待时间"""
        if self.enqueued_count > 0:
            return self.total_wait_time / self.enqueued_count
        return 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'enqueued_count': self.enqueued_count,
            'dequeued_count': self.dequeued_count,
            'rejected_count': self.rejected_count,
            'overflow_count': self.overflow_count,
            'max_queue_size': self.max_queue_size,
            'duration': round(self.duration, 2),
            'throughput': round(self.throughput, 2),
            'avg_wait_time': round(self.avg_wait_time, 4),
        }
    
    def __repr__(self) -> str:
        return (
            f"<QueueStats: enqueued={self.enqueued_count}, "
            f"dequeued={self.dequeued_count}, "
            f"rejected={self.rejected_count}, "
            f"throughput={self.throughput:.1f}/s>"
        )


__all__ = [
    'QueueType',
    'QueuePriority',
    'QueueStats',
]
