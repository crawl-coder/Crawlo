# BloomFilter

BloomFilter is an efficient deduplication component based on the Bloom filter algorithm in the Crawlo framework, suitable for scenarios handling large-scale URLs.

## Overview

BloomFilter implements request deduplication using the Bloom filter algorithm, featuring extremely low memory usage and fast query speed, particularly suitable for handling ultra-large-scale crawling tasks.

### Core Features

1. **Extremely Low Memory Usage** - Much lower memory usage compared to other filters
2. **Fast Query** - O(k) time complexity query speed
3. **Configurable Accuracy** - Supports configurable false positive rate
4. **Large-scale Support** - Supports processing hundreds of millions of URLs

## Configuration Options

The behavior of BloomFilter can be adjusted through the following configuration options:

| Configuration Item | Type | Default Value | Description |
|--------------------|------|---------------|-------------|
| BLOOM_FILTER_CAPACITY | int | 1000000 | Filter capacity |
| BLOOM_FILTER_ERROR_RATE | float | 0.001 | False positive rate |
| BLOOM_FILTER_PERSISTENCE | bool | True | Whether to persist |
| BLOOM_FILTER_FILENAME | str | 'bloom_filter.dat' | Persistence filename |

## Usage Examples

### Basic Usage

```python
from crawlo.config import CrawloConfig

# Configure to use Bloom filter
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_capacity=10000000,  # 10 million capacity
    bloom_filter_error_rate=0.0001   # 0.01% false positive rate
)
```

### Advanced Configuration

```python
# Configure persistence
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_persistence=True,
    bloom_filter_filename='my_filter.dat'
)
```

## Performance Characteristics

### Memory Usage Comparison

| Filter Type | Memory Usage for 1M URLs | Memory Usage for 100M URLs |
|-------------|-------------------------|---------------------------|
| MemoryFilter | 100MB | 10GB |
| AioRedisFilter | 50MB | 5GB |
| BloomFilter | 1MB | 100MB |

### Query Performance

```python
# BloomFilter query performance
import time

# Test query performance
start_time = time.time()
for i in range(1000000):
    filter.check_duplicate(Request(url=f"http://example.com/{i}"))
end_time = time.time()

print(f"BloomFilter 1 million queries time: {end_time - start_time:.2f} seconds")
# Usually less than 1 second
```

## False Positive Rate Management

### False Positive Rate Configuration

```python
# Memory usage with different false positive rates
config_low_error = CrawloConfig.standalone(
    bloom_filter_capacity=1000000,
    bloom_filter_error_rate=0.0001  # 0.01% false positive rate, memory usage ~2MB
)

config_high_error = CrawloConfig.standalone(
    bloom_filter_capacity=1000000,
    bloom_filter_error_rate=0.01   # 1% false positive rate, memory usage ~1MB
)
```

### False Positive Handling

```python
class BloomSpider(Spider):
    def parse(self, response):
        # Handle possible false positives
        if self.is_likely_duplicate(response.url):
            # Might be a false positive, perform secondary verification
            if not self.secondary_check(response.url):
                return
        
        # Normal processing logic
        yield Item(data=response.text)
    
    def is_likely_duplicate(self, url):
        # Judge if it's likely a false positive based on business logic
        return False
    
    def secondary_check(self, url):
        # Secondary verification logic
        return True
```

## Best Practices

### 1. Capacity Planning

```python
# Plan capacity based on expected URL count
expected_urls = 50000000  # Expected 50 million URLs
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_capacity=int(expected_urls * 1.2),  # Reserve 20% space
    bloom_filter_error_rate=0.001
)
```

### 2. False Positive Rate Selection

```python
# Choose false positive rate based on business requirements
# For scenarios requiring high accuracy
config_strict = CrawloConfig.standalone(
    bloom_filter_error_rate=0.0001  # 0.01% false positive rate
)

# For scenarios requiring high performance
config_performance = CrawloConfig.standalone(
    bloom_filter_error_rate=0.01    # 1% false positive rate
)
```

### 3. Persistence Configuration

```python
# Enable persistence in production environment
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_persistence=True,
    bloom_filter_filename=f'bloom_filter_{int(time.time())}.dat'
)

# Regularly backup filter
import shutil
shutil.copy('bloom_filter.dat', f'backup/bloom_filter_{int(time.time())}.dat')
```

## Troubleshooting

### Common Issues

1. **Insufficient Memory**
   ```python
   # Issue: MemoryError
   # Solution: Reduce capacity or increase false positive rate
   config = CrawloConfig.standalone(
       bloom_filter_capacity=5000000,   # Reduce capacity
       bloom_filter_error_rate=0.01     # Increase false positive rate
   )
   ```

2. **High False Positive Rate**
   ```python
   # Issue: Too many false positives causing data loss
   # Solution: Reduce false positive rate or add secondary verification
   config = CrawloConfig.standalone(
       bloom_filter_error_rate=0.0001   # Reduce false positive rate
   )
   ```

3. **Persistence File Corruption**
   ```python
   # Issue: Persistence file corruption
   # Solution: Delete corrupted file and recreate
   import os
   if os.path.exists('bloom_filter.dat'):
       os.remove('bloom_filter.dat')
   # Restart spider will automatically create new file
   ```

### Performance Tuning

```python
# Monitor BloomFilter performance
class PerformanceMonitor:
    def __init__(self):
        self.check_count = 0
        self.duplicate_count = 0
    
    def monitor_filter(self, filter):
        # Monitor filter performance
        stats = filter.get_stats()
        self.logger.info(f"Filter statistics: {stats}")
        
        # Calculate actual false positive rate
        if self.check_count > 0:
            actual_error_rate = self.duplicate_count / self.check_count
            self.logger.info(f"Actual false positive rate: {actual_error_rate:.4f}")
```