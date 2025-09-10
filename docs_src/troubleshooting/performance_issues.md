# Performance Issues

This document provides guidance on identifying, diagnosing, and resolving performance issues in Crawlo-based web crawlers.

## Common Performance Issues

### 1. Slow Crawling Speed

**Symptoms:**
- Low requests per second
- Long delays between requests
- Spider appears to be stuck

**Causes:**
- Low concurrency settings
- High download delays
- Network latency
- Target server throttling
- Inefficient parsing logic

### 2. High Memory Usage

**Symptoms:**
- Memory consumption keeps growing
- System becomes unresponsive
- Out of memory errors

**Causes:**
- Too many concurrent requests
- Large item objects
- Memory leaks in custom code
- Inefficient data structures

### 3. High CPU Usage

**Symptoms:**
- CPU utilization near 100%
- System slowdown
- Spider becomes unresponsive

**Causes:**
- CPU-intensive parsing operations
- Too many concurrent threads
- Inefficient algorithms
- Continuous polling

### 4. Database Bottlenecks

**Symptoms:**
- Slow item processing
- Database connection timeouts
- High database CPU usage

**Causes:**
- Inefficient database queries
- Lack of database connection pooling
- Missing database indexes
- Too many simultaneous database operations

## Performance Monitoring

### Built-in Statistics

Crawlo provides built-in statistics collection:

```python
# settings.py
DOWNLOADER_STATS = True
DOWNLOAD_STATS = True
DOWNLOADER_HEALTH_CHECK = True
REQUEST_STATS_ENABLED = True
```

### Custom Performance Monitoring

```python
import time
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()
    
    def record_metric(self, metric_name, value):
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': time.time()
        })
    
    def get_average(self, metric_name):
        values = [m['value'] for m in self.metrics[metric_name]]
        return sum(values) / len(values) if values else 0
    
    def get_percentile(self, metric_name, percentile):
        values = sorted([m['value'] for m in self.metrics[metric_name]])
        if not values:
            return 0
        index = int(len(values) * percentile / 100)
        return values[index]
```

### Performance Profiling Extension

```python
import cProfile
import pstats
import io

class PerformanceProfilerExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.profiler = cProfile.Profile()
        self.profiling_enabled = crawler.settings.get_bool('PERFORMANCE_PROFILING_ENABLED', False)
    
    async def spider_opened(self, spider):
        if self.profiling_enabled:
            self.profiler.enable()
    
    async def spider_closed(self, spider):
        if self.profiling_enabled:
            self.profiler.disable()
            self.save_profile(spider)
    
    def save_profile(self, spider):
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats()
        with open(f'profile_{spider.name}.txt', 'w') as f:
            f.write(s.getvalue())
```

## Optimization Strategies

### 1. Concurrency Optimization

#### Adjusting Concurrency Settings

```python
# settings.py
CONCURRENCY = 32  # Adjust based on target server capacity
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30

# For distributed mode
SCHEDULER_MAX_QUEUE_SIZE = 10000
```

#### Smart Concurrency Control

```python
class SmartConcurrencySpider(Spider):
    name = 'smart_concurrency'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_concurrency = self.settings.get_int('CONCURRENCY', 16)
        self.max_concurrency = 64
        self.min_concurrency = 4
        self.error_count = 0
        self.success_count = 0
    
    def adjust_concurrency(self):
        # Simple algorithm: increase on success, decrease on error
        success_rate = self.success_count / (self.success_count + self.error_count + 1)
        
        if success_rate > 0.9 and self.current_concurrency < self.max_concurrency:
            self.current_concurrency += 1
        elif success_rate < 0.7 and self.current_concurrency > self.min_concurrency:
            self.current_concurrency -= 1
        
        self.logger.info(f"Adjusted concurrency to {self.current_concurrency}")
```

### 2. Memory Optimization

#### Efficient Item Processing

```python
class MemoryEfficientPipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.batch_size = 100
        self.item_buffer = []
    
    async def process_item(self, item, spider):
        # Buffer items instead of processing individually
        self.item_buffer.append(item)
        
        if len(self.item_buffer) >= self.batch_size:
            await self.process_batch(self.item_buffer)
            self.item_buffer.clear()
        
        return item
    
    async def process_batch(self, items):
        # Process items in batch for better memory efficiency
        # Example: batch database insert
        pass
    
    async def close_spider(self, spider):
        # Process remaining items
        if self.item_buffer:
            await self.process_batch(self.item_buffer)
```

