# Queue API Reference

This document provides detailed information about the queue components in the Crawlo framework.

## QueueManager Class

The QueueManager is responsible for managing different types of queues based on the configuration.

### Class: QueueManager

```python
class QueueManager(object):
    def __init__(self, crawler):
        # Initialize the queue manager with a crawler
        pass
    
    def create_queue(self, queue_type, *args, **kwargs):
        # Create a queue of the specified type
        pass
    
    async def enqueue_request(self, request):
        # Add a request to the queue
        pass
    
    async def next_request(self):
        # Get the next request from the queue
        pass
    
    async def has_pending_requests(self):
        # Check if there are pending requests
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the queue manager with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this queue manager.

##### `create_queue(self, queue_type, *args, **kwargs)`
Create a queue of the specified type.

**Parameters:**
- `queue_type` (str): The type of queue to create ('memory' or 'redis').
- `*args`: Positional arguments to pass to the queue constructor.
- `**kwargs`: Keyword arguments to pass to the queue constructor.

**Returns:**
- `BaseQueue`: A queue instance of the specified type.

##### `enqueue_request(self, request)`
Add a request to the queue.

**Parameters:**
- `request` (Request): The request to enqueue.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is enqueued.

##### `next_request(self)`
Get the next request from the queue.

**Returns:**
- `Coroutine`: A coroutine that resolves to the next Request object or None.

##### `has_pending_requests(self)`
Check if there are pending requests in the queue.

**Returns:**
- `Coroutine`: A coroutine that resolves to a boolean indicating if there are pending requests.

## BaseQueue Class

The base class for all queue implementations.

### Class: BaseQueue

```python
class BaseQueue(object):
    def __init__(self, crawler):
        # Initialize the base queue
        pass
    
    async def push(self, request):
        # Push a request to the queue
        pass
    
    async def pop(self):
        # Pop a request from the queue
        pass
    
    async def peek(self):
        # Peek at the next request without removing it
        pass
    
    async def size(self):
        # Get the size of the queue
        pass
    
    async def clear(self):
        # Clear the queue
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the base queue with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this queue.

##### `push(self, request)`
Push a request to the queue.

**Parameters:**
- `request` (Request): The request to push.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is pushed.

##### `pop(self)`
Pop a request from the queue.

**Returns:**
- `Coroutine`: A coroutine that resolves to the next Request object or None.

##### `peek(self)`
Peek at the next request without removing it.

**Returns:**
- `Coroutine`: A coroutine that resolves to the next Request object or None.

##### `size(self)`
Get the size of the queue.

**Returns:**
- `Coroutine`: A coroutine that resolves to the size of the queue.

##### `clear(self)`
Clear the queue.

**Returns:**
- `Coroutine`: A coroutine that completes when the queue is cleared.

## MemoryQueue Class

An in-memory queue implementation.

### Class: MemoryQueue

```python
class MemoryQueue(BaseQueue):
    def __init__(self, crawler):
        # Initialize the memory queue
        pass
```

#### Methods

Inherits all methods from BaseQueue.

## RedisPriorityQueue Class

A Redis-based priority queue implementation using sorted sets.

### Class: RedisPriorityQueue

```python
class RedisPriorityQueue(BaseQueue):
    def __init__(self, crawler, module_name="default"):
        # Initialize the Redis priority queue
        pass
    
    async def push(self, request):
        # Push a request to the Redis queue
        pass
    
    async def pop(self):
        # Pop a request from the Redis queue
        pass
    
    async def ack(self, request):
        # Acknowledge that a request has been processed
        pass
    
    async def fail(self, request):
        # Mark a request as failed
        pass
```

#### Parameters

- `crawler` (Crawler): The crawler instance to associate with this queue.
- `module_name` (str, optional): The module name for Redis key generation. Defaults to "default".

#### Methods

##### `__init__(self, crawler, module_name="default")`
Initialize the Redis priority queue with a crawler and module name.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this queue.
- `module_name` (str, optional): The module name for Redis key generation. Defaults to "default".

##### `push(self, request)`
Push a request to the Redis queue.

**Parameters:**
- `request` (Request): The request to push.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is pushed.

##### `pop(self)`
Pop a request from the Redis queue.

**Returns:**
- `Coroutine`: A coroutine that resolves to the next Request object or None.

##### `ack(self, request)`
Acknowledge that a request has been processed.

**Parameters:**
- `request` (Request): The request to acknowledge.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is acknowledged.

##### `fail(self, request)`
Mark a request as failed.

**Parameters:**
- `request` (Request): The request to mark as failed.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is marked as failed.

## PQueue Class

A priority queue implementation based on Python's heapq.

### Class: PQueue

```python
class PQueue(BaseQueue):
    def __init__(self, crawler):
        # Initialize the priority queue
        pass
```

#### Methods

Inherits all methods from BaseQueue.

## Example Usage

```python
from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.queue.pqueue import PQueue

# Using QueueManager
queue_manager = QueueManager(crawler)
queue = queue_manager.create_queue('redis', module_name='my_spider')

# Directly using RedisPriorityQueue
redis_queue = RedisPriorityQueue(crawler, module_name='my_spider')

# Directly using PQueue (memory queue)
memory_queue = PQueue(crawler)
```