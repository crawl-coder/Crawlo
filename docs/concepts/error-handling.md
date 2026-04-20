# 错误处理机制

完善的错误处理是爬虫稳定运行的关键。

---

## 📊 错误分类

Crawlo 中的错误主要分为三类：

```
错误类型
├── 网络错误（Network Errors）
│   ├── 连接超时
│   ├── DNS 解析失败
│   ├── 连接被拒绝
│   └── SSL 证书错误
│
├── HTTP 错误（HTTP Errors）
│   ├── 4xx 客户端错误
│   │   ├── 400 Bad Request
│   │   ├── 403 Forbidden
│   │   ├── 404 Not Found
│   │   └── 429 Too Many Requests
│   └── 5xx 服务器错误
│       ├── 500 Internal Server Error
│       ├── 502 Bad Gateway
│       ├── 503 Service Unavailable
│       └── 504 Gateway Timeout
│
└── 解析错误（Parse Errors）
    ├── 选择器未匹配
    ├── 数据格式错误
    └── 编码问题
```

---

## 1️⃣ 重试机制

### 1.1 配置重试

```python
# settings.py
RETRY_ENABLED = True
RETRY_TIMES = 3  # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503, 504, 408]  # 触发重试的状态码
```

### 1.2 重试中间件

```python
# 内置 RetryMiddleware 工作流程
def process_response(self, request, response, spider):
    # 检查状态码
    if response.status in RETRY_HTTP_CODES:
        retry_times = request.meta.get('retry_times', 0)
        
        if retry_times < RETRY_TIMES:
            # 创建重试请求
            retry_request = request.copy()
            retry_request.meta['retry_times'] = retry_times + 1
            
            # 指数退避
            delay = 2 ** retry_times
            retry_request.meta['download_delay'] = delay
            
            spider.logger.info(
                f"重试 {retry_request.url} "
                f"(第 {retry_times + 1}/{RETRY_TIMES} 次)"
            )
            
            return retry_request
    
    return response
```

### 1.3 自定义重试逻辑

```python
class CustomRetryMiddleware:
    async def process_response(self, request, response, spider):
        # 自定义重试条件
        if response.status == 403:
            # 403 错误，切换代理后重试
            request.meta['change_proxy'] = True
            return request
        
        if '验证码' in response.text:
            # 检测到验证码，使用浏览器渲染
            request.meta['use_dynamic_loader'] = True
            return request
        
        return response
```

---

## 2️⃣ 异常处理

### 2.1 下载异常

```python
class MySpider(Spider):
    async def parse(self, response):
        try:
            # 正常解析
            data = response.css('div.data::text').get()
            yield {'data': data}
            
        except Exception as e:
            # 捕获异常
            self.logger.error(f"解析失败: {e}")
            
            # 记录错误 URL
            self.logger.error(f"错误 URL: {response.url}")
            
            # 可以选择不 yield 任何数据
            # 或者 yield 一个错误标记
            yield {
                'error': str(e),
                'url': response.url,
            }
```

### 2.2 中间件异常

```python
class MyMiddleware:
    def process_exception(self, request, exception, spider):
        """处理下载异常"""
        
        spider.logger.error(f"下载异常: {exception}")
        spider.logger.error(f"请求 URL: {request.url}")
        
        # 选择处理方式：
        
        # 1. 返回 Request - 重试
        if 'timeout' in str(exception).lower():
            return request.copy()
        
        # 2. 返回 None - 传递给下一个中间件
        return None
        
        # 3. 返回 Response - 模拟响应
        # return Response(url=request.url, status=500)
```

---

## 3️⃣ 降级策略

### 3.1 下载器降级

```python
class MySpider(Spider):
    async def parse(self, response):
        # 如果静态请求失败，降级到浏览器渲染
        if response.status == 403:
            yield Request(
                url=response.url,
                callback=self.parse,
                meta={'use_dynamic_loader': True}  # 使用浏览器
            )
            return
```

### 3.2 数据提取降级

```python
async def parse(self, response):
    # 方式1: CSS 选择器
    title = response.css('h1.title::text').get()
    
    # 方式1 失败，使用 XPath
    if not title:
        title = response.xpath('//h1[@class="title"]/text()').get()
    
    # 方式2 失败，使用正则
    if not title:
        import re
        match = re.search(r'<h1 class="title">(.*?)</h1>', response.text)
        if match:
            title = match.group(1)
    
    yield {'title': title or '未找到标题'}
```

