# Custom Extensions

Extensions are components in the Crawlo framework used to add additional functionality. Through custom extensions, you can implement various functions such as monitoring, statistics, logging, etc.

## Creating Custom Extensions

To create a custom extension, you need to inherit from the `crawlo.extensions.Extension` base class and implement the corresponding methods.

### Basic Structure

```python
from crawlo.extensions import Extension

class CustomExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        # Initialize extension
    
    def open(self):
        # Called when the extension is enabled
        pass
    
    def close(self):
        # Called when the extension is closed
        pass
    
    @classmethod
    def from_crawler(cls, crawler):
        # Create extension instance from crawler instance
        return cls(crawler)
```

### Method Descriptions

#### __init__(self, crawler)

- **Purpose**: Initialize the extension
- **Parameters**:
  - `crawler`: Crawler instance

#### open(self)

- **Purpose**: Called when the extension is enabled, used for initializing resources
- **Return Value**: None

#### close(self)

- **Purpose**: Called when the extension is closed, used for releasing resources
- **Return Value**: None

#### from_crawler(cls, crawler)

- **Purpose**: Class method to create extension instance from crawler instance
- **Parameters**:
  - `crawler`: Crawler instance
- **Return Value**: Extension instance

## Examples

### Statistics Extension

```python
from crawlo.extensions import Extension
from collections import defaultdict

class StatsExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.stats = defaultdict(int)
    
    def open(self):
        # Register event listeners
        self.crawler.signals.connect(self.on_request_sent, signal='request_sent')
        self.crawler.signals.connect(self.on_response_received, signal='response_received')
        self.crawler.signals.connect(self.on_item_scraped, signal='item_scraped')
    
    def close(self):
        # Output statistics
        print("Crawling Statistics:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
    
    def on_request_sent(self, request):
        self.stats['requests_sent'] += 1
    
    def on_response_received(self, response):
        self.stats['responses_received'] += 1
        self.stats[f'status_{response.status_code}'] += 1
    
    def on_item_scraped(self, item):
        self.stats['items_scraped'] += 1
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

### Logging Extension

```python
from crawlo.extensions import Extension
import logging

class LoggingExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = logging.getLogger(__name__)
    
    def open(self):
        # Register event listeners
        self.crawler.signals.connect(self.on_spider_opened, signal='spider_opened')
        self.crawler.signals.connect(self.on_spider_closed, signal='spider_closed')
        self.crawler.signals.connect(self.on_request_sent, signal='request_sent')
    
    def on_spider_opened(self, spider):
        self.logger.info(f"Spider {spider.name} opened")
    
    def on_spider_closed(self, spider):
        self.logger.info(f"Spider {spider.name} closed")
    
    def on_request_sent(self, request):
        self.logger.debug(f"Sending request to {request.url}")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

### Memory Monitor Extension

```python
from crawlo.extensions import Extension
import psutil
import threading
import time

class MemoryMonitorExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.monitoring = False
        self.monitor_thread = None
        self.threshold = 500 * 1024 * 1024  # 500MB
    
    def open(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_memory)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def close(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_memory(self):
        while self.monitoring:
            memory_usage = psutil.Process().memory_info().rss
            if memory_usage > self.threshold:
                self.crawler.logger.warning(f"High memory usage: {memory_usage / 1024 / 1024:.2f} MB")
            time.sleep(10)  # Check every 10 seconds
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
```

## Configuring Extensions

Enable custom extensions in the configuration file:

```python
# settings.py
EXTENSIONS = {
    'myproject.extensions.StatsExtension': 100,
    'myproject.extensions.LoggingExtension': 200,
    'myproject.extensions.MemoryMonitorExtension': 300,
}
```

The number for extensions represents the priority, with smaller numbers having higher priority.

## Best Practices

1. **Single Responsibility**: Each extension should only be responsible for one function
2. **Event-Driven**: Use the signal system to listen for and respond to events
3. **Resource Management**: Correctly open and close resources
4. **Performance Considerations**: Avoid performing time-consuming operations in extensions
5. **Exception Handling**: Properly handle exceptions in extensions
6. **Testing**: Write unit tests for extensions