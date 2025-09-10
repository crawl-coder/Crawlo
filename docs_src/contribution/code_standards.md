# Code Standards

This document outlines the coding standards and best practices for contributing to the Crawlo framework.

## Python Version and Compatibility

Crawlo supports Python 3.10 and higher. All code must be compatible with these versions.

### Supported Python Versions

- Python 3.10
- Python 3.11
- Python 3.12

### Version-Specific Features

When using Python version-specific features, ensure they are available in all supported versions or provide appropriate fallbacks.

## Code Style

### PEP 8 Compliance

All code must follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines. The project uses automated tools to enforce these standards:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting

### Line Length

Maximum line length is 88 characters (Black's default). This allows for better readability on various screen sizes.

### Naming Conventions

#### Variables and Functions

Use `snake_case` for variables and functions:

```python
# Good
user_name = "John"
def calculate_total():
    pass

# Avoid
userName = "John"
def CalculateTotal():
    pass
```

#### Classes

Use `PascalCase` for classes:

```python
# Good
class Spider:
    pass

class RequestMiddleware:
    pass
```

#### Constants

Use `UPPER_CASE` for constants:

```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Avoid
maxRetries = 3
default_timeout = 30
```

#### Private Members

Prefix private members with an underscore:

```python
class MyClass:
    def __init__(self):
        self._private_var = "private"
        self.public_var = "public"
    
    def _private_method(self):
        pass
```

### Imports

#### Import Order

Imports should be grouped and ordered as follows:

1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

Each group should be separated by a blank line:

```python
import os
import sys
from collections import defaultdict

import aiohttp
import redis

from crawlo.core.engine import Engine
from crawlo.utils.log import get_logger
```

#### Import Formatting

Use `isort` to automatically format imports. The configuration is in `pyproject.toml`:

```toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
```

#### Avoid Wildcard Imports

Avoid wildcard imports as they make code harder to understand:

```python
# Avoid
from module import *

# Prefer
from module import specific_function, SpecificClass
```

### String Formatting

Use f-strings for string formatting (Python 3.6+):

```python
# Good
name = "John"
age = 30
message = f"Hello, {name}! You are {age} years old."

# Acceptable for simple cases
message = "Hello, %s!" % name

# Avoid
message = "Hello, " + name + "!"
```

### Type Hints

Use type hints to improve code clarity and enable better tooling support:

```python
from typing import Optional, List, Dict, Any

def process_items(items: List[Dict[str, Any]]) -> Optional[str]:
    """Process a list of items and return a result."""
    if not items:
        return None
    
    # Process items
    return "processed"

class Spider:
    def __init__(self, name: str, settings: Optional[Dict[str, Any]] = None):
        self.name = name
        self.settings = settings or {}
```

### Comments and Docstrings

#### Comments

Use comments to explain why something is done, not what is done:

```python
# Good: Explain the reason
# Retry on network errors as they might be transient
if isinstance(error, NetworkError):
    retry_request()

# Avoid: State the obvious
# Increment counter
counter += 1
```

#### Docstrings

Use docstrings to document modules, classes, and functions. Follow the Google Python Style Guide format:

```python
def fetch_data(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch data from a URL.
    
    Args:
        url: The URL to fetch data from.
        timeout: Request timeout in seconds. Defaults to 30.
    
    Returns:
        A dictionary containing the fetched data.
    
    Raises:
        NetworkError: If the request fails due to network issues.
        TimeoutError: If the request times out.
    """
    pass
```

### Exception Handling

#### Specific Exceptions

Catch specific exceptions rather than using bare except clauses:

```python
# Good
try:
    response = await fetch_url(url)
except NetworkError:
    logger.warning(f"Network error fetching {url}")
except TimeoutError:
    logger.warning(f"Timeout fetching {url}")

# Avoid
try:
    response = await fetch_url(url)
except Exception:
    logger.warning(f"Error fetching {url}")
```

#### Exception Context

Preserve exception context when re-raising:

```python
# Good
try:
    process_data(data)
except ValueError as e:
    logger.error(f"Invalid data: {data}")
    raise RuntimeError("Data processing failed") from e

# Avoid
try:
    process_data(data)
except ValueError:
    raise RuntimeError("Data processing failed")
```

## Asynchronous Programming

### async/await Usage

Use `async`/`await` syntax for asynchronous operations:

```python
import asyncio

async def fetch_data(url: str) -> str:
    """Fetch data asynchronously."""
    # Simulate async operation
    await asyncio.sleep(1)
    return f"Data from {url}"

async def process_urls(urls: List[str]) -> List[str]:
    """Process multiple URLs concurrently."""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results
```

### Concurrency Control

Use semaphores or other mechanisms to control concurrency:

```python
import asyncio

class DataFetcher:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_limit(self, url: str) -> str:
        async with self.semaphore:
            return await self.fetch_data(url)
```

## Error Handling

### Error Classes

Create specific error classes for different error conditions:

```python
class CrawloError(Exception):
    """Base exception for Crawlo errors."""
    pass

class NetworkError(CrawloError):
    """Raised when a network error occurs."""
    pass

class ConfigurationError(CrawloError):
    """Raised when there's a configuration error."""
    pass
```

### Error Logging

Log errors with appropriate context and log levels:

```python
import logging

logger = logging.getLogger(__name__)

def process_item(item):
    try:
        # Process item
        result = do_something(item)
        logger.debug(f"Processed item: {item}")
        return result
    except ValueError as e:
        logger.warning(f"Invalid item data: {item}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing item: {item}", exc_info=True)
        raise
```

## Testing Standards

### Test Structure

Organize tests to mirror the source code structure:

```
tests/
├── test_core/
│   ├── test_engine.py
│   └── test_scheduler.py
├── test_downloader/
│   ├── test_aiohttp.py
│   └── test_httpx.py
└── test_utils/
    ├── test_log.py
    └── test_request.py
```

### Test Naming

Use descriptive test names that indicate what is being tested:

```python
def test_engine_starts_successfully():
    """Test that the engine starts without errors."""
    pass

def test_scheduler_handles_duplicate_requests():
    """Test that the scheduler properly handles duplicate requests."""
    pass
```

### Test Documentation

Document complex test setups and assertions:

```python
def test_pipeline_processes_items_correctly():
    """Test that the pipeline processes items correctly.
    
    This test verifies that:
    1. Items are processed in the correct order
    2. Item data is transformed as expected
    3. Errors are handled appropriately
    """
    # Test implementation
    pass
```

### Mocking and Fixtures

Use mocking appropriately to isolate units under test:

```python
from unittest.mock import Mock, patch

def test_downloader_handles_network_errors():
    """Test that the downloader handles network errors gracefully."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = aiohttp.ClientError("Network error")
        
        downloader = AioHttpDownloader(settings={})
        with pytest.raises(NetworkError):
            downloader.download(Request("http://example.com"))
```

## Performance Considerations

### Memory Efficiency

Avoid creating unnecessary objects and use generators when possible:

```python
# Good: Generator
def process_items(items):
    for item in items:
        yield process_item(item)

# Avoid: Creating large lists
def process_items(items):
    return [process_item(item) for item in items]
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

class Spider:
    @lru_cache(maxsize=128)
    def parse_selector(self, css_selector: str):
        """Cache parsed CSS selectors."""
        return parsel.CSSSelector(css_selector)
```

### Lazy Initialization

Initialize expensive resources only when needed:

```python
class DatabasePipeline:
    def __init__(self):
        self._connection = None
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection
```

## Security Considerations

### Input Validation

Validate all inputs to prevent injection attacks:

```python
def sanitize_url(url: str) -> str:
    """Sanitize URL to prevent injection attacks."""
    # Validate URL format
    parsed = urlparse(url)
    if not parsed.scheme in ('http', 'https'):
        raise ValueError("Invalid URL scheme")
    
    # Additional validation
    return url
```

### Secure Configuration

Handle sensitive configuration securely:

```python
import os

class RedisConfig:
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        # Never log passwords
        self.password = os.getenv('REDIS_PASSWORD')  # Don't log this!
```

## Documentation Standards

### Code Documentation

Document all public APIs with clear docstrings:

```python
class Scheduler:
    """Manages request scheduling and deduplication.
    
    The scheduler coordinates between the engine and queues to ensure
    efficient request processing while preventing duplicate work.
    """
    
    def enqueue_request(self, request: Request) -> bool:
        """Add a request to the queue.
        
        Args:
            request: The request to enqueue.
            
        Returns:
            True if the request was added, False if it was a duplicate.
        """
        pass
```

### Example Documentation

Provide clear examples in documentation:

```python
def custom_middleware_example():
    """Example of creating custom middleware.
    
    To create custom middleware, inherit from the appropriate base class:
    
    ```python
    from crawlo.middleware import RequestMiddleware
    
    class CustomHeaderMiddleware(RequestMiddleware):
        async def process_request(self, request, spider):
            request.headers['X-Custom'] = 'Value'
            return request
    ```
    
    Then add it to your settings:
    
    ```python
    MIDDLEWARES = [
        'myproject.middlewares.CustomHeaderMiddleware',
    ]
    ```
    """
    pass
```

## Version Control Standards

### Commit Messages

Write clear, concise commit messages following the conventional commits format:

```
feat: Add support for HTTP/2 in httpx downloader
fix: Resolve memory leak in Redis queue implementation
docs: Update configuration documentation
test: Add tests for error handling in pipelines
refactor: Simplify scheduler initialization logic
```

### Branch Naming

Use descriptive branch names:

```
feature/http2-support
bugfix/memory-leak-redis
docs/update-configuration-guide
refactor/scheduler-optimization
```

By following these code standards, you'll help maintain the quality and consistency of the Crawlo framework, making it easier for everyone to contribute and use.