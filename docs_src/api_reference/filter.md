# Filter API Reference

This document provides detailed information about the filter components in the Crawlo framework.

## BaseFilter Class

The base class for all filter implementations.

### Class: BaseFilter

```python
class BaseFilter(object):
    def __init__(self, crawler):
        # Initialize the base filter
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen before
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen
        pass
    
    async def clear(self):
        # Clear the filter
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the base filter with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this filter.

##### `request_seen(self, request)`
Check if a request has been seen before.

**Parameters:**
- `request` (Request): The request to check.

**Returns:**
- `Coroutine`: A coroutine that resolves to a boolean indicating if the request has been seen.

##### `mark_request_seen(self, request)`
Mark a request as seen.

**Parameters:**
- `request` (Request): The request to mark as seen.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is marked as seen.

##### `clear(self)`
Clear the filter.

**Returns:**
- `Coroutine`: A coroutine that completes when the filter is cleared.

## MemoryFilter Class

An in-memory filter implementation using Python sets.

### Class: MemoryFilter

```python
class MemoryFilter(BaseFilter):
    def __init__(self, crawler):
        # Initialize the memory filter
        pass
```

#### Methods

Inherits all methods from BaseFilter.

## AioRedisFilter Class

A Redis-based filter implementation using async Redis connections.

### Class: AioRedisFilter

```python
class AioRedisFilter(BaseFilter):
    def __init__(self, crawler, module_name="default"):
        # Initialize the Redis filter
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen before using Redis
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen using Redis
        pass
    
    async def clear(self):
        # Clear the Redis filter
        pass
```

#### Parameters

- `crawler` (Crawler): The crawler instance to associate with this filter.
- `module_name` (str, optional): The module name for Redis key generation. Defaults to "default".

#### Methods

##### `__init__(self, crawler, module_name="default")`
Initialize the Redis filter with a crawler and module name.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this filter.
- `module_name` (str, optional): The module name for Redis key generation. Defaults to "default".

##### `request_seen(self, request)`
Check if a request has been seen before using Redis.

**Parameters:**
- `request` (Request): The request to check.

**Returns:**
- `Coroutine`: A coroutine that resolves to a boolean indicating if the request has been seen.

##### `mark_request_seen(self, request)`
Mark a request as seen using Redis.

**Parameters:**
- `request` (Request): The request to mark as seen.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is marked as seen.

##### `clear(self)`
Clear the Redis filter.

**Returns:**
- `Coroutine`: A coroutine that completes when the filter is cleared.

## FilterManager Class

A manager class for handling different filter implementations.

### Class: FilterManager

```python
class FilterManager(object):
    def __init__(self, crawler):
        # Initialize the filter manager
        pass
    
    def create_filter(self, filter_type, *args, **kwargs):
        # Create a filter of the specified type
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen by the active filter
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen by the active filter
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the filter manager with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this filter manager.

##### `create_filter(self, filter_type, *args, **kwargs)`
Create a filter of the specified type.

**Parameters:**
- `filter_type` (str): The type of filter to create ('memory' or 'redis').
- `*args`: Positional arguments to pass to the filter constructor.
- `**kwargs`: Keyword arguments to pass to the filter constructor.

**Returns:**
- `BaseFilter`: A filter instance of the specified type.

##### `request_seen(self, request)`
Check if a request has been seen by the active filter.

**Parameters:**
- `request` (Request): The request to check.

**Returns:**
- `Coroutine`: A coroutine that resolves to a boolean indicating if the request has been seen.

##### `mark_request_seen(self, request)`
Mark a request as seen by the active filter.

**Parameters:**
- `request` (Request): The request to mark as seen.

**Returns:**
- `Coroutine`: A coroutine that completes when the request is marked as seen.

## Example Usage

```python
from crawlo.filters.base_filter import BaseFilter
from crawlo.filters.memory_filter import MemoryFilter
from crawlo.filters.aioredis_filter import AioRedisFilter
from crawlo.filters.filter_manager import FilterManager

# Using FilterManager
filter_manager = FilterManager(crawler)
filter_instance = filter_manager.create_filter('redis', module_name='my_spider')

# Directly using AioRedisFilter
redis_filter = AioRedisFilter(crawler, module_name='my_spider')

# Directly using MemoryFilter
memory_filter = MemoryFilter(crawler)

# Checking if a request has been seen
async def check_request(request):
    if await filter_instance.request_seen(request):
        print("Request already seen")
    else:
        await filter_instance.mark_request_seen(request)
        print("Request marked as seen")
```