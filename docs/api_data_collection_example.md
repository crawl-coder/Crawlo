# API Data Collection Example (List-Only Pattern)

This example demonstrates how to use Crawlo framework for distributed crawling in the list-only data retrieval pattern, where complete data is available directly from list/API pages without requiring detail page parsing.

## 🎯 Key Features

- **Distributed Processing**: Multiple nodes process different pages concurrently
- **High Concurrency**: Optimized for high-concurrency scenarios
- **Redis Coordination**: Uses Redis for request queue and deduplication
- **Load Balancing**: Automatic load distribution among nodes

## 📁 Project Structure

```
api_data_collection/
├── crawlo.cfg                   # Project configuration
├── run.py                       # Run script
├── logs/                        # Log directory
└── api_data_collection/
    ├── __init__.py
    ├── settings.py              # Distributed configuration
    ├── items.py                 # Data structure definition
    ├── pipelines.py             # Data processing pipelines
    ├── redis_pipelines.py       # Redis-based deduplication pipeline
    ├── bloom_pipelines.py       # Bloom filter-based pipeline
    ├── db_pipelines.py          # Database-based pipeline
    └── spiders/
        ├── __init__.py
        └── api_data.py         # Spider implementation (list-only pattern)
```

## ⚙️ Configuration Highlights

### Distributed Settings
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
CONCURRENCY = 32  # High concurrency for list-only pattern
DOWNLOAD_DELAY = 0.5
```

### Spider Implementation
The spider generates all page requests upfront, allowing multiple nodes to process them in parallel:

```python
def start_requests(self):
    """Generate all page requests for parallel processing"""
    for page in range(self.start_page, self.end_page + 1):
        yield Request(
            url=f'{self.base_api_url}?page={page}&limit=50',
            callback=self.parse,
            meta={'page': page},
            dont_filter=False  # Enable deduplication
        )
```

## 🔍 Deduplication Mechanisms

Crawlo framework provides two levels of deduplication:

### 1. Request-Level Deduplication (Built-in)
- **Purpose**: Prevent duplicate network requests
- **Implementation**: Automatically handled by Crawlo framework (AioRedisFilter)
- **Configuration**: 
  ```python
  DUPEFILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
  SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
  ```

### 2. Item-Level Deduplication (Pipeline-based)
- **Purpose**: Prevent duplicate data items from being saved
- **Implementation**: Custom pipelines in `pipelines.py`, `redis_pipelines.py`, etc.
- **Usage**: Uncomment desired pipeline in `settings.py`

### Key Differences

| Aspect | AioRedisFilter | RedisDeduplicationPipeline |
|--------|----------------|---------------------------|
| **Level** | Request-level | Item-level |
| **Timing** | Before request | Before saving data |
| **Based on** | Request fingerprint (URL, method, params) | Data content (item fields) |
| **Location** | Framework core | User-defined pipeline |

For detailed comparison, see [filter_vs_pipeline_comparison_detailed.md](filter_vs_pipeline_comparison_detailed.md).

## 🚀 Running the Spider

### 1. Start Redis Server
```bash
redis-server
```

### 2. Run Multiple Nodes
```bash
# Terminal 1
python run.py api_data

# Terminal 2
python run.py api_data --concurrency 32

# Terminal 3
python run.py api_data --concurrency 24
```

## 📊 Performance Benefits

| Aspect | Benefit |
|--------|---------|
| **Speed** | Multiple nodes process pages concurrently |
| **Scalability** | Easy to add more nodes |
| **Reliability** | Node failures don't stop the crawl |
| **Efficiency** | No redundant detail page requests |

## 🛠️ When to Use This Pattern

This pattern is ideal for:
- API data collection where complete data is returned in list responses
- Simple list pages with all required information
- High-volume data collection scenarios
- Cases where detail pages don't provide additional value

For scenarios requiring detail page parsing, see the [telecom_licenses_distributed](https://github.com/crawl-coder/Crawlo/tree/master/examples/telecom_licenses_distributed) example.