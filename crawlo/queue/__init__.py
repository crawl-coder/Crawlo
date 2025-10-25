"""队列管理模块"""
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType
from crawlo.queue.pqueue import SpiderPriorityQueue

__all__ = [
    'QueueManager',
    'QueueConfig',
    'QueueType',
    'SpiderPriorityQueue',
]