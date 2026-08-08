#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
队列层异常定义
=============
队列满、空、关闭、超时等异常。

与 queue/interfaces.py 同目录，供 IQueue 实现类使用。
"""
from crawlo.core.errors import ScheduleException


# ============= 队列异常 =============
class QueueFullError(ScheduleException):
    """队列已满错误"""

    def __init__(self, queue_name: str = "", size: int = 0) -> None:
        message = f"Queue '{queue_name}' is full (size: {size})"
        super().__init__(message)
        self.queue_name = queue_name
        self.size = size


class QueueFullTimeout(ScheduleException):
    """队列满且阻塞等待超时。

    Phase 2：背压双层合并后，``QueueManager.put`` 在队列满时阻塞等待，
    超时后抛出此异常而非隐式 ``return False``，把"丢弃"决策权交给调用方。

    Attributes:
        queue_name: 队列名称
        waited_seconds: 实际等待的秒数
        queue_size: 超时时的队列大小
        max_size: 队列最大容量
    """

    def __init__(
        self,
        queue_name: str = "",
        waited_seconds: float = 0.0,
        queue_size: int = 0,
        max_size: int = 0,
    ) -> None:
        self.queue_name = queue_name
        self.waited_seconds = waited_seconds
        self.queue_size = queue_size
        self.max_size = max_size
        message = (
            f"Queue '{queue_name}' full and wait timed out after "
            f"{waited_seconds:.1f}s (size={queue_size}/{max_size})"
        )
        super().__init__(message)


class QueueEmptyError(ScheduleException):
    """队列为空错误"""

    def __init__(self, queue_name: str = "") -> None:
        message = f"Queue '{queue_name}' is empty"
        super().__init__(message)
        self.queue_name = queue_name


class QueueClosedError(ScheduleException):
    """队列已关闭异常"""
    pass


# ============= 导出 =============
__all__ = [
    'QueueFullError',
    'QueueFullTimeout',
    'QueueEmptyError',
    'QueueClosedError',
]
