# Custom Middleware

Middleware is a hook framework in the Crawlo framework used to process requests and responses. Through custom middleware, you can implement various functions such as request modification, response processing, error handling, etc.

## Creating Custom Middleware

To create custom middleware, you need to inherit from the `crawlo.middleware.Middleware` base class and implement the corresponding methods.

### Basic Structure

```python
from crawlo.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request, spider):
        # Process the request before it is sent
        return request
    
    def process_response(self, request, response, spider):
        # Process the response after it is returned
        return response
    
    def process_exception(self, request, exception, spider):
        # Handle exceptions that occur during the request process
        pass
```

### Method Descriptions

#### process_request(request, spider)

- **Purpose**: Process the request before it is sent
- **Parameters**:
  - `request`: Request object
  - `spider`: Spider instance
- **Return Value**:
  - Return `None` or nothing: Continue processing the request
  - Return a `Request` object: Replace the original request
  - Return a `Response` object: Abort the request and return the response directly

#### process_response(request, response, spider)

- **Purpose**: Process the response after it is returned
- **Parameters**:
  - `request`: Request object
  - `response`: Response object
  - `spider`: Spider instance
- **Return Value**:
  - Return a `Response` object: Replace the original response
  - Return a `Request` object: Retry the request
  - Return `None` or nothing: Continue processing the response

#### process_exception(request, exception, spider)

- **Purpose**: Handle exceptions that occur during the request process
- **Parameters**:
  - `request`: Request object
  - `exception`: Exception object
  - `spider`: Spider instance
- **Return Value**:
  - Return `None` or nothing: Continue processing the exception
  - Return a `Response` object: Ignore the exception and return the response
  - Return a `Request` object: Retry the request

## Examples

### User Agent Middleware

```python
from crawlo.middleware import Middleware

class UserAgentMiddleware(Middleware):
    def __init__(self, user_agent='Crawlo'):
        self.user_agent = user_agent
    
    def process_request(self, request, spider):
        request.headers['User-Agent'] = self.user_agent
        return request
```

### Proxy Middleware

```python
from crawlo.middleware import Middleware

class ProxyMiddleware(Middleware):
    def __init__(self, proxy=None):
        self.proxy = proxy
    
    def process_request(self, request, spider):
        if self.proxy:
            request.proxy = self.proxy
        return request
```

### Retry Middleware

```python
from crawlo.middleware import Middleware
from crawlo.request import Request

class RetryMiddleware(Middleware):
    def __init__(self, max_retry_times=3):
        self.max_retry_times = max_retry_times
    
    def process_response(self, request, response, spider):
        if response.status_code in [500, 502, 503, 504, 408]:
            retry_times = request.meta.get('retry_times', 0)
            if retry_times < self.max_retry_times:
                request.meta['retry_times'] = retry_times + 1
                return request
        return response
    
    def process_exception(self, request, exception, spider):
        retry_times = request.meta.get('retry_times', 0)
        if retry_times < self.max_retry_times:
            request.meta['retry_times'] = retry_times + 1
            return request
```

## Configuring Middleware

Enable custom middleware in the configuration file:

```python
# settings.py
MIDDLEWARES = {
    'myproject.middlewares.CustomMiddleware': 543,
    'myproject.middlewares.UserAgentMiddleware': 400,
    'myproject.middlewares.ProxyMiddleware': 350,
    'myproject.middlewares.RetryMiddleware': 300,
}
```

The number for middleware represents the priority, with smaller numbers having higher priority.

## Best Practices

1. **Keep middleware simple**: Each middleware should only be responsible for one function
2. **Handle return values correctly**: Ensure the correct object types are returned
3. **Exception handling**: Properly handle exceptions in middleware
4. **Performance considerations**: Avoid performing time-consuming operations in middleware
5. **Testing**: Write unit tests for middleware