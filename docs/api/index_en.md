# API Reference

Welcome to the complete API reference documentation for the Crawlo framework. This document details the usage of various modules and classes in the framework.

## Core Modules

### [crawlo.crawler](crawlo_crawler.md)
Crawler process management and runtime core functionality module.

Core Classes:
- `Crawler` - Single crawler instance
- `CrawlerProcess` - Crawler process manager

### [crawlo.spider](crawlo_spider___init__.md)
Spider base class and related functionality module.

Core Classes:
- `Spider` - Spider base class
- `SpiderMeta` - Spider metaclass

## Network Modules

### [crawlo.network.request](crawlo_network_request.md)
HTTP request object implementation.

Core Classes:
- `Request` - Request object

### [crawlo.network.response](crawlo_network_response.md)
HTTP response object implementation.

Core Classes:
- `Response` - Response object

## Data Processing Modules

### [crawlo.items](crawlo_items_items.md)
Data item definition and processing.

Core Classes:
- `Item` - Data item base class
- `ItemMeta` - Data item metaclass

## Downloader Modules

### [crawlo.downloader](crawlo_downloader___init__.md)
HTTP client downloader implementation.

Core Classes:
- `DownloaderBase` - Downloader base class
- `AioHttpDownloader` - aiohttp-based downloader
- `HttpXDownloader` - httpx-based downloader
- `CurlCffiDownloader` - curl-cffi-based downloader

## Scheduler Modules

### [crawlo.core.scheduler](crawlo_core_scheduler.md)
Request scheduling and deduplication management.

Core Classes:
- `Scheduler` - Scheduler

## Queue Modules

### [crawlo.queue](crawlo_queue___init__.md)
Request queue management.

Core Classes:
- `QueueManager` - Queue manager

## Filter Modules

### [crawlo.filters](crawlo_filters___init__.md)
Request deduplication filtering.

Core Classes:
- `BaseFilter` - Filter base class
- `MemoryFilter` - Memory filter
- `RedisFilter` - Redis filter
- `BloomFilter` - Bloom filter

## Middleware Modules

### [crawlo.middleware](crawlo_middleware___init__.md)
Request/response processing middleware.

Core Classes:
- `Middleware` - Middleware base class
- `MiddlewareManager` - Middleware manager

## Pipeline Modules

### [crawlo.pipelines](crawlo_pipelines___init__.md)
Data processing and storage pipelines.

Core Classes:
- `Pipeline` - Pipeline base class
- `PipelineManager` - Pipeline manager

### Built-in Pipelines

- [crawlo.pipelines.bloom_dedup_pipeline](crawlo_pipelines_bloom_dedup_pipeline.md) - Bloom deduplication pipeline
- [crawlo.pipelines.console_pipeline](crawlo_pipelines_console_pipeline.md) - Console output pipeline
- [crawlo.pipelines.csv_pipeline](crawlo_pipelines_csv_pipeline.md) - CSV output pipeline
- [crawlo.pipelines.database_dedup_pipeline](crawlo_pipelines_database_dedup_pipeline.md) - Database deduplication pipeline
- [crawlo.pipelines.json_pipeline](crawlo_pipelines_json_pipeline.md) - JSON output pipeline
- [crawlo.pipelines.memory_dedup_pipeline](crawlo_pipelines_memory_dedup_pipeline.md) - Memory deduplication pipeline
- [crawlo.pipelines.mongo_pipeline](crawlo_pipelines_mongo_pipeline.md) - MongoDB output pipeline
- [crawlo.pipelines.mysql_pipeline](crawlo_pipelines_mysql_pipeline.md) - MySQL output pipeline
- [crawlo.pipelines.redis_dedup_pipeline](crawlo_pipelines_redis_dedup_pipeline.md) - Redis deduplication pipeline

## Extension Modules

### [crawlo.extension](crawlo_extension___init__.md)
Framework extension functionality.

Core Classes:
- `Extension` - Extension base class
- `ExtensionManager` - Extension manager

## Utility Modules

### [crawlo.utils.log](crawlo_utils_log.md)
Logging system utilities.

Core Functions:
- `configure_logging` - Configure logging system
- `get_logger` - Get logger instance

## Usage Example

```python
from crawlo.crawler import Crawler
from crawlo.spider import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # Parsing logic
        pass

# Create and run crawler
crawler = Crawler(MySpider)
await crawler.crawl()
```