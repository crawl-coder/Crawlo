# crawlo.pipelines

Pipeline module for the Crawlo framework.

## Overview

The pipeline module provides a way to process extracted items. Pipelines can clean, validate, and store data in various ways.

## Classes

### Pipeline

Base class for all pipelines.

#### `__init__(self, crawler)`

Initialize the pipeline.

**Parameters:**
- `crawler` (Crawler): The crawler instance

#### `process_item(self, item, spider)`

Process an item.

**Parameters:**
- `item` (Item): The item to process
- `spider` (Spider): The spider instance

**Returns:**
- Processed item

#### `open_spider(self, spider)`

Called when a spider is opened.

**Parameters:**
- `spider` (Spider): The spider instance

#### `close_spider(self, spider)`

Called when a spider is closed.

**Parameters:**
- `spider` (Spider): The spider instance

## Built-in Pipelines

### ConsolePipeline

Outputs items to the console.

### JsonPipeline

Outputs items to a JSON file.

### CsvPipeline

Outputs items to a CSV file.

### RedisDedupPipeline

Deduplicates items using Redis.

### MemoryDedupPipeline

Deduplicates items using memory.

### BloomDedupPipeline

Deduplicates items using a Bloom filter.

### DatabasePipelines

Various database pipelines for storing items.

## Usage Example

```python
from crawlo.pipelines import Pipeline

class MyPipeline(Pipeline):
    def process_item(self, item, spider):
        # Process the item
        item['processed'] = True
        return item
    
    def open_spider(self, spider):
        # Initialize when spider opens
        print(f"Spider {spider.name} opened")
    
    def close_spider(self, spider):
        # Clean up when spider closes
        print(f"Spider {spider.name} closed")

# Register pipeline in settings
ITEM_PIPELINES = {
    'myproject.pipelines.MyPipeline': 300,
}
```