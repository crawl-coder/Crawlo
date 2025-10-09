# stats Command

The `stats` command views crawler runtime statistics, helping to monitor crawler performance and status.

## Command Syntax

```bash
crawlo stats [spider_name] [options]
```

### Parameter Description

- `spider_name` - The spider name to view statistics for (optional, shows all spiders if not specified)
- `options` - Optional parameters

## Usage Examples

### Basic Usage

```bash
# View statistics for all spiders
crawlo stats

# View statistics for specific spider
crawlo stats myspider

# Real-time monitor statistics
crawlo stats --follow
```

### Detailed Statistics

```bash
# Show detailed statistics
crawlo stats --verbose

# Output in JSON format
crawlo stats --format json

# Save statistics to file
crawlo stats --output stats.json
```

## Statistics Types

### 1. Basic Statistics

```bash
# Basic statistics
Total Requests: 1000
Successful Requests: 950
Failed Requests: 50
Items Scraped: 800
Runtime: 02:30:15
```

### 2. Performance Statistics

```bash
# Performance-related statistics
Average Response Time: 1.25 seconds
Request Rate: 25.5 requests/second
Item Rate: 20.3 items/second
Memory Usage: 125.5 MB
CPU Usage: 45.2%
```

### 3. Error Statistics

```bash
# Error-related statistics
HTTP Errors:
  - 404: 20 times
  - 500: 15 times
  - 403: 10 times
  - Timeouts: 5 times
Retry Statistics:
  - Retry Count: 100 times
  - Successful Retries: 85 times
```

## Configuration Options

The `stats` command supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --project-dir | string | Current directory | Project directory path |
| --format | string | 'table' | Output format (table, json, csv) |
| --verbose | flag | - | Show detailed information |
| --follow | flag | - | Real-time monitor statistics |
| --interval | int | 5 | Real-time monitoring interval (seconds) |
| --output | string | None | Output file path |
| --reset | flag | - | Reset statistics |
| --history | flag | - | Show historical statistics |
| --limit | int | 10 | History record limit |

## Output Formats

### Table Format (Default)

```bash
$ crawlo stats myspider
Spider Statistics: myspider
+------------------+-------------------+
| Statistic        | Value             |
+------------------+-------------------+
| Total Requests   | 1000              |
| Successful Requests | 950            |
| Failed Requests  | 50                |
| Items Scraped    | 800               |
| Runtime          | 02:30:15          |
| Avg Response Time | 1.25 seconds     |
| Request Rate     | 25.5 req/sec      |
| Memory Usage     | 125.5 MB          |
+------------------+-------------------+
```

### JSON Format

```bash
$ crawlo stats myspider --format json
{
  "spider": "myspider",
  "timestamp": "2023-01-01T12:00:00Z",
  "basic_stats": {
    "total_requests": 1000,
    "successful_requests": 950,
    "failed_requests": 50,
    "items_scraped": 800,
    "runtime": "02:30:15"
  },
  "performance_stats": {
    "avg_response_time": 1.25,
    "request_rate": 25.5,
    "item_rate": 20.3,
    "memory_usage": 125.5,
    "cpu_usage": 45.2
  },
  "error_stats": {
    "http_errors": {
      "404": 20,
      "500": 15,
      "403": 10
    },
    "timeouts": 5,
    "retries": {
      "total": 100,
      "successful": 85
    }
  }
}
```

### CSV Format

```bash
$ crawlo stats --format csv
Statistic,Value
Total Requests,1000
Successful Requests,950
Failed Requests,50
Items Scraped,800
Runtime,02:30:15
Avg Response Time,1.25 seconds
Request Rate,25.5 req/sec
Memory Usage,125.5 MB
```

## Real-time Monitoring

### Real-time Statistics

```bash
# Real-time monitor statistics
crawlo stats myspider --follow

# Custom monitoring interval
crawlo stats myspider --follow --interval 10
```

### Monitoring Output Example

