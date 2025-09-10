# Middleware API Reference

This document provides detailed information about the middleware components in the Crawlo framework.

## MiddlewareManager Class

The MiddlewareManager is responsible for managing and executing middleware components.

### Class: MiddlewareManager

```python
class MiddlewareManager(object):
    def __init__(self, crawler, middleware_classes):
        # Initialize the middleware manager
        pass
    
    async def process_request(self, request, spider):
        # Process a request through all request middleware
        pass
    
    async def process_response(self, request, response, spider):
        # Process a response through all response middleware
        pass
    
    async def process_exception(self, request, exception, spider):
        # Process an exception through all exception middleware
        pass
```

#### Parameters

- `crawler` (Crawler): The crawler instance to associate with this middleware manager.
- `middleware_classes` (list): A list of middleware class paths to load.

#### Methods

##### `__init__(self, crawler, middleware_classes)`
Initialize the middleware manager with a crawler and middleware classes.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this middleware manager.
- `middleware_classes` (list): A list of middleware class paths to load.

##### `process_request(self, request, spider)`
Process a request through all request middleware.

**Parameters:**
- `request` (Request): The request to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed request or None.

##### `process_response(self, request, response, spider)`
Process a response through all response middleware.

**Parameters:**
- `request` (Request): The request that generated the response.
- `response` (Response): The response to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed response.

##### `process_exception(self, request, exception, spider)`
Process an exception through all exception middleware.

**Parameters:**
- `request` (Request): The request that caused the exception.
- `exception` (Exception): The exception to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed exception or None.

## Base Middleware Classes

### Class: BaseMiddleware

The base class for all middleware implementations.

```python
class BaseMiddleware(object):
    def __init__(self, crawler):
        # Initialize the middleware
        pass
```

#### Methods

##### `__init__(self, crawler)`
Initialize the middleware with a crawler instance.

**Parameters:**
- `crawler` (Crawler): The crawler instance to associate with this middleware.

### Class: RequestMiddleware

Base class for request middleware.

```python
class RequestMiddleware(BaseMiddleware):
    async def process_request(self, request, spider):
        # Process a request
        pass
```

#### Methods

##### `process_request(self, request, spider)`
Process a request before it's sent to the downloader.

**Parameters:**
- `request` (Request): The request to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed request or None.

### Class: ResponseMiddleware

Base class for response middleware.

```python
class ResponseMiddleware(BaseMiddleware):
    async def process_response(self, request, response, spider):
        # Process a response
        pass
```

#### Methods

##### `process_response(self, request, response, spider)`
Process a response after it's received from the downloader.

**Parameters:**
- `request` (Request): The request that generated the response.
- `response` (Response): The response to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed response.

### Class: ExceptionMiddleware

Base class for exception middleware.

```python
class ExceptionMiddleware(BaseMiddleware):
    async def process_exception(self, request, exception, spider):
        # Process an exception
        pass
```

#### Methods

##### `process_exception(self, request, exception, spider)`
Process an exception that occurred during request processing.

**Parameters:**
- `request` (Request): The request that caused the exception.
- `exception` (Exception): The exception to process.
- `spider` (Spider): The spider that generated the request.

**Returns:**
- `Coroutine`: A coroutine that resolves to the processed exception or None.

## Built-in Middleware

### Class: RequestIgnoreMiddleware

Middleware for filtering requests.

```python
class RequestIgnoreMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        # Filter requests based on custom logic
        pass
```

### Class: DownloadDelayMiddleware

Middleware for adding delays between requests.

```python
class DownloadDelayMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        # Add delay before sending request
        pass
```

### Class: DefaultHeaderMiddleware

Middleware for adding default headers to requests.

```python
class DefaultHeaderMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        # Add default headers to request
        pass
```

### Class: ProxyMiddleware

Middleware for handling proxies.

```python
class ProxyMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        # Add proxy information to request
        pass
```

### Class: RetryMiddleware

Middleware for implementing retry logic.

```python
class RetryMiddleware(RequestMiddleware, ResponseMiddleware, ExceptionMiddleware):
    async def process_request(self, request, spider):
        # Process request for retry logic
        pass
    
    async def process_response(self, request, response, spider):
        # Process response for retry logic
        pass
    
    async def process_exception(self, request, exception, spider):
        # Process exception for retry logic
        pass
```

### Class: ResponseCodeMiddleware

Middleware for processing response codes.

```python
class ResponseCodeMiddleware(ResponseMiddleware):
    async def process_response(self, request, response, spider):
        # Process response based on status code
        pass
```

### Class: ResponseFilterMiddleware

Middleware for filtering responses.

```python
class ResponseFilterMiddleware(ResponseMiddleware):
    async def process_response(self, request, response, spider):
        # Filter responses based on custom logic
        pass
```

## Example Usage

```python
from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.middleware.request_ignore import RequestIgnoreMiddleware
from crawlo.middleware.download_delay import DownloadDelayMiddleware
from crawlo.middleware.default_header import DefaultHeaderMiddleware

# Configure middleware classes
middleware_classes = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# Create middleware manager
middleware_manager = MiddlewareManager(crawler, middleware_classes)

# Process a request through middleware
async def process_request_with_middleware(request, spider):
    processed_request = await middleware_manager.process_request(request, spider)
    if processed_request is None:
        # Request was filtered out
        return None
    return processed_request

# Process a response through middleware
async def process_response_with_middleware(request, response, spider):
    processed_response = await middleware_manager.process_response(request, response, spider)
    return processed_response
```