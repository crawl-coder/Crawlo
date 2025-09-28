# 内置中间件

Crawlo提供了几个内置中间件组件来处理常见的网页爬取任务。这些中间件组件可以通过配置启用或禁用。

## 概述

内置中间件为网页爬取提供基本功能：

- 请求过滤和预处理
- 响应处理和后处理
- 错误处理和重试逻辑
- 性能优化

## RequestIgnoreMiddleware

根据各种条件过滤不需要的请求。

### 特性

- URL模式匹配
- 域名过滤
- 请求方法过滤
- 自定义过滤规则

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
]

# 请求忽略设置
IGNORE_DOMAINS = ['example.com']
IGNORE_URLS = [r'/admin/.*']
IGNORE_METHODS = ['POST']
```

## DownloadDelayMiddleware

在请求之间添加延迟以尊重目标服务器。

### 特性

- 可配置的延迟时间
- 随机延迟范围
- 每域名延迟设置

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
]

# 延迟设置
DOWNLOAD_DELAY = 1.0
RANDOM_RANGE = (0.8, 1.2)
RANDOMNESS = True
```

## DefaultHeaderMiddleware

为所有请求添加默认头部，使其看起来更像浏览器请求。

### 特性

- 可自定义的默认头部
- User-Agent轮换
- 常用头部预设

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# 默认头部
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
```

## ProxyMiddleware

处理请求的代理配置。

### 特性

- 代理轮换
- 认证支持
- 代理故障检测
- 回退机制

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.proxy.ProxyMiddleware',
]

# 代理设置
PROXY_ENABLED = True
PROXY_API_URL = "http://proxy-service.com/api"
PROXY_EXTRACTOR = "proxy"
PROXY_REFRESH_INTERVAL = 60
```

## RetryMiddleware

为失败请求实现重试逻辑。

### 特性

- 可配置的重试次数
- 基于HTTP状态码的重试
- 指数退避
- 重试优先级调整

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.retry.RetryMiddleware',
]

# 重试设置
MAX_RETRY_TIMES = 3
RETRY_PRIORITY = -1
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]
```

## ResponseCodeMiddleware

处理HTTP响应码并处理特殊情况。

### 特性

- 状态码分类
- 错误响应处理
- 重定向处理
- 自定义状态码操作

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
]

# 响应码设置
IGNORE_HTTP_CODES = [403, 404]
ALLOWED_CODES = [200, 201, 202]
```

## ResponseFilterMiddleware

根据内容或其他条件过滤响应。

### 特性

- 基于内容的过滤
- 基于大小的过滤
- MIME类型过滤
- 自定义过滤函数

### 配置

```python
# 在settings.py中
MIDDLEWARES = [
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# 响应过滤设置
MIN_RESPONSE_SIZE = 1024
MAX_RESPONSE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ['text/html', 'application/json']
```

## 使用示例

要启用多个内置中间件：

```python
# 在settings.py中
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

## 性能考虑

- 适当排序中间件 - 将轻量级过滤器放在前面
- 禁用未使用的中间件以减少开销
- 配置适当的重试限制以避免过多请求
- 使用高效的过滤模式以最小化处理时间