# Distributed Crawler Examples

This document provides examples of distributed crawlers using the Crawlo framework.

## Simple Distributed Crawler

This example demonstrates a basic distributed crawler that can run across multiple nodes.

### Project Structure

```
simple_distributed/
├── simple_distributed/
│   ├── __init__.py
│   ├── items.py
│   ├── settings.py
│   └── spiders/
│       ├── __init__.py
│       └── quotes.py
├── crawlo.cfg
└── run.py
```

### Items Definition

```python
# simple_distributed/items.py
from crawlo.items import Item, Field

class QuoteItem(Item):
    text = Field(description="Quote text")
    author = Field(description="Author name")
    tags = Field(description="List of tags")
```

### Spider Implementation

```python
# simple_distributed/spiders/quotes.py
from crawlo import Spider, Request
from simple_distributed.items import QuoteItem

class QuotesSpider(Spider):
    name = 'quotes'
    start_urls = ['http://quotes.toscrape.com/']
    
    custom_settings = {
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
    }
    
    def parse(self, response):
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            yield item
        
        # Follow pagination links
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield Request(url=response.urljoin(next_page), callback=self.parse)
```

### Settings Configuration

```python
# simple_distributed/settings.py
PROJECT_NAME = 'simple_distributed'
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5
LOG_LEVEL = 'INFO'

# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_URL = f'redis://@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
]
```

### Running the Distributed Crawler

```bash
# Start Redis server (if not already running)
redis-server

# Terminal 1 - Node 1
cd simple_distributed
python run.py quotes

# Terminal 2 - Node 2
cd simple_distributed
python run.py quotes --concurrency 12

# Terminal 3 - Node 3
cd simple_distributed
python run.py quotes --concurrency 8
```

## Advanced Distributed Crawler with Custom Components

This example demonstrates a more advanced distributed crawler with custom components.

### Custom Distributed Spider

```python
# simple_distributed/spiders/advanced_quotes.py
from crawlo import Spider, Request
from simple_distributed.items import QuoteItem

class AdvancedQuotesSpider(Spider):
    name = 'advanced_quotes'
    start_urls = ['http://quotes.toscrape.com/']
    
    custom_settings = {
        'CONCURRENCY': 32,
        'DOWNLOAD_DELAY': 0.2,
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
        'MIDDLEWARES': [
            'crawlo.middleware.default_header.DefaultHeaderMiddleware',
            'crawlo.middleware.retry.RetryMiddleware',
            'crawlo.middleware.download_delay.DownloadDelayMiddleware',
        ]
    }
    
    def start_requests(self):
        # Generate requests for multiple pages
        for i in range(1, 101):  # 100 pages
            yield Request(
                url=f'http://quotes.toscrape.com/page/{i}/',
                callback=self.parse,
                meta={'page': i}
            )
    
    def parse(self, response):
        page = response.meta['page']
        
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            yield item
        
        self.logger.info(f"Processed page {page}")
```

### Custom Pipeline for Distributed Processing

```python
# simple_distributed/pipelines.py
from crawlo.pipelines import BasePipeline
import asyncio

class DistributedProcessingPipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.processed_count = 0
        self.node_id = None
    
    async def open_spider(self, spider):
        # Generate a unique node ID
        import uuid
        self.node_id = str(uuid.uuid4())[:8]
        self.processed_count = 0
        spider.logger.info(f"Node {self.node_id} started processing")
    
    async def process_item(self, item, spider):
        # Simulate some processing time
        await asyncio.sleep(0.01)
        
        # Add node information to item
        item['processed_by'] = self.node_id
        item['processed_at'] = asyncio.get_event_loop().time()
        
        self.processed_count += 1
        return item
    
    async def close_spider(self, spider):
        spider.logger.info(f"Node {self.node_id} finished processing {self.processed_count} items")
```

### Updated Settings for Advanced Distributed Crawler

```python
# simple_distributed/settings.py
PROJECT_NAME = 'advanced_distributed'
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.2
LOG_LEVEL = 'INFO'

# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_URL = f'redis://@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Middlewares
MIDDLEWARES = [
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
]

# Pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'simple_distributed.pipelines.DistributedProcessingPipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
]

# Performance tuning
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504]
```

## Large-Scale Distributed Crawler

This example demonstrates a large-scale distributed crawler for processing massive datasets.

### High-Performance Spider

