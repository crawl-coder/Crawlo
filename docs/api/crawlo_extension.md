# crawlo.extension

Extension module for the Crawlo framework.

## Overview

The extension module provides a way to add additional functionality to the Crawlo framework. Extensions can hook into various parts of the crawling process to add monitoring, logging, or other features.

## Classes

### Extension

Base class for all extensions.

#### `__init__(self, crawler)`

Initialize the extension.

**Parameters:**
- `crawler` (Crawler): The crawler instance

#### `from_crawler(cls, crawler)`

Create an extension instance from a crawler.

**Parameters:**
- `crawler` (Crawler): The crawler instance

**Returns:**
- Extension instance

#### `open(self)`

Called when the extension is opened/started.

#### `close(self)`

Called when the extension is closed/stopped.

## Built-in Extensions

### LogStatsExtension

Logs basic statistics about the crawling process.

### LogIntervalExtension

Logs periodic status updates during crawling.

### HealthCheckExtension

Provides health check functionality for the crawler.

## Usage Example

```python
from crawlo.extension import Extension

class MyExtension(Extension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.stats = crawler.stats
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def open(self):
        print("Extension opened")
    
    def close(self):
        print("Extension closed")

# Register extension in settings
EXTENSIONS = {
    'myproject.extensions.MyExtension': 300,
}
```