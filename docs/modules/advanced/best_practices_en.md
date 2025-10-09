# Best Practices

This document summarizes the best practices for developing and deploying crawler projects using the Crawlo framework, helping developers write high-quality, maintainable, and high-performance crawler code.

## Project Structure

### Recommended Project Structure

```bash
my_crawler_project/
├── crawlo.cfg              # Main configuration file
├── settings.py             # Configuration module
├── items.py                # Data item definitions
├── pipelines.py            # Data pipelines
├── middlewares.py          # Middlewares
├── extensions.py           # Extensions
├── spiders/                # Spider module
│   ├── __init__.py
│   ├── base_spider.py      # Base spider class
│   └── my_spider.py        # Specific spider implementation
├── utils/                  # Utility module
│   ├── __init__.py
│   ├── parsers.py          # Parsing utilities
│   └── helpers.py          # Helper functions
├── tests/                  # Test code
│   ├── __init__.py
│   ├── test_spiders.py
│   └── test_pipelines.py
├── docs/                   # Documentation
└── requirements.txt        # Dependency list
```

### Modular Design

```python
# base_spider.py - Base spider class
from crawlo.spider import Spider

class BaseSpider(Spider):
    """Base class for all spiders"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_logging()
        self.setup_metrics()
    
    def setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def setup_metrics(self):
        """Setup metrics monitoring"""
        self.metrics = {
            'requests': 0,
            'items': 0,
            'errors': 0
        }
    
    def closed(self, reason):
        """Cleanup when spider closes"""
        self.logger.info(f"Spider {self.name} closed, reason: {reason}")
        self.report_metrics()
    
    def report_metrics(self):
        """Report metrics"""
        self.logger.info(f"Statistics: {self.metrics}")
```

## Spider Development

### Item Design

```python
# items.py
from crawlo.items import Item

class ProductItem(Item):
    """Product data item"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.required_fields = ['name', 'price']
        self.field_types = {
            'name': str,
            'price': float,
            'description': str,
            'images': list,
            'category': str
        }
    
    def validate(self):
        """Data validation"""
        # Check required fields
        for field in self.required_fields:
            if not self.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Check field types
        for field, expected_type in self.field_types.items():
            if field in self and not isinstance(self[field], expected_type):
                self.logger.warning(f"Field {field} has wrong type")
                return False
        
        # Business logic validation
        if self.get('price', 0) < 0:
            self.logger.warning("Price cannot be negative")
            return False
        
        return True
    
    def clean(self):
        """Data cleaning"""
        # Clean string fields
        for field in ['name', 'description']:
            if field in self:
                self[field] = self[field].strip()
        
        # Format price
        if 'price' in self:
            self['price'] = round(float(self['price']), 2)
        
        return self
```

## Configuration Management

### Environment Isolation Configuration

```python
# settings.py
import os

class BaseConfig:
    """Base configuration"""
    # Concurrency configuration
    CONCURRENCY = 16
    DOWNLOAD_DELAY = 0.5
    DOWNLOAD_TIMEOUT = 30
    
    # Queue configuration
    SCHEDULER_MAX_QUEUE_SIZE = 10000
    
    # Log configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = None

class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    CONCURRENCY = 5
    DOWNLOAD_DELAY = 1.0
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = 'logs/dev.log'

class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    CONCURRENCY = 50
    DOWNLOAD_DELAY = 0.1
    LOG_LEVEL = 'WARNING'
    LOG_FILE = 'logs/prod.log'
    LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT = 10

class TestingConfig(BaseConfig):
    """Testing environment configuration"""
    CONCURRENCY = 1
    DOWNLOAD_DELAY = 0.0
    LOG_LEVEL = 'DEBUG'

# Select configuration based on environment variable
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

def get_config():
    env = os.getenv('CRAWLO_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)()
```

## Error Handling

### Exception Handling Strategy

