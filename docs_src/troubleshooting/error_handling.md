# Error Handling

This document provides comprehensive information about error handling in the Crawlo framework.

## Error Types in Crawlo

### 1. Network Errors

Network errors occur during HTTP requests and include:
- Connection timeouts
- DNS resolution failures
- SSL certificate errors
- HTTP error responses (4xx, 5xx)

### 2. Parsing Errors

Parsing errors occur when processing responses:
- CSS/XPath selector errors
- JSON parsing failures
- Data extraction issues

### 3. Configuration Errors

Configuration errors occur due to invalid settings:
- Missing required settings
- Invalid setting values
- Conflicting configurations

### 4. Resource Errors

Resource errors occur due to system limitations:
- Memory exhaustion
- File I/O errors
- Database connection failures

## Built-in Error Handling Mechanisms

### Retry Middleware

Crawlo includes built-in retry middleware that automatically retries failed requests:

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.retry.RetryMiddleware',
]

# Retry configuration
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]
RETRY_PRIORITY_ADJUST = -1
```

### Error Callbacks

You can specify error callbacks for requests:

```python
def parse(self, response):
    # Normal parsing logic
    pass

def handle_error(self, failure):
    # Handle request errors
    self.logger.error(f"Request failed: {failure}")

def start_requests(self):
    yield Request(
        url='http://example.com',
        callback=self.parse,
        errback=self.handle_error
    )
```

## Custom Error Handling

### Using ErrorHandler Utility

Crawlo provides an ErrorHandler utility for consistent error handling:

```python
from crawlo.utils.error_handler import ErrorHandler

class MySpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_handler = ErrorHandler(__name__)
    
    def parse(self, response):
        try:
            # Risky operation
            data = response.json()
            yield {'data': data}
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context=f"Processing {response.url}",
                raise_error=False
            )
```

### Enhanced Error Handler

For more advanced error handling, use the EnhancedErrorHandler:

```python
from crawlo.utils.enhanced_error_handler import EnhancedErrorHandler

class MySpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_handler = EnhancedErrorHandler(__name__)
    
    async def parse(self, response):
        try:
            # Complex operation
            result = await self.complex_operation(response)
            yield result
        except ValueError as e:
            await self.error_handler.handle_error(
                e,
                context="Value error in parsing",
                error_type="value_error",
                severity="medium"
            )
        except ConnectionError as e:
            await self.error_handler.handle_error(
                e,
                context="Connection error",
                error_type="network_error",
                severity="high",
                retryable=True
            )
        except Exception as e:
            await self.error_handler.handle_error(
                e,
                context="Unexpected error",
                error_type="unknown",
                severity="critical"
            )
```

## Error Handling in Pipelines

### Robust Pipeline Implementation

```python
from crawlo.pipelines import BasePipeline
from crawlo.utils.error_handler import ErrorHandler

class RobustPipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.error_handler = ErrorHandler(__name__)
    
    async def process_item(self, item, spider):
        try:
            # Process item
            processed_item = await self.process_item_safely(item)
            return processed_item
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context=f"Processing item {item}",
                raise_error=False
            )
            # Return item unprocessed or drop it
            return item
    
    async def process_item_safely(self, item):
        # Actual processing logic
        return item
```

### Error Handling in Database Pipelines

```python
from crawlo.pipelines import BasePipeline
from crawlo.utils.error_handler import ErrorHandler
import asyncmy

class DatabasePipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.error_handler = ErrorHandler(__name__)
        self.connection = None
    
    async def open_spider(self, spider):
        try:
            self.connection = await asyncmy.connect(
                host='localhost',
                port=3306,
                user='user',
                password='password',
                db='database'
            )
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context="Database connection failed",
                raise_error=True
            )
    
    async def process_item(self, item, spider):
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO items (data) VALUES (%s)",
                    (str(item),)
                )
                await self.connection.commit()
            return item
        except asyncmy.Error as e:
            self.error_handler.handle_error(
                e,
                context=f"Database operation failed for item {item}",
                raise_error=False
            )
            # Optionally retry or drop the item
            return item
    
    async def close_spider(self, spider):
        if self.connection:
            try:
                await self.connection.ensure_closed()
            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context="Closing database connection",
                    raise_error=False
                )
