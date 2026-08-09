"""队列管理模块"""
from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.queue_manager import register_queue_backend, unregister_queue_backend
from crawlo.queue.config import QueueConfig
from crawlo.queue.queue_types import QueueType
from crawlo.queue.backends.memory import SpiderPriorityQueue
from crawlo.queue.backends.disk import DiskQueue
from crawlo.queue.backends.redis_priority import RedisPriorityQueue
from crawlo.queue.backends.redis_stream import RedisStreamQueue
from crawlo.queue.task_tracker import TaskTracker, TaskResult

__all__ = [
    'QueueManager',
    'register_queue_backend',
    'unregister_queue_backend',
    'QueueConfig',
    'QueueType',
    'SpiderPriorityQueue',
    'DiskQueue',
    'RedisPriorityQueue',
    'RedisStreamQueue',
    'TaskTracker',
    'TaskResult',
]
