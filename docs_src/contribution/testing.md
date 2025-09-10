# Testing Guide

This document provides comprehensive guidance on testing in the Crawlo framework, including testing strategies, tools, and best practices.

## Testing Framework

Crawlo uses [pytest](https://docs.pytest.org/) as its primary testing framework. Pytest provides a rich set of features for writing simple and scalable test suites.

### Test Organization

Tests are organized to mirror the source code structure:

```
tests/
├── conftest.py              # Global test configuration and fixtures
├── test_core/              # Core component tests
│   ├── test_engine.py
│   ├── test_scheduler.py
│   └── test_processor.py
├── test_downloader/        # Downloader tests
│   ├── test_aiohttp.py
│   ├── test_httpx.py
│   └── test_curl.py
├── test_queue/             # Queue tests
│   ├── test_memory.py
│   └── test_redis.py
├── test_filters/           # Filter tests
│   ├── test_memory.py
│   └── test_redis.py
├── test_middleware/        # Middleware tests
│   ├── test_retry.py
│   └── test_headers.py
├── test_pipelines/         # Pipeline tests
│   ├── test_console.py
│   ├── test_json.py
│   └── test_database.py
├── test_utils/             # Utility tests
│   ├── test_log.py
│   └── test_request.py
└── test_integration/       # Integration tests
    ├── test_standalone.py
    └── test_distributed.py
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### Selective Test Execution

```bash
# Run tests in a specific file
pytest tests/test_core/test_engine.py

# Run tests matching a pattern
pytest -k "test_redis"

# Run tests with specific markers
pytest -m "slow"

# Run tests and stop on first failure
pytest -x

# Run tests and drop to debugger on failure
pytest --pdb
```

### Test Coverage

```bash
# Run tests with coverage report
pytest --cov=crawlo

# Generate HTML coverage report
pytest --cov=crawlo --cov-report=html

# Generate both terminal and HTML reports
pytest --cov=crawlo --cov-report=term --cov-report=html
```

## Test Types

### Unit Tests

Unit tests focus on individual functions and classes in isolation. They should be fast and not depend on external services.

```python
# tests/test_utils/test_request.py
import pytest
from crawlo.utils.request import request_fingerprint
from crawlo.network.request import Request

def test_request_fingerprint():
    """Test that request fingerprinting works correctly."""
    request1 = Request("http://example.com", method="GET")
    request2 = Request("http://example.com", method="GET")
    request3 = Request("http://example.com", method="POST")
    
    # Same requests should have same fingerprint
    assert request_fingerprint(request1) == request_fingerprint(request2)
    
    # Different requests should have different fingerprints
    assert request_fingerprint(request1) != request_fingerprint(request3)
```

### Integration Tests

Integration tests verify that multiple components work together correctly.

```python
# tests/test_integration/test_scheduler_queue.py
import pytest
from crawlo.core.scheduler import Scheduler
from crawlo.queue.memory_queue import MemoryQueue
from crawlo.network.request import Request

@pytest.fixture
def scheduler():
    """Create a scheduler with memory queue for testing."""
    scheduler = Scheduler(crawler=Mock())
    scheduler.queue = MemoryQueue(crawler=Mock())
    return scheduler

def test_scheduler_enqueue_dequeue(scheduler):
    """Test that scheduler can enqueue and dequeue requests."""
    request = Request("http://example.com")
    
    # Enqueue request
    scheduler.enqueue_request(request)
    
    # Dequeue request
    dequeued = scheduler.next_request()
    
    assert dequeued.url == request.url
```

### Functional Tests

Functional tests verify complete crawling scenarios.

```python
# tests/test_functional/test_simple_crawl.py
import pytest
from crawlo.crawler import Crawler
from crawlo.spider import Spider

class TestSpider(Spider):
    name = "test"
    start_urls = ["http://httpbin.org/get"]
    
    def parse(self, response):
        yield {"url": response.url, "status": response.status}

def test_simple_crawl():
    """Test a simple crawling scenario."""
    crawler = Crawler(TestSpider)
    
    # Run the crawler
    crawler.crawl()
    
    # Verify results
    assert crawler.stats.get_value("item_scraped_count", 0) > 0
```

### Performance Tests

Performance tests verify that components meet performance requirements.

```python
# tests/test_performance/test_queue_performance.py
import pytest
import time
from crawlo.queue.memory_queue import MemoryQueue

@pytest.mark.slow
def test_queue_performance():
    """Test queue performance with large number of requests."""
    queue = MemoryQueue(crawler=Mock())
    num_requests = 10000
    
    # Measure enqueue performance
    start_time = time.time()
    for i in range(num_requests):
        request = Request(f"http://example.com/{i}")
        queue.push(request)
    enqueue_time = time.time() - start_time
    
    # Measure dequeue performance
    start_time = time.time()
    for _ in range(num_requests):
        queue.pop()
    dequeue_time = time.time() - start_time
    
    # Assert performance requirements
    assert enqueue_time < 1.0  # Should enqueue 10k requests in < 1 second
    assert dequeue_time < 1.0   # Should dequeue 10k requests in < 1 second
```

## Test Fixtures

### Built-in Fixtures

Crawlo provides several built-in fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_crawler():
    """Create a mock crawler for testing."""
    return Mock()

@pytest.fixture
def mock_spider():
    """Create a mock spider for testing."""
    spider = Mock()
    spider.logger = Mock()
    return spider

@pytest.fixture
def sample_request():
    """Create a sample request for testing."""
    from crawlo.network.request import Request
    return Request("http://example.com", method="GET")

@pytest.fixture
def sample_response():
    """Create a sample response for testing."""
    from crawlo.network.response import Response
    return Response("http://example.com", body=b"test response")
```

### Custom Fixtures

Create custom fixtures for complex test setups:

```python
# tests/test_downloader/conftest.py
import pytest
import asyncio
from unittest.mock import Mock

@pytest.fixture
async def http_server():
    """Create a mock HTTP server for testing."""
    # Implementation of mock HTTP server
    server = MockHTTPServer()
    await server.start()
    yield server
    await server.stop()

@pytest.fixture
def downloader_settings():
    """Create settings for downloader tests."""
    return {
        "CONCURRENCY": 4,
        "DOWNLOAD_DELAY": 0.1,
        "DOWNLOAD_TIMEOUT": 30,
    }
```

## Mocking and Stubbing

### Using unittest.mock

Use `unittest.mock` for mocking dependencies:

```python
from unittest.mock import Mock, patch, MagicMock

def test_downloader_with_mocked_session():
    """Test downloader with mocked HTTP session."""
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value.__aenter__.return_value = Mock(
            status=200,
            text=AsyncMock(return_value="test content")
        )
        
        downloader = AioHttpDownloader(settings={})
        response = downloader.download(Request("http://example.com"))
        
        assert response.status == 200
        assert response.text == "test content"
```

### Async Mocking

For async code, use `AsyncMock`:

```python
from unittest.mock import AsyncMock

def test_async_pipeline():
    """Test async pipeline with mocked dependencies."""
    pipeline = MyPipeline(crawler=Mock())
    pipeline.db_connection = AsyncMock()
    
    # Mock async method
    pipeline.db_connection.execute = AsyncMock()
    
    # Test the pipeline
    item = {"data": "test"}
    result = await pipeline.process_item(item, spider=Mock())
    
    # Verify async method was called
    pipeline.db_connection.execute.assert_called_once()
```

## Test Data Management

### Factory Functions

Create factory functions for test data:

```python
# tests/factories.py
from crawlo.network.request import Request
from crawlo.network.response import Response

def create_request(url="http://example.com", **kwargs):
    """Create a request for testing."""
    return Request(url, **kwargs)

def create_response(url="http://example.com", body=b"", status=200, **kwargs):
    """Create a response for testing."""
    return Response(url, body=body, status=status, **kwargs)

def create_item(**kwargs):
    """Create an item for testing."""
    return {"id": 1, "name": "test", **kwargs}
```

### Parameterized Tests

Use parameterized tests for testing multiple scenarios:

```python
import pytest

@pytest.mark.parametrize("url,expected_fingerprint", [
    ("http://example.com", "abc123"),
    ("http://example.com/", "abc123"),
    ("http://example.com?param=value", "def456"),
])
def test_request_fingerprint_variations(url, expected_fingerprint):
    """Test request fingerprinting with different URLs."""
    request = Request(url)
    assert request_fingerprint(request) == expected_fingerprint
```

## Testing Async Code

### Async Test Functions

Use `async` for testing async functions:

```python
import pytest

class TestAsyncDownloader:
    @pytest.mark.asyncio
    async def test_async_download(self):
        """Test async download functionality."""
        downloader = AioHttpDownloader(settings={})
        request = Request("http://example.com")
        
        response = await downloader.download(request)
        
        assert response.status == 200
        assert response.url == "http://example.com"
```

### Async Fixtures

Create async fixtures for async test setup:

```python
@pytest.fixture
async def async_downloader():
    """Create an async downloader for testing."""
    downloader = AioHttpDownloader(settings={})
    await downloader.initialize()
    yield downloader
    await downloader.close()

@pytest.mark.asyncio
async def test_with_async_fixture(async_downloader):
    """Test using async fixture."""
    response = await async_downloader.download(Request("http://example.com"))
    assert response is not None
```

## Testing Distributed Components

### Redis Testing

For testing Redis components, use `fakeredis` or a test Redis instance:

```python
import pytest
import fakeredis
from crawlo.filters.aioredis_filter import AioRedisFilter

@pytest.fixture
def redis_filter():
    """Create a Redis filter with fake Redis for testing."""
    redis_client = fakeredis.FakeRedis()
    filter_instance = AioRedisFilter(crawler=Mock())
    filter_instance.redis_client = redis_client
    return filter_instance

def test_redis_filter_deduplication(redis_filter):
    """Test Redis filter deduplication."""
    request = Request("http://example.com")
    
    # First request should not be seen
    assert not redis_filter.request_seen(request)
    
    # Mark as seen
    redis_filter.mark_request_seen(request)
    
    # Second request should be seen
    assert redis_filter.request_seen(request)
```

### Mock Distributed Testing

Mock distributed components for unit testing:

```python
def test_distributed_scheduler():
    """Test distributed scheduler with mocked components."""
    with patch('crawlo.queue.redis_priority_queue.RedisPriorityQueue') as mock_queue:
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        
        scheduler = DistributedScheduler(crawler=Mock())
        
        request = Request("http://example.com")
        scheduler.enqueue_request(request)
        
        mock_queue_instance.push.assert_called_once_with(request)
```

## Test Markers

### Built-in Markers

Use markers to categorize tests:

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "distributed: marks tests that require distributed components",
    "redis: marks tests that require Redis",
]
```

### Using Markers

```python
import pytest

