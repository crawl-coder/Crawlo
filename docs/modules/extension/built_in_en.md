# Built-in Extensions

Crawlo provides several built-in extension components that add additional functionality to the crawling process. These extension components can be enabled or disabled through configuration.

## Overview

Built-in extensions provide auxiliary functionality for web crawling:

- Logging and monitoring
- Performance profiling
- Health checking
- Statistics collection
- Debugging assistance

## LogIntervalExtension

Logs crawling progress at regular intervals to monitor ongoing operations.

### Features

- Configurable logging intervals
- Progress reporting
- Performance metrics
- Real-time monitoring

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
]

# Log interval settings
LOG_INTERVAL = 60  # Log every 60 seconds
```

## LogStats

Logs final statistics when crawling completes to provide a summary of operations.

### Features

- Comprehensive statistics collection
- Final summary reporting
- Performance metrics
- Resource usage tracking

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.log_stats.LogStats',
]

# Log stats settings
STATS_DUMP = True
```

## CustomLoggerExtension

Provides custom logging functionality for specialized logging requirements.

### Features

- Custom log formats
- Multiple log outputs
- Configurable log levels
- Structured logging

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# Custom logger settings
CUSTOM_LOGGER_ENABLED = True
CUSTOM_LOGGER_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

## MemoryMonitorExtension

Monitors memory usage during crawling to detect memory leaks or excessive usage.

### Features

- Real-time memory monitoring
- Memory usage alerts
- Periodic reporting
- Threshold-based warnings

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]

# Memory monitor settings
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL = 60  # Check every 60 seconds
MEMORY_WARNING_THRESHOLD = 80.0  # Warn at 80% memory usage
MEMORY_CRITICAL_THRESHOLD = 90.0  # Critical at 90% memory usage
```

## RequestRecorderExtension

Records all requests for debugging and analysis purposes.

### Features

- Request logging
- Response metadata recording
- File-based storage
- Configurable recording options

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.request_recorder.RequestRecorderExtension',
]

# Request recorder settings
REQUEST_RECORDER_ENABLED = True
REQUEST_RECORDER_OUTPUT_DIR = 'requests_log'
REQUEST_RECORDER_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## PerformanceProfilerExtension

Profiles performance of the crawling process to identify bottlenecks and optimization opportunities.

### Features

- Performance profiling
- Function timing
- Resource usage tracking
- Periodic profiling reports

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
]

# Performance profiler settings
PERFORMANCE_PROFILER_ENABLED = True
PERFORMANCE_PROFILER_OUTPUT_DIR = 'profiling'
PERFORMANCE_PROFILER_INTERVAL = 300  # Profile every 5 minutes
```

## HealthCheckExtension

Monitors the health of the crawling process to ensure proper operation.

### Features

- Health status monitoring
- Component health checks
- Alerting mechanisms
- Recovery actions

### Configuration

```python
# In settings.py
EXTENSIONS = [
    'crawlo.extension.health_check.HealthCheckExtension',
]

# Health check settings
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_INTERVAL = 60  # Check every 60 seconds
```

## Usage Example

To enable multiple built-in extensions:

```python
# In settings.py
EXTENSIONS = [
    # Logging extensions
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
    
    # Monitoring extensions
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
    
    # Utility extensions
    'crawlo.extension.request_recorder.RequestRecorderExtension',
    'crawlo.extension.health_check.HealthCheckExtension',
]
```

## Performance Considerations

- Enable only necessary extensions to minimize overhead
- Configure appropriate intervals for periodic extensions
- Monitor extension resource usage
- Disable debugging extensions in production
- Use lightweight implementations for high-frequency events

## Extension Integration

Built-in extensions integrate with the crawler through event hooks:

```python
class ExampleExtension:
    def __init__(self, crawler):
        # Initialize extension
        pass
        
    def spider_opened(self, spider):
        # Handle spider opened event
        pass
        
    def response_received(self, response, spider):
        # Handle response received event
        pass
        
    def item_successful(self, item, spider):
        # Handle item processed event
        pass
        
    def spider_closed(self, spider, reason):
        # Handle spider closed event
        pass
```

## Best Practices

1. **Selective Enablement**: Only enable extensions you need
2. **Performance Monitoring**: Monitor extension impact on crawling performance
3. **Configuration**: Properly configure extension settings for your use case
4. **Production vs Development**: Use different extension sets for different environments
5. **Error Handling**: Extensions should handle errors gracefully without affecting crawling