```python
# error_handlers.py
import asyncio
import logging
from functools import wraps

def retry_on_failure(max_retries=3, delay=1.0):
    """Retry decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logging.error(f"Function {func.__name__} failed, max retries reached: {e}")
                        raise last_exception
            
            return None
        return wrapper
    return decorator

class ErrorHandler:
    """Error handler"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_parsing_error(self, response, exception):
        """Handle parsing errors"""
        self.logger.error(f"Failed to parse page {response.url}: {exception}")
        
        # Log error details
        error_info = {
            'url': response.url,
            'status_code': response.status_code,
            'exception': str(exception),
            'timestamp': datetime.now().isoformat()
        }
        
        # Can store error information in database or file
        self._log_error(error_info)
        
        # Decide whether to retry based on error type
        if self._should_retry(exception):
            return self._retry_request(response.request)
        
        return None
    
    def _log_error(self, error_info):
        """Log error information"""
        # Implement error logging logic
        pass
    
    def _should_retry(self, exception):
        """Determine whether to retry"""
        # Implement retry logic
        return True
    
    def _retry_request(self, request):
        """Retry request"""
        # Implement request retry logic
        request.retry_times += 1
        return request
```

## Performance Optimization

### Async Processing

```python
# async_utils.py
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor

class AsyncProcessor:
    """Async processor"""
    
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = asyncio.Semaphore(max_workers * 2)
    
    async def process_batch(self, items, processor_func):
        """Batch async processing"""
        tasks = []
        async with self.semaphore:
            for item in items:
                task = asyncio.create_task(
                    self._process_item(item, processor_func)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]
    
    async def _process_item(self, item, processor_func):
        """Process single item"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, processor_func, item)
    
    async def write_to_file(self, filename, data):
        """Async write to file"""
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(data)

# Usage example
async def main():
    processor = AsyncProcessor(max_workers=8)
    
    # Batch process data
    items = [f"item_{i}" for i in range(1000)]
    results = await processor.process_batch(items, lambda x: x.upper())
    
    # Async write results
    await processor.write_to_file('output.txt', '\n'.join(results))
```

## Testing Strategy

### Unit Testing

```python
# test_spiders.py
import unittest
from unittest.mock import Mock, patch
from crawlo.spider import Spider
from crawlo.network import Response, Request

class TestMySpider(unittest.TestCase):
    """Spider unit tests"""
    
    def setUp(self):
        """Test initialization"""
        self.spider = MySpider(name='test_spider')
    
    def test_parse_product(self):
        """Test product page parsing"""
        # Create mock response
        mock_response = Mock(spec=Response)
        mock_response.url = 'https://example.com/product/123'
        mock_response.extract_text.return_value = 'Test Product'
        mock_response.extract_attrs.return_value = ['image1.jpg', 'image2.jpg']
        
        # Execute parsing
        items = list(self.spider.parse_product(mock_response))
        
        # Verify results
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Test Product')
        self.assertEqual(len(items[0]['images']), 2)
    
    def test_parse_with_pagination(self):
        """Test pagination parsing"""
        mock_response = Mock(spec=Response)
        mock_response.url = 'https://example.com/products'
        mock_response.extract_attrs.return_value = ['/product/1', '/product/2']
        mock_response.extract_attr.return_value = '/products?page=2'
        
        requests = list(self.spider.parse(mock_response))
        
        # Verify number of generated requests
        self.assertEqual(len(requests), 3)  # 2 product requests + 1 pagination request

# test_pipelines.py
class TestProductPipeline(unittest.TestCase):
    """Pipeline unit tests"""
    
    def setUp(self):
        self.pipeline = ProductPipeline()
    
    def test_process_item_valid(self):
        """Test valid item processing"""
        item = ProductItem(name='Test Product', price=99.99)
        result = self.pipeline.process_item(item, Mock())
        
        self.assertEqual(result['name'], 'Test Product')
        self.assertEqual(result['price'], 99.99)
    
    def test_process_item_invalid(self):
        """Test invalid item processing"""
        item = ProductItem(name='', price=-10)  # Invalid data
        result = self.pipeline.process_item(item, Mock())
        
        self.assertIsNone(result)  # Invalid data should be discarded
```

## Deployment and Operations

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p logs

# Expose port (if needed)
EXPOSE 8000

# Run command
CMD ["crawlo", "run", "my_spider"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  crawler:
    build: .
    environment:
      - CRAWLO_ENV=production
      - REDIS_HOST=redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

By following these best practices, you can develop high-quality, maintainable, and high-performance Crawlo crawler projects. It is recommended to select appropriate practice methods based on specific project requirements and continuously optimize and improve during actual development.