# Built-in Middlewares

Crawlo provides several built-in middleware components that handle common web scraping tasks. These middleware components can be enabled or disabled through configuration.

## Overview

Built-in middlewares provide essential functionality for web scraping:

- Request filtering and preprocessing
- Response handling and postprocessing
- Error handling and retry logic
- Performance optimization

## RequestIgnoreMiddleware

Filters out unwanted requests based on various criteria.

### Features

- URL pattern matching
- Domain filtering
- Request method filtering
- Custom filtering rules

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
]

# Request ignore settings
IGNORE_DOMAINS = ['example.com']
IGNORE_URLS = [r'/admin/.*']
IGNORE_METHODS = ['POST']
```

## DownloadDelayMiddleware

Adds delays between requests to be respectful to target servers.

### Features

- Configurable delay times
- Random delay ranges
- Per-domain delay settings

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
]

# Delay settings
DOWNLOAD_DELAY = 1.0
RANDOM_RANGE = (0.8, 1.2)
RANDOMNESS = True
```

## DefaultHeaderMiddleware

Adds default headers to all requests to make them appear more like browser requests.

### Features

- Customizable default headers
- User-Agent rotation
- Common header presets

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# Default headers
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
```

## ProxyMiddleware

Handles proxy configuration for requests.

### Features

- Proxy rotation
- Authentication support
- Proxy failure detection
- Fallback mechanisms

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.proxy.ProxyMiddleware',
]

# Proxy settings
PROXY_ENABLED = True
PROXY_API_URL = "http://proxy-service.com/api"
PROXY_EXTRACTOR = "proxy"
PROXY_REFRESH_INTERVAL = 60
```

## RetryMiddleware

Implements retry logic for failed requests.

### Features

- Configurable retry counts
- HTTP status code based retry
- Exponential backoff
- Retry priority adjustment

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.retry.RetryMiddleware',
]

# Retry settings
MAX_RETRY_TIMES = 3
RETRY_PRIORITY = -1
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]
```

## ResponseCodeMiddleware

Processes HTTP response codes and handles special cases.

### Features

- Status code categorization
- Error response handling
- Redirect processing
- Custom status code actions

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
]

# Response code settings
IGNORE_HTTP_CODES = [403, 404]
ALLOWED_CODES = [200, 201, 202]
```

## ResponseFilterMiddleware

Filters responses based on content or other criteria.

### Features

- Content-based filtering
- Size-based filtering
- MIME type filtering
- Custom filter functions

### Configuration

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# Response filter settings
MIN_RESPONSE_SIZE = 1024
MAX_RESPONSE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ['text/html', 'application/json']
```

## Usage Example

To enable multiple built-in middlewares:

```python
# In settings.py
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]
```

## Performance Considerations

- Order middleware appropriately - place lightweight filters first
- Disable unused middleware to reduce overhead
- Configure appropriate retry limits to avoid excessive requests
- Use efficient filtering patterns to minimize processing time