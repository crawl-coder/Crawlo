# Extension API Reference

This document provides detailed information about the extension components in the Crawlo framework.

## ExtensionManager Class

The ExtensionManager is responsible for managing and executing extension components.

### Class: ExtensionManager

```python
class ExtensionManager(object):
    def __init__(self, crawler):
        # Initialize the extension manager
        pass
    
    def add_extension(self, extension_class):
        # Add an extension to the manager
        pass
    
    async def fire_event(self, event_name, *args, **kwargs):
        # Fire an event to all registered extensions
        pass
```

#### Parameters

- `crawler` (Crawler): The crawler instance to associate with this extension manager.

#### Methods

##### `__init__(self, crawler)`
Initialize the extension manager with a crawler.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this extension manager.

##### `add_extension(self, extension_class)`
Add an extension to the manager.

**Parameters:**
- `extension_class` (class): The extension class to add.

##### `fire_event(self, event_name, *args, **kwargs)`
Fire an event to all registered extensions.

**Parameters:**
- `event_name` (str): The name of the event to fire.
- `*args`: Positional arguments to pass to the event handlers.
- `**kwargs`: Keyword arguments to pass to the event handlers.

**Returns:**
- `Coroutine`: A coroutine that completes when all event handlers have been executed.

## Base Extension Class

### Class: BaseExtension

The base class for all extension implementations.

```python
class BaseExtension(object):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    @classmethod
    def create_instance(cls, crawler):
        # Create an instance of the extension
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the extension with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this extension.

##### `create_instance(cls, crawler)`
Create an instance of the extension.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this extension.

**Returns:**
- `BaseExtension`: An instance of the extension.

## Built-in Extensions

### Class: LogIntervalExtension

An extension that periodically logs crawler statistics.

```python
class LogIntervalExtension(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def spider_opened(self):
        # Called when a spider is opened
        pass
    
    async def spider_closed(self):
        # Called when a spider is closed
        pass
```

### Class: LogStats

An extension that collects and logs crawler statistics.

```python
class LogStats(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def spider_opened(self):
        # Called when a spider is opened
        pass
    
    async def spider_closed(self):
        # Called when a spider is closed
        pass
```

### Class: CustomLoggerExtension

An extension that initializes and configures the logging system.

```python
class CustomLoggerExtension(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def crawler_started(self):
        # Called when the crawler is started
        pass
```

### Class: MemoryMonitorExtension

An extension that monitors memory usage and warns when thresholds are exceeded.

```python
class MemoryMonitorExtension(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def spider_opened(self):
        # Called when a spider is opened
        pass
    
    async def spider_closed(self):
        # Called when a spider is closed
        pass
```

### Class: RequestRecorderExtension

An extension that records all requests and responses for debugging purposes.

```python
class RequestRecorderExtension(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def request_scheduled(self, request, spider):
        # Called when a request is scheduled
        pass
    
    async def response_downloaded(self, response, request, spider):
        # Called when a response is downloaded
        pass
```

### Class: PerformanceProfilerExtension

An extension that profiles crawler performance and generates reports.

```python
class PerformanceProfilerExtension(BaseExtension):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    async def spider_opened(self):
        # Called when a spider is opened
        pass
    
    async def spider_closed(self):
        # Called when a spider is closed
        pass
```

## Example Usage

```python
from crawlo.extension.extension_manager import ExtensionManager
from crawlo.extension.log_interval import LogIntervalExtension
from crawlo.extension.log_stats import LogStats

# Create extension manager
extension_manager = ExtensionManager(crawler)

# Add extensions
extension_manager.add_extension(LogIntervalExtension)
extension_manager.add_extension(LogStats)

# Fire events
async def fire_spider_opened_event(spider):
    await extension_manager.fire_event('spider_opened', spider=spider)

async def fire_spider_closed_event(spider):
    await extension_manager.fire_event('spider_closed', spider=spider)
```