---

## 4️⃣ 错误监控

### 4.1 统计错误

```python
# settings.py
STATS_ENABLED = True
STATS_INTERVAL = 60  # 每 60 秒打印统计
```

日志输出：
```
INFO: 统计信息:
  - 总请求数: 1234
  - 成功数: 1200
  - 失败数: 34
  - 错误率: 2.76%
  - 重试次数: 50
```

### 4.2 错误告警

```python
# settings.py
NOTIFICATION_ENABLED = True
NOTIFICATION_ON_ERROR = True
NOTIFICATION_ERROR_THRESHOLD = 0.1  # 错误率超过 10% 告警
NOTIFICATION_CHANNELS = ['feishu', 'email']
```

### 4.3 自定义错误处理

```python
class ErrorTrackingMiddleware:
    def __init__(self):
        self.errors = []
    
    def process_exception(self, request, exception, spider):
        # 记录错误
        self.errors.append({
            'url': request.url,
            'error': str(exception),
            'timestamp': datetime.now().isoformat(),
        })
        
        # 错误数过多时告警
        if len(self.errors) > 100:
            spider.logger.warning(f"错误数过多: {len(self.errors)}")
            # 发送告警
            # await send_alert(self.errors)
        
        return None
```

---

## 💡 最佳实践

### 1. 区分可重试和不可重试错误

```python
RETRYABLE_ERRORS = [
    'timeout',
    'connection reset',
    '502',
    '503',
    '504',
]

NON_RETRYABLE_ERRORS = [
    '404',
    '400',
    'SSL Error',  # SSL 错误通常不可重试
]
```

### 2. 使用指数退避

```python
# 重试延迟逐渐增加
retry_delay = min(2 ** retry_times, 60)  # 最大 60 秒
```

### 3. 记录详细错误信息

```python
self.logger.error(
    f"请求失败:\n"
    f"  URL: {request.url}\n"
    f"  状态码: {response.status}\n"
    f"  错误: {exception}\n"
    f"  重试次数: {request.meta.get('retry_times', 0)}"
)
```

### 4. 优雅降级

```python
async def parse(self, response):
    try:
        # 尝试完整解析
        data = self.extract_full_data(response)
    except Exception as e:
        self.logger.warning(f"完整解析失败，使用简化解析: {e}")
        try:
            # 降级到简化解析
            data = self.extract_simple_data(response)
        except Exception as e2:
            self.logger.error(f"简化解析也失败: {e2}")
            data = {'error': '解析失败'}
    
    yield data
```

---

## ⚠️ 常见错误和解决方案

### 错误 1: 连接超时

**现象**：
```
TimeoutError: Connection timed out
```

**解决方案**：
```python
# 增加超时时间
DOWNLOAD_TIMEOUT = 60

# 使用代理
PROXY_ENABLED = True

# 降低并发
CONCURRENCY = 4
```

### 错误 2: 403 Forbidden

**现象**：
```
HTTP 403 Forbidden
```

**解决方案**：
```python
# 使用浏览器渲染
yield Request(url, meta={'use_dynamic_loader': True})

# 使用代理
yield Request(url, meta={'proxy': 'http://proxy:8080'})

# 启用 Cloudflare 绕过
CLOUDFLARE_BYPASS_ENABLED = True
```

### 错误 3: 选择器未匹配

**现象**：
```
WARNING: 未找到数据
```

**解决方案**：
```python
# 使用自适应选择器
title = response.css('h1.title::text', adaptive=True).get()

# 打印 HTML 调试
self.logger.debug(response.text[:1000])
```

### 错误 4: 内存溢出

**现象**：
```
MemoryError
```

**解决方案**：
```python
# 限制队列大小
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000

# 启用背压
BACKPRESSURE_ENABLED = True

# 分批处理
BATCH_SIZE = 1000
```

---

## 📚 相关文档

- [请求生命周期](request-lifecycle.md)
- [爬虫生命周期](spider-lifecycle.md)
- [中间件链](middleware-chain.md)
- [背压系统](../guides/scheduling/backpressure.md)

---

**需要更多帮助？** 查看 [故障排查](../faq/troubleshooting.md) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
