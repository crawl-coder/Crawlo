# Frequently Asked Questions (FAQ)

This document answers common questions and issues users may encounter when using the Crawlo framework.

## General Questions

### What is Crawlo?

Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers. It supports both standalone and distributed modes, making it suitable for everything from small-scale development to large-scale production environments.

### What are the system requirements for Crawlo?

Crawlo requires:
- Python 3.10 or higher
- Redis (for distributed crawling)
- pip (Python package installer)

For optional features:
- MySQL or MongoDB (for data storage)

### How do I install Crawlo?

You can install Crawlo using pip:

```bash
pip install crawlo
```

Or install from source:

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -e .
```

## Configuration Questions

### How do I configure Crawlo for distributed crawling?

To configure Crawlo for distributed crawling, set the following in your `settings.py`:

```python
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
REDIS_URL = f'redis://@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
```

### How do I use environment variables with Crawlo?

Crawlo supports environment variables for configuration. You can set them like this:

```bash
export PROJECT_NAME=my_project
export CONCURRENCY=16
export REDIS_HOST=redis.example.com
```

Then in your `settings.py`:

```python
from crawlo.utils.env_config import get_env_var, get_redis_config

PROJECT_NAME = get_env_var('PROJECT_NAME', 'default_project')
CONCURRENCY = get_env_var('CONCURRENCY', 8, int)

redis_config = get_redis_config()
REDIS_HOST = redis_config['REDIS_HOST']
```

### How do I configure different downloaders?

Crawlo supports multiple downloaders. To configure them, set:

```python
# For aiohttp (default)
DOWNLOADER_TYPE = 'aiohttp'

# For httpx (with HTTP/2 support)
DOWNLOADER_TYPE = 'httpx'
HTTPX_HTTP2 = True

# For curl-cffi (with browser fingerprinting)
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'
```

## Spider Development Questions

### How do I create a new spider?

You can create a new spider using the command line:

```bash
crawlo genspider my_spider example.com
```

Or create it manually:

```python
from crawlo import Spider, Request
from myproject.items import MyItem

class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        item = MyItem()
        item['title'] = response.css('title::text').get()
        yield item
```

### How do I handle pagination in my spider?

```python
def parse(self, response):
    # Extract data from current page
    for item in response.css('.item'):
        yield {'title': item.css('.title::text').get()}
    
    # Follow pagination
    next_page = response.css('.next-page::attr(href)').get()
    if next_page:
        yield Request(url=response.urljoin(next_page), callback=self.parse)
```

### How do I pass data between callbacks?

Use the `meta` attribute of Request objects:

```python
def parse_list(self, response):
    category = response.css('h1::text').get()
    for link in response.css('.item-link::attr(href)').getall():
        yield Request(
            url=response.urljoin(link),
            callback=self.parse_detail,
            meta={'category': category}
        )

def parse_detail(self, response):
    category = response.meta['category']
    # Use the category data
    yield {'category': category, 'title': response.css('h1::text').get()}
```

## Distributed Crawling Questions

### How do I run multiple nodes in distributed mode?

Start Redis server first:

```bash
redis-server
```

Then run multiple nodes in separate terminals:

```bash
# Terminal 1
python run.py my_spider

# Terminal 2
python run.py my_spider --concurrency 16

# Terminal 3
python run.py my_spider --concurrency 12
```

### How do I monitor distributed crawling progress?

You can monitor Redis queues using redis-cli:

```bash
# Check pending requests
redis-cli -n 2 scard crawlo:my_project:queue:requests

# Check processing requests
redis-cli -n 2 scard crawlo:my_project:queue:processing

