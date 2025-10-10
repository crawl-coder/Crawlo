# crawlo.middleware

Middleware module for the Crawlo framework.

## Overview

The middleware module provides a hook system for processing requests and responses. Middleware can modify requests before they are sent and responses after they are received.

## Classes

### Middleware

Base class for all middleware.

#### `__init__(self, crawler)`

Initialize the middleware.

**Parameters:**
- `crawler` (Crawler): The crawler instance

#### `process_request(self, request, spider)`

Process a request before it is sent.

**Parameters:**
- `request` (Request): The request object
- `spider` (Spider): The spider instance

**Returns:**
- None, Request, or Response object

#### `process_response(self, request, response, spider)`

Process a response after it is received.

**Parameters:**
- `request` (Request): The original request object
- `response` (Response): The response object
- `spider` (Spider): The spider instance

**Returns:**
- None, Request, or Response object

#### `process_exception(self, request, exception, spider)`

Process an exception that occurred during request processing.

**Parameters:**
- `request` (Request): The request object
- `exception` (Exception): The exception that occurred
- `spider` (Spider): The spider instance

**Returns:**
- None, Request, or Response object

## Built-in Middlewares

### RequestIgnoreMiddleware

Filters out unwanted requests.

### DownloadDelayMiddleware

Adds delays between requests.

### DefaultHeaderMiddleware

Adds default headers to requests.

### ProxyMiddleware

Handles proxy configuration for requests.

### RetryMiddleware

Implements retry logic for failed requests.

## Usage Example

```python
from crawlo.middleware import Middleware

class MyMiddleware(Middleware):
    def process_request(self, request, spider):
        # Modify request before sending
        request.headers['X-Custom-Header'] = 'value'
        return request
    
    def process_response(self, request, response, spider):
        # Modify response after receiving
        if response.status_code == 403:
            # Handle 403 errors
            pass
        return response
    
    def process_exception(self, request, exception, spider):
        # Handle exceptions
        pass

# Register middleware in settings
MIDDLEWARES = {
    'myproject.middlewares.MyMiddleware': 500,
}
```