# Performance Optimization

The Crawlo framework provides various performance optimization options to help users improve crawling efficiency and resource utilization. This document details various performance optimization strategies and best practices.

## Overview

Performance optimization is an important aspect of crawler development. Through proper configuration and optimization strategies, crawling speed can be significantly improved, resource consumption reduced, and system stability enhanced.

### Optimization Goals

1. **Improve Crawling Speed** - Accelerate data collection while maintaining quality
2. **Reduce Resource Consumption** - Decrease memory, CPU, and network resource usage
3. **Enhance Stability** - Improve system stability under high load
4. **Optimize Scalability** - Facilitate horizontal scaling to handle larger scale data

## Concurrency Optimization

### Adjusting Concurrency

Concurrency is a key parameter affecting crawler performance and needs to be adjusted based on the target website's capacity and local resources.

```python
from crawlo.config import CrawloConfig

# Standalone mode concurrency optimization
config = CrawloConfig.standalone(
    concurrency=20,        # Concurrent requests
    download_delay=0.5     # Download delay
)

# Distributed mode concurrency optimization
config = CrawloConfig.distributed(
    concurrency=50,        # Concurrent requests
    download_delay=0.1     # Download delay
)
```

### Concurrency Strategy

```python
# Adjust concurrency based on website response time
# Fast responding websites can use higher concurrency
config = CrawloConfig.standalone(concurrency=50)

# Slow responding websites use lower concurrency
config = CrawloConfig.standalone(concurrency=10)

# Adjust concurrency based on network bandwidth
# High bandwidth environment
config = CrawloConfig.standalone(concurrency=100)

# Low bandwidth environment
config = CrawloConfig.standalone(concurrency=5)
```

## Memory Optimization

### Object Pooling

Use object pooling to reduce object creation and destruction overhead:

```python
import weakref

class RequestPool:
    def __init__(self):
        self._pool = weakref.WeakSet()
    
    def get_request(self, url, **kwargs):
        # Get or create request object from pool
        return Request(url, **kwargs)
    
    def release_request(self, request):
        # Release request object to pool
        self._pool.add(request)

# Global request pool
request_pool = RequestPool()
```

### Memory Monitoring

```python
import psutil
import gc

class MemoryMonitor:
    def __init__(self, threshold_mb=500):
        self.threshold_mb = threshold_mb
    
    def check_memory(self):
        # Check memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.threshold_mb:
            # Trigger garbage collection
            gc.collect()
            self.logger.warning(f"High memory usage: {memory_mb:.2f}MB")
```

### Data Flow Optimization

```python
# Use generators to reduce memory usage
def parse_large_response(response):
    # Process large response line by line
    for line in response.iter_lines():
        yield process_line(line)

# Batch process data
def batch_process_items(items, batch_size=100):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```

## Network Optimization

### Connection Pool Optimization

```python
# Configure connection pool size
config = CrawloConfig.standalone(
    downloader_type='aiohttp',
    aiohttp_connector_limit=100,      # Connection pool size
    aiohttp_connector_limit_per_host=20  # Connection limit per host
)

# HTTP/2 support
config = CrawloConfig.standalone(
    downloader_type='httpx',
    http2=True  # Enable HTTP/2
)
```

### DNS Caching

```python
# Configure DNS caching
config = CrawloConfig.standalone(
    dns_cache_timeout=600,  # DNS cache timeout (seconds)
    dns_cache_size=1000     # DNS cache size
)
```

### Compression Support

```python
# Enable response compression
config = CrawloConfig.standalone(
    accept_encoding=True  # Accept encoding compression
)

# Custom request headers
HEADERS = {
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (compatible; Crawlo/1.0)'
}
```

## Storage Optimization

### Batch Writing

```python
class BatchPipeline:
    def __init__(self, settings):
        self.batch_size = 100
        self.buffer = []
    
    def process_item(self, item, spider):
        self.buffer.append(item)
        
        if len(self.buffer) >= self.batch_size:
            self.flush_buffer()
        
        return item
    
    def flush_buffer(self):
        # Batch write to database
        with self.db.transaction():
            for item in self.buffer:
                self.db.insert(item)
        self.buffer.clear()
```

### Async Storage

```python
import asyncio

class AsyncPipeline:
    def __init__(self, settings):
        self.queue = asyncio.Queue(maxsize=1000)
        self.worker_task = None
    
    async def open_spider(self, spider):
        # Start async write worker
        self.worker_task = asyncio.create_task(self.worker())
    
    async def close_spider(self, spider):
        # Wait for queue to finish processing
        await self.queue.join()
        if self.worker_task:
            self.worker_task.cancel()
    
    async def process_item(self, item, spider):
        # Async process item
        await self.queue.put(item)
        return item
    
    async def worker(self):
        while True:
            try:
                item = await self.queue.get()
                # Async write to database
                await self.async_save_item(item)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
```

