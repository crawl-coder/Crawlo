# Distributed Crawling Patterns Explained

In the Crawlo framework, distributed crawlers can be applied to different data collection scenarios. This document details two main distributed crawling patterns and their technical implementations.

## 1. List-Only Data Retrieval Pattern

### Scenario Description
In this pattern, APIs or list pages directly return complete data without requiring access to detail pages. This is the case with your current telecom equipment license project.

### Technical Advantages
1. **High Concurrency Processing**: Multiple nodes can process different pages in parallel
2. **Load Balancing**: Requests are automatically distributed to idle nodes
3. **Fault Tolerance**: Node failures do not affect overall tasks
4. **Deduplication**: Avoids processing the same pages repeatedly

### Configuration Key Points
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# High concurrency configuration
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.5
```

### Example Code
```python
class ListOnlySpider(Spider):
    name = 'list_only'
    start_page = 1
    end_page = 1000
    
    def start_requests(self):
        """Generate all page requests at once"""
        for page in range(self.start_page, self.end_page + 1):
            yield Request(
                url=f'https://api.example.com/data?page={page}',
                callback=self.parse,
                meta={'page': page},
                dont_filter=False  # Enable deduplication
            )
    
    def parse(self, response):
        """Extract complete data directly from list pages"""
        data_list = response.json().get('data', [])
        for item_data in data_list:
            item = MyItem()
            item['field1'] = item_data['field1']
            item['field2'] = item_data['field2']
            # ... other fields
            yield item
```

### Startup Method
```bash
# Start Redis
redis-server

# Start multiple nodes
# Terminal 1
python run.py list_only

# Terminal 2
python run.py list_only --concurrency 32

# Terminal 3
python run.py list_only --concurrency 24
```

## 2. Traditional List-Detail Page Pattern

### Scenario Description
In this pattern, you first need to parse list pages to get detail page links, then access detail pages to extract complete data.

### Technical Advantages
1. **Deep Data Collection**: Can obtain more detailed page information
2. **Distributed Deduplication**: Avoids repeatedly accessing the same detail pages
3. **Task Coordination**: Multiple nodes collaboratively handle list and detail page requests
4. **Scalability**: Supports complex page structures and data extraction logic

### Configuration Key Points
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Moderate concurrency configuration (detail pages may require more processing time)
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
```

### Example Code
```python
class ListDetailSpider(Spider):
    name = 'list_detail'
    start_urls = ['https://example.com/list']
    
    def parse(self, response):
        """Parse list page and extract detail page links"""
        # Extract detail page links
        detail_links = response.css('.item-link::attr(href)').getall()
        
        for link in detail_links:
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail,
                dont_filter=False  # Enable deduplication
            )
        
        # Handle pagination
        next_page = response.css('.next-page::attr(href)').get()
        if next_page:
            yield Request(
                url=response.urljoin(next_page),
                callback=self.parse
            )
    
    def parse_detail(self, response):
        """Parse detail page and extract complete data"""
        item = MyItem()
        item['title'] = response.css('h1.title::text').get()
        item['content'] = response.css('.content::text').get()
        item['price'] = response.css('.price::text').get()
        # ... other fields
        
        yield item
```

### Startup Method
```bash
# Start Redis
redis-server

# Start multiple nodes
# Terminal 1
python run.py list_detail

# Terminal 2
python run.py list_detail --concurrency 16

# Terminal 3
python run.py list_detail --concurrency 12
```

## Comparison of Both Patterns

| Feature | List-Only Data Retrieval | Traditional List-Detail Pattern |
|---------|--------------------------|---------------------------------|
| Data Completeness | Complete data in list pages | Requires detail pages for complete data |
| Concurrency Efficiency | High (simple requests) | Moderate (complex requests) |
| Network Overhead | Low | High (more requests) |
| Implementation Complexity | Simple | Complex |
| Applicable Scenarios | API data collection, simple lists | Complex page structures, in-depth information |

## Best Practices

### 1. List-Only Pattern Best Practices
- Generate all page requests at once
- Set appropriate concurrency levels (typically higher)
- Enable deduplication mechanism to avoid duplicate processing
- Monitor request frequency to avoid server pressure

### 2. List-Detail Pattern Best Practices
- Perform preliminary deduplication during list page parsing
- Set appropriate delays to avoid anti-crawler mechanisms
- Use middleware to handle login status or cookies
- Implement error retry mechanisms

## Configuration Optimization Recommendations

### Redis Configuration
```python
# settings.py
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
SCHEDULER_QUEUE_NAME = 'my_spider:requests'
REDIS_KEY = 'my_spider:fingerprint'
```

### Performance Tuning
```python
# settings.py
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504]
```

## Monitoring and Debugging

### Check Queue Status
```bash
# Check request queue length
redis-cli llen my_spider:requests

# Check deduplication set size
redis-cli scard my_spider:fingerprint
```

### Log Monitoring
```python
# settings.py
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/distributed_spider.log'
```

By properly selecting and configuring these two distributed crawling patterns, you can achieve efficient distributed data collection based on your specific data collection requirements.