```python
# simple_distributed/spiders/large_scale.py
from crawlo import Spider, Request
from simple_distributed.items import QuoteItem

class LargeScaleSpider(Spider):
    name = 'large_scale'
    
    custom_settings = {
        'CONCURRENCY': 64,
        'DOWNLOAD_DELAY': 0.05,
        'DUPEFILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'SCHEDULER': 'crawlo.scheduler.Scheduler',
    }
    
    def start_requests(self):
        # Generate requests for a large number of pages
        for i in range(1, 1001):  # 1000 pages
            yield Request(
                url=f'http://quotes.toscrape.com/page/{i}/',
                callback=self.parse,
                meta={'page': i},
                priority=1000-i  # Higher priority for earlier pages
            )
    
    def parse(self, response):
        page = response.meta['page']
        
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            item['page'] = page
            yield item
        
        if page % 100 == 0:
            self.logger.info(f"Processed {page} pages")
```

### Production Settings for Large-Scale Crawler

```python
# simple_distributed/settings.py
PROJECT_NAME = 'large_scale_distributed'
CONCURRENCY = 64
DOWNLOAD_DELAY = 0.05
LOG_LEVEL = 'WARNING'  # Reduce log verbosity for performance

# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis configuration for production
REDIS_HOST = 'redis-cluster.internal'  # Use your Redis cluster
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_PASSWORD = 'your_redis_password'  # Add password for security
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Pipelines
PIPELINES = [
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
    'crawlo.pipelines.mongo_pipeline.MongoPoolPipeline',  # Use MongoDB for high-volume storage
]

# Performance tuning
CONNECTION_POOL_LIMIT = 200
CONNECTION_POOL_LIMIT_PER_HOST = 50
MAX_RETRY_TIMES = 5
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]
DOWNLOAD_TIMEOUT = 30

# Memory optimization
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
```

## Monitoring Distributed Crawlers

### Checking Queue Status

```bash
# Check the number of pending requests
redis-cli -n 2 scard crawlo:advanced_distributed:queue:requests

# Check the number of processing requests
redis-cli -n 2 scard crawlo:advanced_distributed:queue:processing

# Check the number of failed requests
redis-cli -n 2 scard crawlo:advanced_distributed:queue:failed

# Check deduplication set size
redis-cli -n 2 scard crawlo:advanced_distributed:filter:fingerprint
```

### Viewing Logs

Each node will generate its own logs. Check the log files to monitor progress:

```bash
# Tail logs from multiple nodes
tail -f logs/crawlo.log
```

## Running Examples

### Basic Distributed Example

```bash
# Start Redis server
redis-server

# Terminal 1 - Node 1
cd simple_distributed
python run.py quotes

# Terminal 2 - Node 2
cd simple_distributed
python run.py quotes --concurrency 16

# Terminal 3 - Node 3
cd simple_distributed
python run.py quotes --concurrency 12
```

### Advanced Distributed Example

```bash
# Start Redis server
redis-server

# Terminal 1 - Node 1
cd simple_distributed
python run.py advanced_quotes --concurrency 32

# Terminal 2 - Node 2
cd simple_distributed
python run.py advanced_quotes --concurrency 24

# Terminal 3 - Node 3
cd simple_distributed
python run.py advanced_quotes --concurrency 20
```

### Large-Scale Example

```bash
# Start Redis server
redis-server

# Terminal 1 - Node 1
cd simple_distributed
python run.py large_scale --concurrency 64

# Terminal 2 - Node 2
cd simple_distributed
python run.py large_scale --concurrency 64

# Terminal 3 - Node 3
cd simple_distributed
python run.py large_scale --concurrency 64

# Terminal 4 - Node 4
cd simple_distributed
python run.py large_scale --concurrency 64
```

## Best Practices for Distributed Crawlers

1. **Resource Management**: Monitor system resources on each node
2. **Fault Tolerance**: Implement proper error handling and retry mechanisms
3. **Data Consistency**: Use proper deduplication mechanisms
4. **Scalability**: Add nodes dynamically based on workload
5. **Monitoring**: Monitor Redis queues and node health
6. **Security**: Use secure Redis connections with authentication
7. **Performance**: Optimize Redis connection pools and concurrency settings

## Performance Tuning

### Redis Optimization

```python
# settings.py
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
REDIS_DB = 2  # Use separate DB for Crawlo
```

### Concurrency Optimization

```python
# settings.py
CONCURRENCY = 32  # Adjust based on target server capacity
DOWNLOAD_DELAY = 0.1  # Balance speed and politeness
```

These examples demonstrate various ways to use Crawlo for distributed crawling, from simple multi-node setups to large-scale distributed systems.