#### Memory Monitoring

```python
import psutil
import asyncio

class MemoryMonitorExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.memory_threshold = crawler.settings.get_float('MEMORY_THRESHOLD', 80.0)
        self.check_interval = crawler.settings.get_float('MEMORY_CHECK_INTERVAL', 60.0)
        self.monitoring_task = None
    
    async def spider_opened(self, spider):
        self.monitoring_task = asyncio.create_task(self.monitor_memory(spider))
    
    async def spider_closed(self, spider):
        if self.monitoring_task:
            self.monitoring_task.cancel()
    
    async def monitor_memory(self, spider):
        while True:
            try:
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > self.memory_threshold:
                    spider.logger.warning(f"High memory usage: {memory_percent:.1f}%")
                    # Implement memory cleanup strategies
                    await self.cleanup_memory(spider)
                
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                spider.logger.error(f"Memory monitoring error: {e}")
    
    async def cleanup_memory(self, spider):
        # Implement memory cleanup strategies
        # Example: force garbage collection
        import gc
        gc.collect()
```

### 3. Network Optimization

#### Connection Pool Optimization

```python
# settings.py
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
KEEPALIVE_EXPIRATION = 300  # 5 minutes

# HTTP/2 support for httpx downloader
HTTPX_HTTP2 = True
```

#### Efficient DNS Resolution

```python
# settings.py
DNS_TIMEOUT = 10
DNS_CACHE_SIZE = 10000
DNS_CACHE_TIMEOUT = 3600  # 1 hour
```

### 4. Database Optimization

#### Connection Pooling

```python
class OptimizedDatabasePipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.pool_size = crawler.settings.get_int('DB_POOL_SIZE', 10)
        self.connection_pool = asyncio.Queue(maxsize=self.pool_size)
    
    async def get_connection(self):
        try:
            return self.connection_pool.get_nowait()
        except asyncio.QueueEmpty:
            # Create new connection if pool is empty
            return await self.create_connection()
    
    async def return_connection(self, connection):
        try:
            self.connection_pool.put_nowait(connection)
        except asyncio.QueueFull:
            # Close connection if pool is full
            await connection.close()
    
    async def process_item(self, item, spider):
        connection = await self.get_connection()
        try:
            # Process item with connection
            await self.process_item_with_connection(item, connection)
            return item
        finally:
            await self.return_connection(connection)
```

#### Batch Database Operations

```python
class BatchDatabasePipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.batch_size = crawler.settings.get_int('DB_BATCH_SIZE', 100)
        self.item_buffer = []
        self.buffer_lock = asyncio.Lock()
    
    async def process_item(self, item, spider):
        async with self.buffer_lock:
            self.item_buffer.append(item)
            
            if len(self.item_buffer) >= self.batch_size:
                await self.flush_buffer(spider)
        
        return item
    
    async def flush_buffer(self, spider):
        if not self.item_buffer:
            return
        
        items_to_process = self.item_buffer.copy()
        self.item_buffer.clear()
        
        try:
            # Batch insert
            await self.batch_insert(items_to_process)
            spider.logger.info(f"Processed batch of {len(items_to_process)} items")
        except Exception as e:
            spider.logger.error(f"Batch processing failed: {e}")
            # Handle failed items appropriately
    
    async def batch_insert(self, items):
        # Implement efficient batch insert
        # Example with asyncmy:
        # await cursor.executemany(sql, [(item['field1'], item['field2']) for item in items])
        pass
    
    async def close_spider(self, spider):
        # Process remaining items
        async with self.buffer_lock:
            if self.item_buffer:
                await self.flush_buffer(spider)
```

## Performance Testing

### Load Testing Framework

