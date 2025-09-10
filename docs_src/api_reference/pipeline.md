# Pipeline API Reference

This document provides detailed information about the pipeline components in the Crawlo framework.

## PipelineManager Class

The PipelineManager is responsible for managing and executing pipeline components.

### Class: PipelineManager

```python
class PipelineManager(object):
    def __init__(self, crawler, pipeline_classes):
        # Initialize the pipeline manager
        pass
    
    async def process_item(self, item, spider):
        # Process an item through all pipelines
        pass
```

#### Parameters

- `crawler` (Crawler): The crawler instance to associate with this pipeline manager.
- `pipeline_classes` (list): A list of pipeline class paths to load.

#### Methods

##### `__init__(self, crawler, pipeline_classes)`
Initialize the pipeline manager with a crawler and pipeline classes.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this pipeline manager.
- `pipeline_classes` (list): A list of pipeline class paths to load.

##### `process_item(self, item, spider)`
Process an item through all pipelines in order.

**Parameters:**
- `item` (Item): The item to process.
- `spider` (Spider): The spider that generated the item.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed item.

## Base Pipeline Classes

### Class: BasePipeline

The base class for all pipeline implementations.

```python
class BasePipeline(object):
    def __init__(self, crawler):
        # Initialize the pipeline
        pass
    
    async def process_item(self, item, spider):
        # Process an item
        pass
    
    async def open_spider(self, spider):
        # Called when the spider is opened
        pass
    
    async def close_spider(self, spider):
        # Called when the spider is closed
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the pipeline with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this pipeline.

##### `process_item(self, item, spider)`
Process an item that has been extracted by a spider.

**Parameters:**
- `item` (Item): The item to process.
- `spider` (Spider): The spider that generated the item.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed item.

##### `open_spider(self, spider)`
Called when the spider is opened.

**Parameters:**
- `spider` (Spider): The spider that is being opened.

**Returns:**
- `Coroutine`: A coroutine that completes when the spider is opened.

##### `close_spider(self, spider)`
Called when the spider is closed.

**Parameters:**
- `spider` (Spider): The spider that is being closed.

**Returns:**
- `Coroutine`: A coroutine that completes when the spider is closed.

## Built-in Pipelines

### Class: ConsolePipeline

A pipeline that outputs items to the console.

```python
class ConsolePipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Output item to console
        pass
```

### Class: JsonPipeline

A pipeline that saves items to JSON files.

```python
class JsonPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Save item to JSON file
        pass
    
    async def open_spider(self, spider):
        # Open JSON file for writing
        pass
    
    async def close_spider(self, spider):
        # Close JSON file
        pass
```

### Class: CsvPipeline

A pipeline that saves items to CSV files.

```python
class CsvPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Save item to CSV file
        pass
    
    async def open_spider(self, spider):
        # Open CSV file for writing
        pass
    
    async def close_spider(self, spider):
        # Close CSV file
        pass
```

### Class: AsyncmyMySQLPipeline

A pipeline that stores items in a MySQL database using asyncmy.

```python
class AsyncmyMySQLPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Store item in MySQL database
        pass
    
    async def open_spider(self, spider):
        # Connect to MySQL database
        pass
    
    async def close_spider(self, spider):
        # Close MySQL database connection
        pass
```

### Class: MongoPipeline

A pipeline that stores items in a MongoDB database.

```python
class MongoPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Store item in MongoDB database
        pass
    
    async def open_spider(self, spider):
        # Connect to MongoDB database
        pass
    
    async def close_spider(self, spider):
        # Close MongoDB database connection
        pass
```

### Class: MemoryDedupPipeline

A pipeline for deduplicating items using memory storage.

```python
class MemoryDedupPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Deduplicate item using memory storage
        pass
```

### Class: RedisDedupPipeline

A pipeline for deduplicating items using Redis storage.

```python
class RedisDedupPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Deduplicate item using Redis storage
        pass
    
    async def open_spider(self, spider):
        # Initialize Redis connection
        pass
    
    async def close_spider(self, spider):
        # Close Redis connection
        pass
```

### Class: BloomDedupPipeline

A pipeline for deduplicating items using a Bloom filter.

```python
class BloomDedupPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Deduplicate item using Bloom filter
        pass
```

### Class: DatabaseDedupPipeline

A pipeline for deduplicating items using database storage.

```python
class DatabaseDedupPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Deduplicate item using database storage
        pass
    
    async def open_spider(self, spider):
        # Initialize database connection
        pass
    
    async def close_spider(self, spider):
        # Close database connection
        pass
```

## Custom Pipeline Example

```python
class CustomPipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.items_processed = 0
    
    async def process_item(self, item, spider):
        # Custom processing logic
        self.items_processed += 1
        # Return the item to pass it to the next pipeline
        return item
    
    async def open_spider(self, spider):
        self.items_processed = 0
        print(f"Spider {spider.name} opened")
    
    async def close_spider(self, spider):
        print(f"Spider {spider.name} closed. Processed {self.items_processed} items")
```

## Example Usage

```python
from crawlo.pipelines.pipeline_manager import PipelineManager
from crawlo.pipelines.console_pipeline import ConsolePipeline
from crawlo.pipelines.json_pipeline import JsonPipeline

# Configure pipeline classes
pipeline_classes = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]

# Create pipeline manager
pipeline_manager = PipelineManager(crawler, pipeline_classes)

# Process an item through pipelines
async def process_item_with_pipelines(item, spider):
    processed_item = await pipeline_manager.process_item(item, spider)
    return processed_item
```