@pytest.mark.slow
def test_large_dataset_processing():
    """Test processing of large datasets."""
    # Test implementation
    pass

@pytest.mark.integration
def test_end_to_end_crawl():
    """Test complete crawling workflow."""
    # Test implementation
    pass

@pytest.mark.distributed
@pytest.mark.redis
def test_redis_distributed_crawling():
    """Test distributed crawling with Redis."""
    # Test implementation
    pass
```

## Continuous Integration

### GitHub Actions Configuration

Example GitHub Actions workflow for testing:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest --cov=crawlo --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

## Best Practices

### 1. Write Clear Test Names

```python
# Good
def test_scheduler_handles_duplicate_requests():
    pass

# Avoid
def test_scheduler():
    pass
```

### 2. Test One Thing at a Time

```python
# Good - focused test
def test_request_fingerprint_consistency():
    pass

def test_request_fingerprint_uniqueness():
    pass

# Avoid - scattered test
def test_request_fingerprint():
    # Tests multiple things
    pass
```

### 3. Use Appropriate Assertions

```python
# Good - specific assertions
assert response.status == 200
assert "expected_text" in response.text

# Avoid - generic assertions
assert response is not None
```

### 4. Clean Up Test Data

```python
def test_file_pipeline_creates_file(tmp_path):
    """Test that file pipeline creates output file."""
    # Setup
    output_file = tmp_path / "output.json"
    
    # Test
    pipeline = JsonPipeline(output_file=str(output_file))
    # ... test implementation
    
    # Cleanup happens automatically with tmp_path fixture
```

### 5. Mock External Dependencies

```python
def test_downloader_without_network():
    """Test downloader without actual network calls."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock network response
        mock_get.return_value.__aenter__.return_value = Mock(
            status=200,
            text=AsyncMock(return_value="mocked response")
        )
        
        # Test implementation
        pass
```

By following this testing guide, you'll be able to write effective tests for Crawlo components and ensure the framework maintains high quality and reliability.