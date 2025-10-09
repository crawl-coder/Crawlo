# 自定义中间件

中间件是 Crawlo 框架中用于处理请求和响应的钩子框架。通过自定义中间件，您可以实现各种功能，如请求修改、响应处理、错误处理等。

## 创建自定义中间件

要创建自定义中间件，需要继承 `crawlo.middleware.Middleware` 基类并实现相应的方法。

### 基本结构

```python
from crawlo.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request, spider):
        # 在请求发送之前处理请求
        return request
    
    def process_response(self, request, response, spider):
        # 在响应返回之后处理响应
        return response
    
    def process_exception(self, request, exception, spider):
        # 处理请求过程中发生的异常
        pass
```

### 方法说明

#### process_request(request, spider)

- **作用**: 在请求发送之前处理请求
- **参数**:
  - `request`: 请求对象
  - `spider`: 爬虫实例
- **返回值**:
  - 返回 `None` 或不返回：继续处理请求
  - 返回 `Request` 对象：替换原始请求
  - 返回 `Response` 对象：中止请求，直接返回响应

#### process_response(request, response, spider)

- **作用**: 在响应返回之后处理响应
- **参数**:
  - `request`: 请求对象
  - `response`: 响应对象
  - `spider`: 爬虫实例
- **返回值**:
  - 返回 `Response` 对象：替换原始响应
  - 返回 `Request` 对象：重试请求
  - 返回 `None` 或不返回：继续处理响应

#### process_exception(request, exception, spider)

- **作用**: 处理请求过程中发生的异常
- **参数**:
  - `request`: 请求对象
  - `exception`: 异常对象
  - `spider`: 爬虫实例
- **返回值**:
  - 返回 `None` 或不返回：继续处理异常
  - 返回 `Response` 对象：忽略异常，返回响应
  - 返回 `Request` 对象：重试请求

## 示例

### 请求头中间件

```python
from crawlo.middleware import Middleware

class UserAgentMiddleware(Middleware):
    def __init__(self, user_agent='Crawlo'):
        self.user_agent = user_agent
    
    def process_request(self, request, spider):
        request.headers['User-Agent'] = self.user_agent
        return request
```

### 代理中间件

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

### 重试中间件

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

## 配置中间件

在配置文件中启用自定义中间件：

```python
# settings.py
MIDDLEWARES = {
    'myproject.middlewares.CustomMiddleware': 543,
    'myproject.middlewares.UserAgentMiddleware': 400,
    'myproject.middlewares.ProxyMiddleware': 350,
    'myproject.middlewares.RetryMiddleware': 300,
}
```

中间件的数字表示优先级，数字越小优先级越高。

## 最佳实践

1. **保持中间件简单**：每个中间件应该只负责一个功能
2. **正确处理返回值**：确保返回正确的对象类型
3. **异常处理**：在中间件中妥善处理异常
4. **性能考虑**：避免在中间件中执行耗时操作
5. **测试**：为中间件编写单元测试