"""队列管理模块"""
from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.config import QueueConfig
from crawlo.queue.queue_types import QueueType
from crawlo.queue.memory_queue import SpiderPriorityQueue
from crawlo.queue.task_tracker import TaskTracker, TaskResult

__all__ = [
    'QueueManager',
    'QueueConfig',
    'QueueType',
    'SpiderPriorityQueue',
    'TaskTracker',
    'TaskResult',
]