# 中间件

中间件是 Crawlo 框架中用于处理请求和响应的组件。它们在请求发送之前和响应接收之后执行，可以用于修改请求、处理响应或处理异常。

## 中间件管理器

[MiddlewareManager](file:///d%3A/dowell/projects/Crawlo/crawlo/middleware/middleware_manager.py#L18-L134) 负责管理所有中间件组件，并协调它们的执行。

### 类: MiddlewareManager

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

#### 参数

- `crawler` (Crawler): 与中间件管理器关联的爬虫实例
- `middleware_classes` (list): 要加载的中间件类路径列表

#### 方法

##### `__init__(self, crawler, middleware_classes)`

使用爬虫和中间件类初始化中间件管理器。

**参数:**
- `crawler` (Crawler): 与中间件管理器关联的爬虫实例
- `middleware_classes` (list): 要加载的中间件类路径列表

##### `process_request(self, request, spider)`

通过所有请求中间件处理请求。

**参数:**
- `request` (Request): 要处理的请求
- `spider` (Spider): 生成请求的爬虫

**返回:**
- `Coroutine`: 解析为处理后的请求或 None 的协程

##### `process_response(self, request, response, spider)`

通过所有响应中间件处理响应。

**参数:**
- `request` (Request): 生成响应的请求
- `response` (Response): 要处理的响应
- `spider` (Spider): 生成请求的爬虫

**返回:**
- `Coroutine`: 解析为处理后的响应的协程

##### `process_exception(self, request, exception, spider)`

通过所有异常中间件处理异常。

**参数:**
- `request` (Request): 导致异常的请求
- `exception` (Exception): 要处理的异常
- `spider` (Spider): 生成请求的爬虫

**返回:**
- `Coroutine`: 解析为处理后的异常或 None 的协程

## 基础中间件类

所有中间件都应该继承 [BaseMiddleware](file:///d%3A/dowell/projects/Crawlo/crawlo/middleware/__init__.py#L6-L20) 类。

### 类: BaseMiddleware

```python
class BaseMiddleware(object):
    def process_request(self, request, spider) -> None | Request | Response:
        # 请求预处理
        pass

    def process_response(self, request, response, spider) -> Request | Response:
        # 响应预处理
        pass

    def process_exception(self, request, exp, spider) -> None | Request | Response:
        # 异常预处理
        pass

    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

#### 方法

##### `process_request(self, request, spider)`

在请求发送之前处理请求。

**参数:**
- `request` (Request): 要处理的请求
- `spider` (Spider): 当前爬虫实例

**返回:**
- `None`: 继续处理下一个中间件
- `Request`: 返回新的请求对象
- `Response`: 返回响应对象（短路处理）

##### `process_response(self, request, response, spider)`

在响应接收之后处理响应。

**参数:**
- `request` (Request): 生成响应的请求
- `response` (Response): 要处理的响应
- `spider` (Spider): 当前爬虫实例

**返回:**
- `Request`: 返回新的请求对象（重新发送请求）
- `Response`: 返回处理后的响应对象

##### `process_exception(self, request, exp, spider)`

处理请求过程中发生的异常。

**参数:**
- `request` (Request): 导致异常的请求
- `exp` (Exception): 异常对象
- `spider` (Spider): 当前爬虫实例

**返回:**
- `None`: 继续处理下一个中间件
- `Request`: 返回新的请求对象
- `Response`: 返回响应对象

##### `create_instance(cls, crawler)`

创建中间件实例的类方法。

**参数:**
- `crawler` (Crawler): 爬虫实例

**返回:**
- 中间件实例

## 内置中间件

Crawlo 提供了多种内置中间件：

### 请求忽略中间件 (RequestIgnoreMiddleware)

用于过滤不需要的请求。

### 下载延迟中间件 (DownloadDelayMiddleware)

控制请求之间的下载延迟。

### 默认头部中间件 (DefaultHeaderMiddleware)

为请求添加默认头部信息。

### 代理中间件 (ProxyMiddleware)

处理请求的代理设置。

### 重试中间件 (RetryMiddleware)

处理请求失败时的重试逻辑。

### 响应码中间件 (ResponseCodeMiddleware)

处理特定响应码的逻辑。

### 响应过滤中间件 (ResponseFilterMiddleware)

过滤不需要的响应。

## 创建自定义中间件

要创建自定义中间件，需要继承 [BaseMiddleware](file:///d%3A/dowell/projects/Crawlo/crawlo/middleware/__init__.py#L6-L20) 类并实现相应的方法。

### 示例：用户代理中间件

```python
from crawlo.middleware import BaseMiddleware
from crawlo import Request

class UserAgentMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
    
    def process_request(self, request: Request, spider):
        # 为每个请求随机选择一个 User-Agent
        import random
        user_agent = random.choice(self.user_agents)
        request.headers['User-Agent'] = user_agent
        return None
    
    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

### 示例：响应处理中间件

```python
from crawlo.middleware import BaseMiddleware
from crawlo import Request, Response

class ResponseProcessingMiddleware(BaseMiddleware):
    def process_response(self, request: Request, response: Response, spider):
        # 记录响应状态码
        spider.logger.info(f"Received response with status {response.status_code} for {request.url}")
        
        # 检查是否需要重定向
        if response.status_code in [301, 302]:
            redirect_url = response.headers.get('Location')
            if redirect_url:
                spider.logger.info(f"Redirecting to {redirect_url}")
                return Request(url=redirect_url, callback=request.callback)
        
        return response
    
    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

### 示例：异常处理中间件

```python
from crawlo.middleware import BaseMiddleware
from crawlo import Request
import asyncio

class ExceptionHandlingMiddleware(BaseMiddleware):
    async def process_exception(self, request: Request, exp: Exception, spider):
        # 记录异常信息
        spider.logger.error(f"Exception occurred for {request.url}: {exp}")
        
        # 对于超时异常，可以重试
        if "timeout" in str(exp).lower():
            spider.logger.info("Retrying due to timeout")
            # 等待一段时间后重试
            await asyncio.sleep(1)
            return request  # 返回原始请求以重新发送
        
        # 对于其他异常，可以选择忽略或返回默认响应
        return None  # 继续处理下一个异常处理器
    
    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

## 配置中间件

在 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中配置中间件：

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
    # 添加自定义中间件
    'myproject.middlewares.UserAgentMiddleware',
    'myproject.middlewares.ResponseProcessingMiddleware',
]
```

## 最佳实践

1. **明确中间件职责**：每个中间件应该有明确的单一职责
2. **正确处理返回值**：理解不同返回值的含义和影响
3. **异常处理**：在中间件中妥善处理异常
4. **性能考虑**：避免在中间件中执行耗时操作
5. **日志记录**：适当记录中间件的操作日志
6. **配置管理**：通过设置文件配置中间件行为
7. **测试**：为中间件编写单元测试