```bash
$ crawlo stats myspider --follow --interval 5
Spider Statistics: myspider (Real-time Monitoring)
Update Time: 2023-01-01 12:00:00
Total Requests: 1000 (+5)
Successful Requests: 950 (+3)
Failed Requests: 50 (+2)
Items Scraped: 800 (+4)
Avg Response Time: 1.25 seconds
Request Rate: 25.5 req/sec
Memory Usage: 125.5 MB

Update Time: 2023-01-01 12:00:05
Total Requests: 1025 (+25)
Successful Requests: 970 (+20)
Failed Requests: 55 (+5)
Items Scraped: 820 (+20)
Avg Response Time: 1.30 seconds
Request Rate: 26.8 req/sec
Memory Usage: 128.2 MB
```

## Historical Statistics

### View History Records

```bash
# View historical statistics
crawlo stats myspider --history

# Limit history record count
crawlo stats myspider --history --limit 20
```

### Historical Statistics Output

```bash
$ crawlo stats myspider --history --limit 3
Historical Statistics: myspider
+----+---------------------+--------------+----------------+--------------+
| No | Time                | Total Reqs   | Successful Reqs | Items        |
+----+---------------------+--------------+----------------+--------------+
| 1  | 2023-01-01 10:00:00 | 500          | 475            | 400          |
| 2  | 2023-01-01 11:00:00 | 750          | 710            | 600          |
| 3  | 2023-01-01 12:00:00 | 1000         | 950            | 800          |
+----+---------------------+--------------+----------------+--------------+
```

## Statistics Reset

### Reset Statistics

```bash
# Reset statistics
crawlo stats myspider --reset

# Reset all spider statistics
crawlo stats --reset
```

## Best Practices

### 1. Performance Monitoring

```bash
# Regular performance monitoring
crawlo stats myspider --format json --output stats_$(date +%s).json

# Set performance alerts
crawlo stats myspider --verbose | grep "Request Rate" | awk '{if ($3 < 10) print "Warning: Request rate too low"}'
```

### 2. Error Analysis

```bash
# Analyze error statistics
crawlo stats myspider --format json | jq '.error_stats'

# Monitor specific error types
crawlo stats myspider --follow | grep "404"
```

### 3. Resource Monitoring

```bash
# Monitor resource usage
crawlo stats myspider --follow --interval 30

# Set resource usage alerts
crawlo stats myspider --verbose | grep "Memory Usage" | awk '{if ($3 > 500) print "Warning: High memory usage"}'
```

### 4. Automated Monitoring

```bash
# Use statistics in scripts
#!/bin/bash
stats=$(crawlo stats myspider --format json)
requests=$(echo $stats | jq '.basic_stats.total_requests')
if [ $requests -gt 10000 ]; then
    echo "Request threshold reached, preparing to restart spider"
    # Restart logic
fi
```

## Custom Statistics

### Adding Custom Statistics Items

```python
# custom_stats.py
from crawlo.stats import BaseStatsCollector

class CustomStatsCollector(BaseStatsCollector):
    def collect(self, spider):
        """Collect custom statistics"""
        stats = super().collect(spider)
        
        # Add custom statistics items
        stats['custom_metric'] = self.calculate_custom_metric()
        stats['business_stats'] = self.get_business_stats()
        
        return stats
    
    def calculate_custom_metric(self):
        # Custom metric calculation logic
        return 42
    
    def get_business_stats(self):
        # Business-related statistics
        return {'processed_orders': 100, 'revenue': 5000}
```

### Registering Custom Statistics Collector

```python
# settings.py
STATS_COLLECTORS = [
    'myproject.stats.CustomStatsCollector'
]
```

## Troubleshooting

### Common Issues

1. **Empty Statistics**
   ```bash
   # Issue: No statistics found
   # Solution: Check if spider is running
   crawlo list  # Confirm spider exists
   ps aux | grep crawlo  # Check processes
   ```

2. **Permission Issues**
   ```bash
   # Issue: Permission denied
   # Solution: Check statistics file permissions
   ls -la ~/.crawlo/stats/
   chmod 644 ~/.crawlo/stats/*
   ```

3. **Format Errors**
   ```bash
   # Issue: Invalid output format
   # Solution: Check format parameters
   crawlo stats --format table  # Use supported format
   ```

### Debugging Tips

```bash
# Show detailed statistics
crawlo stats myspider --verbose

# Check statistics file
cat ~/.crawlo/stats/myspider.json

# Real-time monitoring debug
crawlo stats myspider --follow --verbose --interval 1
```