```

## Error Handling in Middleware

### Robust Middleware Implementation

```python
from crawlo.middleware import RequestMiddleware
from crawlo.utils.error_handler import ErrorHandler

class RobustMiddleware(RequestMiddleware):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.error_handler = ErrorHandler(__name__)
    
    async def process_request(self, request, spider):
        try:
            # Modify request
            request.headers['X-Processed'] = 'true'
            return request
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context=f"Processing request {request.url}",
                raise_error=False
            )
            # Return request unmodified
            return request
```

## Error Monitoring and Logging

### Structured Error Logging

```python
import logging
from crawlo.utils.log import get_logger

class MySpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(__name__)
    
    def parse(self, response):
        try:
            # Processing logic
            yield {'data': response.css('.data::text').get()}
        except Exception as e:
            self.logger.error(
                "Failed to parse response",
                extra={
                    'url': response.url,
                    'status': response.status,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'spider': self.name
                }
            )
```

### Error Statistics Collection

```python
from collections import defaultdict

class ErrorStatsExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.error_counts = defaultdict(int)
    
    async def process_exception(self, request, exception, spider):
        error_type = type(exception).__name__
        self.error_counts[error_type] += 1
        spider.logger.info(f"Error stats: {dict(self.error_counts)}")
```

## Best Practices for Error Handling

### 1. Always Use Try-Except Blocks

```python
def parse(self, response):
    try:
        data = response.json()
        yield {'data': data}
    except ValueError as e:
        self.logger.error(f"JSON parsing failed: {e}")
        yield {'error': 'json_parsing_failed', 'url': response.url}
```

### 2. Implement Graceful Degradation

```python
def parse(self, response):
    try:
        # Primary data extraction
        primary_data = response.css('.primary::text').get()
    except Exception:
        primary_data = None
    
    try:
        # Secondary data extraction
        secondary_data = response.css('.secondary::text').get()
    except Exception:
        secondary_data = None
    
    if primary_data or secondary_data:
        yield {'primary': primary_data, 'secondary': secondary_data}
```

### 3. Use Appropriate Log Levels

```python
def parse(self, response):
    try:
        data = self.extract_data(response)
        self.logger.debug(f"Extracted data: {data}")
        yield data
    except ValueError as e:
        self.logger.warning(f"Data extraction warning: {e}")
    except Exception as e:
        self.logger.error(f"Data extraction failed: {e}", exc_info=True)
```

### 4. Implement Circuit Breaker Pattern

```python
import time
from collections import deque

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
```

### 5. Monitor and Alert on Errors

```python
class ErrorMonitoringExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.error_threshold = 10  # Alert if more than 10 errors
        self.errors_in_period = 0
        self.reset_timer = None
    
    async def process_exception(self, request, exception, spider):
        self.errors_in_period += 1
        
        if self.errors_in_period >= self.error_threshold:
            self.send_alert(spider, self.errors_in_period)
            self.errors_in_period = 0
    
    def send_alert(self, spider, error_count):
        # Send alert via email, Slack, etc.
        spider.logger.critical(f"High error rate detected: {error_count} errors")
```

## Error Recovery Strategies

### 1. Retry with Exponential Backoff

```python
import asyncio
import random

async def retry_with_backoff(func, *args, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func(*args)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)
```

### 2. Dead Letter Queue for Failed Items

```python
class DeadLetterQueuePipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.failed_items = []
    
    async def process_item(self, item, spider):
        try:
            # Process item
            return await self.process_item_safely(item)
        except Exception as e:
            # Add to dead letter queue
            self.failed_items.append({
                'item': item,
                'error': str(e),
                'timestamp': time.time()
            })
            spider.logger.warning(f"Item sent to DLQ: {item}")
            # Drop the item
            return None
    
    async def close_spider(self, spider):
        if self.failed_items:
            # Save failed items to a file or database
            with open('failed_items.json', 'w') as f:
                json.dump(self.failed_items, f)
```

Proper error handling is crucial for building robust and reliable web crawlers. By following these practices and using the built-in error handling mechanisms in Crawlo, you can create crawlers that gracefully handle failures and continue operating even in the face of unexpected issues.