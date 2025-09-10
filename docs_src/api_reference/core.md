# Core API Reference

This document provides detailed information about the core components of the Crawlo framework.

## Engine

The Engine is the central component that coordinates the crawling process, managing the scheduler, downloader, and processor.

### Class: Engine

```python
class Engine(object):
    def __init__(self, crawler):
        # Initialize the engine with a crawler instance
        pass
    
    async def start(self):
        # Start the crawling process
        pass
    
    async def stop(self):
        # Stop the crawling process
        pass
    
    def pause(self):
        # Pause the crawling process
        pass
    
    def resume(self):
        # Resume the crawling process
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the engine with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this engine.

##### `start()`
Start the crawling process asynchronously.

**Returns:**
- `Coroutine`: A coroutine that completes when crawling starts.

##### `stop()`
Stop the crawling process asynchronously.

**Returns:**
- `Coroutine`: A coroutine that completes when crawling stops.

##### `pause()`
Pause the crawling process.

##### `resume()`
Resume the crawling process.

## Scheduler

The Scheduler manages the request queue and handles request deduplication.

### Class: Scheduler

```python
class Scheduler(object):
    def __init__(self, crawler):
        # Initialize the scheduler with a crawler instance
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
Initialize the scheduler with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this scheduler.

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

## Processor

The Processor handles the extraction of data from responses and passes items through the pipeline.

### Class: Processor

```python
class Processor(object):
    def __init__(self, crawler):
        # Initialize the processor with a crawler instance
        pass
    
    async def process_response(self, response):
        # Process a response and extract items
        pass
    
    async def process_item(self, item, spider):
        # Process an item through the pipeline
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the processor with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this processor.

##### `process_response(self, response)`
Process a response and extract items.

**Parameters:**
- `response` (Response): The response to process.

**Returns:**
- `Coroutine`: A coroutine that processes the response.

##### `process_item(self, item, spider)`
Process an item through the pipeline.

**Parameters:**
- `item` (Item): The item to process.
- `spider` (Spider): The spider that generated the item.

**Returns:**
- `Coroutine`: A coroutine that processes the item.

## Crawler

The Crawler is the main runtime instance that manages the lifecycle of a spider and its associated components.

### Class: Crawler

```python
class Crawler(object):
    def __init__(self, spidercls, settings=None):
        # Initialize the crawler with a spider class and settings
        pass
    
    async def crawl(self, *args, **kwargs):
        # Start crawling with the given arguments
        pass
    
    async def stop(self):
        # Stop the crawling process
        pass
```

#### Methods

##### `__init__(self, spidercls, settings=None)`
Initialize the crawler with a spider class and optional settings.

**Parameters:**
- `spidercls` (class): The spider class to instantiate.
- `settings` (dict, optional): Configuration settings for the crawler.

##### `crawl(self, *args, **kwargs)`
Start crawling with the given arguments, which are passed to the spider's start_requests method.

**Parameters:**
- `*args`: Positional arguments to pass to the spider.
- `**kwargs`: Keyword arguments to pass to the spider.

**Returns:**
- `Coroutine`: A coroutine that completes when crawling finishes.

##### `stop(self)`
Stop the crawling process.

**Returns:**
- `Coroutine`: A coroutine that completes when the crawler stops.