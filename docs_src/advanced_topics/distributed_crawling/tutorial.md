# Distributed Crawling Tutorial

This tutorial will guide you through setting up and running distributed crawlers with Crawlo.

## Prerequisites

Before starting this tutorial, ensure you have:

1. Installed Crawlo (see [Installation Guide](../../getting_started/installation.md))
2. A Redis server running
3. Basic knowledge of Crawlo concepts

## Setting Up Redis

### Installing Redis

If you haven't installed Redis yet, follow these steps:

#### On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
```

#### On macOS (using Homebrew):
```bash
brew install redis
```

#### On Windows:
Download Redis from the [official website](https://redis.io/download/) or use [WSL](https://docs.microsoft.com/en-us/windows/wsl/install).

### Starting Redis

Start the Redis server:

```bash
redis-server
```

By default, Redis runs on `localhost:6379`.

## Configuring Your Project for Distributed Crawling

### 1. Update settings.py

In your project's `settings.py` file, add the following configuration:

```python
# Enable distributed mode
RUN_MODE = 'distributed'

# Configure Redis connection
REDIS_HOST = '127.0.0.1'  # Change if Redis is on a different host
REDIS_PORT = 6379
REDIS_DB = 2  # Use a separate DB for Crawlo
REDIS_PASSWORD = ''  # Add password if required

# Scheduler configuration
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
QUEUE_TYPE = 'redis'

# Deduplication filter
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Project name (used in Redis keys)
PROJECT_NAME = 'my_distributed_project'
```

### 2. Configure Concurrency

For distributed crawling, you might want to adjust concurrency settings:

```python
# Higher concurrency for distributed crawling
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.5
```

## Creating a Distributed Spider

Let's create a simple spider that can take advantage of distributed crawling:

```python
# spiders/distributed_example.py
from crawlo import Spider, Request
from myproject.items import MyItem

class DistributedExampleSpider(Spider):
    name = 'distributed_example'
    
    custom_settings = {
        'CONCURRENCY': 32,
        'DOWNLOAD_DELAY': 0.5,
    }
    
    def start_requests(self):
        # Generate a large number of requests to demonstrate distribution
        for i in range(1, 1001):  # 1000 pages
            yield Request(
                url=f'https://httpbin.org/get?page={i}',
                callback=self.parse,
                meta={'page': i}
            )
    
    def parse(self, response):
        page = response.meta['page']
        item = MyItem()
        item['page'] = page
        item['url'] = response.url
        item['status'] = response.status
        yield item
```

## Running Distributed Crawlers

### Single Node Test

First, test your spider with a single node:

```bash
crawlo run distributed_example
```

### Multi-Node Deployment

To run multiple nodes, open several terminal windows and run the same command in each:

```bash
# Terminal 1
crawlo run distributed_example

# Terminal 2
crawlo run distributed_example

# Terminal 3
crawlo run distributed_example
```

Each node will automatically discover the shared Redis queue and start processing tasks.

## Monitoring Distributed Crawling

### Checking Queue Status

You can monitor the status of your distributed crawler using Redis CLI:

```bash
# Check the number of pending requests
redis-cli scard crawlo:my_distributed_project:queue:requests

# Check the number of processed requests
redis-cli scard crawlo:my_distributed_project:queue:processing

# Check the number of failed requests
redis-cli scard crawlo:my_distributed_project:queue:failed

# Check deduplication set size
redis-cli scard crawlo:my_distributed_project:filter:fingerprint
```

### Viewing Logs

Each node will generate its own logs. Check the log files to monitor progress:

```bash
tail -f logs/crawlo.log
```

## Advanced Configuration

### Custom Redis Key Names

You can customize Redis key names if needed:

```python
# In settings.py
SCHEDULER_QUEUE_NAME = 'myproject:custom_queue'
```

### Redis Connection Pool Optimization

For high-performance distributed crawling, optimize Redis connection settings:

```python
# In settings.py
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
```

### Error Handling and Retries

Configure error handling for distributed environments:

```python
# In settings.py
MAX_RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]
REQUEST_TIMEOUT = 30
```

## Best Practices

### 1. Resource Management
- Monitor system resources on each node
- Adjust concurrency settings based on available resources
- Use appropriate download delays to avoid overwhelming target servers

### 2. Fault Tolerance
- Implement proper error handling in your spiders
- Use retry mechanisms for transient failures
- Monitor node health and restart failed nodes

### 3. Data Consistency
- Use proper deduplication mechanisms
- Ensure all nodes use the same configuration
- Regularly backup Redis data for critical projects

### 4. Scaling
- Add nodes dynamically based on workload
- Use load balancing techniques
- Monitor performance metrics to optimize scaling

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check if Redis server is running
   - Verify Redis host and port configuration
   - Check firewall settings

2. **Nodes Not Discovering Each Other**
   - Ensure all nodes connect to the same Redis instance
   - Verify PROJECT_NAME configuration is consistent
   - Check Redis key names

3. **Performance Issues**
   - Monitor Redis memory usage
   - Adjust concurrency settings
   - Check network latency between nodes and Redis

### Debugging Tips

1. **Enable Debug Logging**
   ```python
   # In settings.py
   LOG_LEVEL = 'DEBUG'
   ```

2. **Monitor Redis Keys**
   ```bash
   redis-cli keys "crawlo:*"
   ```

3. **Check Node Status**
   ```bash
   redis-cli info clients
   ```

## Conclusion

Distributed crawling with Crawlo allows you to scale your web scraping projects across multiple machines, significantly improving performance and fault tolerance. By following this tutorial, you should now be able to:

- Set up Redis for distributed crawling
- Configure your Crawlo project for distributed mode
- Create spiders that work well in distributed environments
- Run and monitor multiple crawler nodes
- Troubleshoot common distributed crawling issues

For more advanced topics, check out the [Distributed Crawling Mechanism](mechanism.md) documentation.