# Check failed requests
redis-cli -n 2 scard crawlo:my_project:queue:failed
```

### How do I handle node failures in distributed crawling?

Crawlo automatically handles node failures:
- Failed requests are requeued after a timeout
- Redis persistence ensures no data loss
- New nodes can be added dynamically

To monitor node health, check logs and Redis statistics.

## Performance Questions

### How do I optimize Crawlo for better performance?

1. Adjust concurrency settings:
```python
CONCURRENCY = 32  # Higher for distributed mode
DOWNLOAD_DELAY = 0.1  # Lower for faster crawling
```

2. Optimize Redis connection pools:
```python
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
```

3. Use appropriate downloaders:
```python
DOWNLOADER_TYPE = 'aiohttp'  # For general high performance
```

### How do I reduce memory usage?

1. Use lower concurrency:
```python
CONCURRENCY = 8
```

2. Implement efficient item processing:
```python
# Process items in batches
ITEM_PIPELINES = {
    'crawlo.pipelines.batch_pipeline.BatchPipeline': 100,
}
```

3. Use memory-efficient data structures in your spiders.

## Error Handling Questions

### How do I handle errors in my spider?

```python
def parse(self, response):
    try:
        # Your parsing logic
        yield {'data': response.css('.data::text').get()}
    except Exception as e:
        self.logger.error(f"Error parsing {response.url}: {e}")
        # Optionally yield a special error item
        yield {'error': str(e), 'url': response.url}
```

### How do I implement retry logic?

Crawlo has built-in retry middleware:

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.retry.RetryMiddleware',
]

MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504]
```

You can also implement custom retry logic in your spider:

```python
def parse(self, response):
    if response.status in [500, 502, 503, 504]:
        # Retry the request
        yield response.request
    else:
        # Process normally
        yield {'data': response.css('.data::text').get()}
```

## Pipeline Questions

### How do I create a custom pipeline?

```python
from crawlo.pipelines import BasePipeline

class CustomPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # Process the item
        item['processed_at'] = datetime.now()
        return item
    
    async def open_spider(self, spider):
        # Initialize when spider opens
        self.file = open('output.txt', 'w')
    
    async def close_spider(self, spider):
        # Clean up when spider closes
        self.file.close()
```

### How do I configure multiple pipelines?

```python
# settings.py
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'myproject.pipelines.CustomPipeline',
]
```

## Middleware Questions

### How do I create custom middleware?

```python
from crawlo.middleware import RequestMiddleware

class CustomMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        # Modify request before sending
        request.headers['X-Custom-Header'] = 'MyValue'
        return request
```

### How do I configure middleware?

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'myproject.middlewares.CustomMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
]
```

## Common Issues and Solutions

### ImportError: No module named 'myproject'

**Cause**: Not running from the project root directory.

**Solution**: Ensure you're in the directory containing `crawlo.cfg` when running framework commands.

### Redis connection failed

**Cause**: Redis server not running or incorrect configuration.

**Solution**: 
1. Check if Redis is running: `redis-server`
2. Verify Redis configuration in `settings.py`
3. Test connection: `redis-cli ping`

### No spider found for: myspider

**Cause**: Spider name doesn't match or spider file not in spiders directory.

**Solution**: 
1. Check that the spider file is in the `spiders/` directory
2. Verify the spider's `name` attribute matches the command argument

### Memory usage too high

**Cause**: Too many concurrent requests or inefficient item processing.

**Solution**:
1. Reduce concurrency: `CONCURRENCY = 8`
2. Increase download delay: `DOWNLOAD_DELAY = 2.0`
3. Optimize item processing in pipelines

### Slow crawling speed

**Cause**: Low concurrency or high download delays.

**Solution**:
1. Increase concurrency: `CONCURRENCY = 32`
2. Reduce download delay: `DOWNLOAD_DELAY = 0.1`
3. Optimize Redis connection pools

## Debugging Tips

### Enable debug logging

```python
# settings.py
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'logs/debug.log'
```

### Use the --debug flag

```bash
python run.py my_spider --debug
```

### Add debug statements in your spider

```python
def parse(self, response):
    self.logger.debug(f"Processing {response.url}")
    # Your parsing logic
```

### Monitor Redis keys

```bash
redis-cli keys "crawlo:*"
```

This FAQ covers the most common questions and issues. For more detailed information, please refer to the other documentation sections.