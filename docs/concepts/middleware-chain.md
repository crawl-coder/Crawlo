# 中间件链

中间件是 Crawlo 框架的核心扩展机制，用于处理请求和响应。

---

## 📊 中间件架构

```
Request → [Middleware 1] → [Middleware 2] → [Middleware 3] → Downloader
              ↓               ↓               ↓
         process_request   process_request   process_request

Response ← [Middleware 1] ← [Middleware 2] ← [Middleware 3] ← Downloader
              ↓               ↓               ↓
         process_response  process_response  process_response
```

---

## 📝 中间件类型

### 1. 下载器中间件（Downloader Middleware）

处理请求和响应的中间件：

```python
class MyMiddleware:
    def process_request(self, request, spider):
        """处理请求（下载前）"""
        # 可以修改请求
        request.headers['User-Agent'] = 'Mozilla/5.0'
        
        # 可以返回三种类型：
        # 1. None - 继续处理下一个中间件
        # 2. Response - 跳过下载，直接返回响应
        # 3. Request - 重新调度请求
        
        return None
    
    def process_response(self, request, response, spider):
        """处理响应（下载后）"""
        # 可以修改响应
        if response.status == 403:
            # 返回 Request 会重新下载
            request.meta['use_proxy'] = True
            return request
        
        # 正常响应
        return response
    
    def process_exception(self, request, exception, spider):
        """处理下载异常"""
        # 返回 Request 会重试
        # 返回 None 会传递给下一个中间件
        return None
```

### 2. Spider 中间件（Spider Middleware）

处理 Spider 输入输出的中间件：

```python
class MySpiderMiddleware:
    def process_spider_input(self, response, spider):
        """响应进入 Spider 前"""
        return None
    
    def process_spider_output(self, response, result, spider):
        """Spider 输出后"""
        for item in result:
            yield item
    
    def process_spider_exception(self, response, exception, spider):
        """Spider 异常"""
        return None
```

---

## ⚙️ 内置中间件

### 常用下载器中间件

| 中间件 | 优先级 | 功能 |
|--------|--------|------|
| **ProxyMiddleware** | 100 | 代理管理 |
| **UserAgentMiddleware** | 200 | User-Agent 设置 |
| **RetryMiddleware** | 300 | 重试处理 |
| **CloudflareMiddleware** | 400 | Cloudflare 绕过 |
| **ThrottleMiddleware** | 500 | 智能限速 |

### 配置中间件

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'crawlo.middleware.ProxyMiddleware': 100,
    'crawlo.middleware.UserAgentMiddleware': 200,
    'crawlo.middleware.RetryMiddleware': 300,
    'crawlo.middleware.CloudflareMiddleware': 400,
    'crawlo.middleware.ThrottleMiddleware': 500,
}
```

**优先级规则**：
- 数字越小，优先级越高
- `process_request` 按优先级**升序**执行
- `process_response` 按优先级**降序**执行

---

## 🔧 自定义中间件

### 示例 1: 请求日志中间件

```python
import logging

class RequestLogMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
    
    def process_request(self, request, spider):
        self.request_count += 1
        self.logger.info(
            f"[{self.request_count}] 请求: {request.url}"
        )
        return None
    
    def process_response(self, request, response, spider):
        self.logger.info(
            f"响应: {response.status} - {response.url}"
        )
        return response
```

### 示例 2: 随机延迟中间件

```python
import asyncio
import random