```python
import asyncio
import time
from collections import defaultdict

class PerformanceTester:
    def __init__(self, spider_class, settings=None):
        self.spider_class = spider_class
        self.settings = settings or {}
        self.metrics = defaultdict(list)
    
    async def run_test(self, duration=300, concurrency_levels=[4, 8, 16, 32]):
        results = {}
        
        for concurrency in concurrency_levels:
            self.settings['CONCURRENCY'] = concurrency
            result = await self.test_concurrency_level(duration)
            results[concurrency] = result
        
        return results
    
    async def test_concurrency_level(self, duration):
        start_time = time.time()
        request_count = 0
        response_times = []
        
        # Mock crawler for testing
        crawler = self.create_mock_crawler()
        spider = self.spider_class()
        
        # Run test for specified duration
        while time.time() - start_time < duration:
            request_start = time.time()
            try:
                # Simulate request processing
                await self.simulate_request_processing(spider)
                response_times.append(time.time() - request_start)
                request_count += 1
            except Exception as e:
                self.metrics['errors'].append({
                    'time': time.time(),
                    'error': str(e)
                })
        
        return {
            'requests_per_second': request_count / duration,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'total_requests': request_count,
            'duration': duration
        }
    
    def create_mock_crawler(self):
        # Create a mock crawler for testing
        pass
    
    async def simulate_request_processing(self, spider):
        # Simulate request processing
        await asyncio.sleep(0.01)  # Simulate network delay
```

### Benchmarking Different Configurations

```python
async def benchmark_configurations():
    configurations = [
        {'CONCURRENCY': 8, 'DOWNLOAD_DELAY': 1.0},
        {'CONCURRENCY': 16, 'DOWNLOAD_DELAY': 0.5},
        {'CONCURRENCY': 32, 'DOWNLOAD_DELAY': 0.25},
    ]
    
    tester = PerformanceTester(MySpider)
    
    for config in configurations:
        print(f"Testing configuration: {config}")
        results = await tester.run_test(duration=60, concurrency_levels=[config['CONCURRENCY']])
        print(f"Results: {results}")
```

## Profiling Tools

### CPU Profiling

```python
# Using cProfile
import cProfile
import pstats

def profile_spider():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run your spider
    # ...
    
    profiler.disable()
    
    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Print top 20 functions
```

### Memory Profiling

```python
# Using memory_profiler
from memory_profiler import profile

class MemoryProfiledSpider(Spider):
    @profile
    def parse(self, response):
        # Your parsing logic
        pass
```

### Async Profiling

```python
# Using asyncio debug mode
import asyncio

async def main():
    # Enable asyncio debug mode
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    
    # Run your spider
    # ...

# Run with: PYTHONASYNCIODEBUG=1 python your_script.py
```

## Best Practices for Performance

### 1. Monitor Key Metrics

```python
class PerformanceMetricsExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.metrics = {
            'requests_per_second': 0,
            'average_response_time': 0,
            'success_rate': 0,
            'memory_usage': 0,
            'cpu_usage': 0
        }
    
    async def collect_metrics(self):
        # Collect and log metrics periodically
        while True:
            self.metrics['memory_usage'] = psutil.virtual_memory().percent
            self.metrics['cpu_usage'] = psutil.cpu_percent()
            
            self.crawler.logger.info(f"Performance metrics: {self.metrics}")
            await asyncio.sleep(60)  # Log every minute
```

### 2. Use Efficient Data Structures

```python
# Use generators instead of lists when possible
def parse(self, response):
    # Good: Generator
    for item in response.css('.item'):
        yield {'data': item.css('.data::text').get()}
    
    # Avoid: Creating large lists
    # items = [extract_item(item) for item in response.css('.item')]
    # return items
```

### 3. Optimize Parsing Logic

```python
# Cache compiled selectors
class OptimizedSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_selectors = {}
    
    def get_selector(self, css_selector):
        if css_selector not in self.cached_selectors:
            self.cached_selectors[css_selector] = parsel.CSSSelector(css_selector)
        return self.cached_selectors[css_selector]
    
    def parse(self, response):
        selector = self.get_selector('.item .data::text')
        for data in selector(response):
            yield {'data': data.get()}
```

### 4. Implement Backpressure Control

```python
class BackpressureSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_size_limit = 1000
        self.backpressure_active = False
    
    async def start_requests(self):
        while True:
            # Check queue size
            queue_size = await self.get_queue_size()
            
            if queue_size > self.queue_size_limit:
                self.backpressure_active = True
                await asyncio.sleep(1)  # Wait before checking again
                continue
            
            self.backpressure_active = False
            
            # Generate requests
            yield self.generate_next_request()
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
```

By following these performance optimization strategies and monitoring techniques, you can build high-performance Crawlo-based web crawlers that efficiently handle large-scale data collection tasks.