## CPU Optimization

### Async Processing

```python
import asyncio
import concurrent.futures

class CPUIntensivePipeline:
    def __init__(self, settings):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    async def process_item(self, item, spider):
        # Run CPU-intensive tasks in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor, 
            self.cpu_intensive_task, 
            item
        )
        return result
    
    def cpu_intensive_task(self, item):
        # CPU-intensive processing logic
        return complex_processing(item)
```

### Cache Optimization

```python
from functools import lru_cache

class OptimizedSpider(Spider):
    @lru_cache(maxsize=1000)
    def parse_url(self, url):
        # Cache parsing results
        return urlparse(url)
    
    def parse(self, response):
        # Use cached parsing results
        parsed = self.parse_url(response.url)
        # Processing logic
```

## I/O Optimization

### Async I/O

```python
import aiofiles

class AsyncFilePipeline:
    async def open_spider(self, spider):
        self.file = await aiofiles.open('output.json', 'w')
    
    async def close_spider(self, spider):
        await self.file.close()
    
    async def process_item(self, item, spider):
        # Async write to file
        await self.file.write(json.dumps(item) + '\n')
        await self.file.flush()
        return item
```

### Memory-Mapped Files

```python
import mmap

class MmapPipeline:
    def __init__(self, settings):
        self.file = open('output.dat', 'r+b')
        self.mmap = mmap.mmap(self.file.fileno(), 0)
    
    def close_spider(self, spider):
        self.mmap.close()
        self.file.close()
```

## Configuration Optimization

### Performance-Related Configuration

```python
# High-performance configuration example
PERFORMANCE_CONFIG = {
    # Concurrency configuration
    'CONCURRENCY': 50,
    'DOWNLOAD_DELAY': 0.1,
    'DOWNLOAD_TIMEOUT': 30,
    
    # Downloader configuration
    'DOWNLOADER_TYPE': 'aiohttp',
    'AIOHTTP_CONNECTOR_LIMIT': 100,
    'AIOHTTP_CONNECTOR_LIMIT_PER_HOST': 20,
    
    # Queue configuration
    'SCHEDULER_MAX_QUEUE_SIZE': 100000,
    'QUEUE_PERSISTENCE': False,  # Memory queue without persistence
    
    # DNS configuration
    'DNS_CACHE_TIMEOUT': 600,
    'DNS_CACHE_SIZE': 1000,
    
    # Log configuration
    'LOG_LEVEL': 'WARNING',  # Reduce log output
}
```

### Environment Variable Optimization

```bash
# Set high-performance environment variables
export CRAWLO_CONCURRENCY=50
export CRAWLO_DOWNLOAD_DELAY=0.1
export CRAWLO_LOG_LEVEL=WARNING
export CRAWLO_AIOHTTP_CONNECTOR_LIMIT=100
```

## Monitoring and Tuning

### Performance Monitoring

```python
import time
import psutil

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
    
    def get_stats(self):
        # Get performance statistics
        elapsed = time.time() - self.start_time
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        return {
            'elapsed_time': elapsed,
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'requests_per_second': self.request_count / elapsed if elapsed > 0 else 0
        }
```

### Performance Profiling

```python
import cProfile
import pstats

def profile_spider():
    # Performance profiling
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run spider
    run_spider()
    
    profiler.disable()
    
    # Output analysis results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Show top 20 most time-consuming functions
```

## Best Practices

### 1. Progressive Optimization

```python
# Start with base configuration
BASE_CONFIG = CrawloConfig.standalone(concurrency=10)

# Gradually increase concurrency and monitor performance
MEDIUM_CONFIG = CrawloConfig.standalone(concurrency=20)
HIGH_CONFIG = CrawloConfig.standalone(concurrency=50)

# Choose optimal configuration based on monitoring results
```

### 2. Load Testing

```python
# Perform load testing with different configurations
def load_test(config, duration=60):
    start_time = time.time()
    request_count = 0
    
    # Run for specified duration
    while time.time() - start_time < duration:
        run_crawler(config)
        request_count += config.CONCURRENCY
    
    # Calculate performance metrics
    rps = request_count / duration
    return rps
```

### 3. Resource Limiting

```python
# Set resource limits
import resource

def set_resource_limits():
    # Limit memory usage (1GB)
    resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024, 1024*1024*1024))
    
    # Limit CPU time (1 hour)
    resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))
```

Through the above performance optimization strategies, Crawlo crawler performance and efficiency can be significantly improved. It is recommended to choose appropriate optimization solutions based on specific application scenarios and verify optimization effects through monitoring and testing.