class RandomDelayMiddleware:
    def __init__(self, min_delay=0.5, max_delay=2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    async def process_request(self, request, spider):
        # 随机延迟
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        return None
```

### 示例 3: 请求过滤中间件

```python
class URLFilterMiddleware:
    def __init__(self):
        self.blocked_domains = ['ads.example.com', 'tracker.example.com']
    
    def process_request(self, request, spider):
        # 过滤广告域名
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc
        
        if domain in self.blocked_domains:
            spider.logger.info(f"拦截广告: {request.url}")
            return None  # 丢弃请求
        
        return None
```

---

## 🎯 中间件执行顺序

### 请求处理流程

```python
# 伪代码
async def download_with_middleware(request):
    # 1. 按优先级升序处理请求
    for mw in sorted(middlewares, key=lambda x: x.priority):
        result = await mw.process_request(request, spider)
        
        if result is not None:
            # 返回 Response：跳过下载
            if isinstance(result, Response):
                return result
            
            # 返回 Request：重新调度
            if isinstance(result, Request):
                await schedule(result)
                return None
    
    # 2. 下载请求
    response = await downloader.fetch(request)
    
    # 3. 按优先级降序处理响应
    for mw in sorted(middlewares, key=lambda x: x.priority, reverse=True):
        response = await mw.process_response(request, response, spider)
        
        # 如果返回 Request，重新下载
        if isinstance(response, Request):
            return await download_with_middleware(response)
    
    return response
```

### 实际示例

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'ProxyMiddleware': 100,        # 1. 先设置代理
    'UserAgentMiddleware': 200,    # 2. 再设置 UA
    'RetryMiddleware': 300,        # 3. 最后检查重试
}
```

**执行顺序**：

```
Request
    ↓
ProxyMiddleware.process_request()      # 添加代理
    ↓
UserAgentMiddleware.process_request()  # 添加 UA
    ↓
RetryMiddleware.process_request()      # 检查重试次数
    ↓
Downloader                           # 下载
    ↓
RetryMiddleware.process_response()     # 检查状态码
    ↓
UserAgentMiddleware.process_response() # （通常不处理）
    ↓
ProxyMiddleware.process_response()     # （通常不处理）
    ↓
Spider.parse()
```

---

## 💡 最佳实践

### 1. 中间件职责单一

```python
# ❌ 不好：一个中间件做太多事
class BadMiddleware:
    def process_request(self, request, spider):
        # 设置代理
        # 设置 UA
        # 检查重试
        # 记录日志
        # ... 太多职责
        pass

# ✅ 好：每个中间件一个职责
class ProxyMiddleware:
    def process_request(self, request, spider):
        # 只处理代理
        pass

class UserAgentMiddleware:
    def process_request(self, request, spider):
        # 只处理 UA
        pass
```

### 2. 异步中间件

```python
# 如果需要 IO 操作，使用异步
class DatabaseMiddleware:
    async def process_request(self, request, spider):
        # 查询数据库
        result = await db.query('SELECT ...')
        request.meta['data'] = result
        return None
```

### 3. 错误处理

```python
class SafeMiddleware:
    def process_request(self, request, spider):
        try:
            # 正常逻辑
            pass
        except Exception as e:
            spider.logger.error(f"中间件错误: {e}")
            return None  # 出错时继续执行
```

---

## ⚠️ 常见问题

### Q1: 中间件不生效？

**原因**：
- 未在 settings.py 中启用
- 优先级设置错误

**解决方案**：

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'myproject.middleware.MyMiddleware': 100,  # 确保启用
}
```

### Q2: 如何跳过某个中间件？

**方式1**: 在请求中设置

```python
yield Request(
    url='https://example.com',
    meta={'dont_proxy': True}  # 跳过代理中间件
)
```

**方式2**: 在中间件中检查

```python
def process_request(self, request, spider):
    if request.meta.get('skip_middleware'):
        return None  # 跳过
```

### Q3: 中间件顺序混乱？

**解决**：检查优先级数字

```python
# 优先级数字越小越先执行
DOWNLOADER_MIDDLEWARES = {
    'MiddlewareA': 100,  # 先执行
    'MiddlewareB': 200,  # 后执行
}
```

---

## 📚 相关文档

- [请求生命周期](request-lifecycle.md)
- [爬虫生命周期](spider-lifecycle.md)
- [错误处理机制](error-handling.md)
- [使用指南](../guides/)

---

**需要更多帮助？** 查看 [常见问题](../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
