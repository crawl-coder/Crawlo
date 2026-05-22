# 请求生命周期

理解请求的完整生命周期对于调试和优化爬虫至关重要。

---

## 📊 请求生命周期概览

```
创建请求 → 中间件处理 → 下载 → 响应解析 → 数据输出
    ↓          ↓          ↓         ↓          ↓
 Request   Middleware  Response   Spider    Pipeline
```

---

## 1️⃣ 请求创建阶段

### 1.1 起始请求

爬虫启动时，从 `start_urls` 创建初始请求：

```python
class MySpider(Spider):
    start_urls = ['https://example.com']
    
    # 框架内部会自动创建请求
    # Request(url='https://example.com', callback=self.parse)
```

### 1.2 手动创建请求

```python
from crawlo import Request

# 基础请求
request = Request(url='https://example.com')

# 带回调的请求
request = Request(
    url='https://example.com/page/1',
    callback=self.parse_detail,
)

# 带元数据的请求
request = Request(
    url='https://example.com/api',
    callback=self.parse_api,
    meta={
        'proxy': 'http://proxy:8080',
        'timeout': 30,
        'retry_times': 3,
    }
)
```

### 1.3 跟进请求

```python
async def parse(self, response):
    # 方式1: 使用 response.follow()
    yield response.follow('/page/2', callback=self.parse)
    
    # 方式2: 使用 Request
    yield Request(
        url=response.urljoin('/page/2'),
        callback=self.parse
    )
```

### 1.4 Depth 自动传播

框架自动为子请求传播 `depth`，无需手动设置：

```
start_requests 产生的请求  →  depth = 1（默认）
       ↓ Spider 回调产出
子请求  →  depth = 父请求.depth + 1（框架自动注入）
       ↓ Spider 回调产出
孙请求  →  depth = 父请求.depth + 1（框架自动注入）
```

- **自动传播**：Engine 在处理 Spider 回调输出时，自动将 `depth` 注入到子 Request 的 `meta` 中
- **手动覆盖**：如果用户在 `meta` 中手动设置了 `depth`，框架不会覆盖
- **Errback 支持**：errback 产生的请求同样自动传播 `depth`

```python
async def parse(self, response):
    # 无需手动设置 depth，框架自动传播
    # response.meta['depth'] = 1（来自 start_requests）
    
    yield Request(url="http://example.com/detail")
    # 此请求的 depth 自动设为 2
    
    # 如果需要手动指定 depth（框架不会覆盖）
    yield Request(url="http://example.com/custom", meta={'depth': 10})
    # 此请求的 depth 保持为 10
```

> **⚠️ 重要**：`depth` 传播由 Engine 层（`_handle_spider_output`）统一管理。中间件或工具函数**不应提前注入** `depth` 到 `request.meta`，否则会导致 Engine 的 depth 传播逻辑被跳过，造成子请求 depth 值错误，进而使 `DEPTH_PRIORITY` 调度策略失效。

配合 `DEPTH_PRIORITY` 配置，depth 会影响请求的出队优先级：

| `DEPTH_PRIORITY` | 策略 | 效果 |
|------------------|------|------|
| `1`（默认） | 深度优先 | depth 越大越先出队（详情页优先） |
| `-1` | 广度优先 | depth 越小越先出队（列表页优先） |
| `0` | 不调整 | depth 不影响出队顺序 |

---

## 2️⃣ 中间件处理阶段

### 2.1 请求中间件（Downloader Middleware）

请求在下载前会经过中间件链：

```
Request
    ↓
[Middleware 1] → process_request()
    ↓
[Middleware 2] → process_request()
    ↓
[Middleware 3] → process_request()
    ↓
Downloader
```

**常见中间件**：

1. **ProxyMiddleware** - 代理处理
```python
def process_request(self, request, spider):
    # 为请求添加代理
    request.meta['proxy'] = 'http://proxy:8080'
```

2. **UserAgentMiddleware** - User-Agent 设置
```python
def process_request(self, request, spider):
    # 设置 User-Agent
    request.headers['User-Agent'] = 'Mozilla/5.0...'
```

3. **RetryMiddleware** - 重试处理
```python
def process_request(self, request, spider):
    # 检查是否需要重试
    if request.meta.get('retry_times', 0) > 0:
        spider.logger.info(f"重试: {request.url}")
```

### 2.2 中间件优先级

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'crawlo.middleware.ProxyMiddleware': 100,      # 先执行
    'crawlo.middleware.UserAgentMiddleware': 200,
    'crawlo.middleware.RetryMiddleware': 300,      # 后执行
}
```

**数字越小，优先级越高**。

---

## 3️⃣ 下载阶段

### 3.1 选择下载器

根据请求特性，框架自动选择下载器：

```python
# 方式1: 自动选择（默认）
# 根据 URL 模式配置
DYNAMIC_LOADER_URL_PATTERNS = [
    r'.*\.example\.com/.*',  # 使用浏览器
]

# 方式2: 请求中指定
yield Request(
    url='https://example.com',
    meta={'use_dynamic_loader': True}  # 使用浏览器
)
```

### 3.2 下载器类型

| 下载器 | 适用场景 | 速度 | 通过率 |
|--------|---------|------|--------|
| **AioHttpDownloader** | 静态页面 | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ |
| **HttpXDownloader** | API 请求 | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ |
| **PlaywrightDownloader** | 动态页面 | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| **CurlCffiDownloader** | 反爬网站 | ⚡⚡⚡ | ⭐⭐⭐⭐ |

### 3.3 下载过程

```python
# 伪代码
async def download(request):
    # 1. 应用超时
    timeout = request.meta.get('timeout', 30)
    
    # 2. 应用代理
    proxy = request.meta.get('proxy')
    
    # 3. 发送请求
    response = await downloader.fetch(
        url=request.url,
        method=request.method,
        headers=request.headers,
        body=request.body,
        timeout=timeout,
        proxy=proxy,
    )
    
    # 4. 返回响应
    return response
```

---

## 4️⃣ 响应解析阶段

### 4.1 响应对象

下载完成后，创建 Response 对象：

```python
class Response:
    url: str              # 响应 URL
    status: int           # HTTP 状态码
    headers: dict         # 响应头
    body: bytes           # 响应体（原始字节）
    text: str             # 响应体（文本）
    metadata: dict        # 元数据
```

### 4.2 中间件处理（响应）

响应返回给 Spider 前，也会经过中间件：

```
Response
    ↓
[Middleware 3] → process_response()
    ↓
[Middleware 2] → process_response()
    ↓
[Middleware 1] → process_response()
    ↓
Spider.parse()
```

**处理逻辑**：

```python
def process_response(self, request, response, spider):
    # 检查状态码
    if response.status == 403:
        # 触发 Cloudflare 绕过
        request.meta['use_dynamic_loader'] = True
        return request  # 返回 Request 会重新下载
    
    # 正常响应
    return response
```

### 4.3 Spider 解析

Spider 的 `parse()` 方法处理响应：

```python
async def parse(self, response):
    # 1. 提取数据
    items = []
    for item in response.css('div.item'):
        data = {
            'title': item.css('h2::text').get(),
            'link': item.css('a::attr(href)').get(),
        }
        items.append(data)
    
    # 2. 返回数据（交给 Pipeline）
    for item in items:
        yield item
    
    # 3. 提取下一页链接（生成新请求）
    next_page = response.css('a.next::attr(href)').get()
    if next_page:
        yield response.follow(next_page, callback=self.parse)
```

---

## 5️⃣ 数据输出阶段

### 5.1 Pipeline 处理

Item 数据会经过 Pipeline 链：

```
Spider yield Item
    ↓
[Pipeline 1] → process_item()
    ↓
[Pipeline 2] → process_item()
    ↓
[Pipeline 3] → process_item()
    ↓
输出（文件/数据库）
```

**Pipeline 示例**：

```python
# 1. 数据验证 Pipeline
class ValidationPipeline:
    def process_item(self, item, spider):
        if not item.get('title'):
            raise DropItem(f"缺少 title: {item}")
        return item

# 2. 去重 Pipeline
class DeduplicationPipeline:
    def __init__(self):
        self.seen = set()
    
    def process_item(self, item, spider):
        item_id = item.get('url')
        if item_id in self.seen:
            raise DropItem(f"重复 item: {item_id}")
        self.seen.add(item_id)
        return item

# 3. 存储 Pipeline
class MySQLPipeline:
    async def process_item(self, item, spider):
        await db.insert('items', dict(item))
        return item
```

### 5.2 Pipeline 优先级

```python
# settings.py
PIPELINES = {
    'myproject.pipelines.ValidationPipeline': 100,     # 先验证
    'myproject.pipelines.DeduplicationPipeline': 200,  # 再去重
    'myproject.pipelines.MySQLPipeline': 300,          # 最后存储
}
```

### 5.3 输出方式

**Pipeline 输出**
```python
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
```

**方式3: 同时输出**
```bash
# 文件 + Pipeline
crawlo run myspider -o output.json
```

---

## 🔍 请求生命周期调试

### 1. 查看请求详情

```python
async def parse(self, response):
    # 打印请求信息
    self.logger.info(f"URL: {response.url}")
    self.logger.info(f"Status: {response.status}")
    self.logger.info(f"Headers: {response.headers}")
```

### 2. 跟踪请求链路

```python
# settings.py
LOG_LEVEL = 'DEBUG'  # 查看详细日志
```

日志输出：
```
DEBUG: Crawled (200) <GET https://example.com>
DEBUG: Scraped data: {'title': '...', 'url': '...'}
DEBUG: Scheduled new request: <GET https://example.com/page/2>
```

### 3. 使用事件系统

```python
# 监听请求完成事件
from crawlo.event import CrawlerEvent

async def spider_opened(self):
    # 注册事件订阅者
    async def on_response_received(response, spider):
        self.logger.info(f"收到响应: {response.url}")
    
    self.crawler.subscriber.subscribe(
        CrawlerEvent.RESPONSE_RECEIVED,
        on_response_received
    )
```

**注意**：Crawlo 使用事件系统（`CrawlerEvent` + `subscriber`），而不是 Scrapy 的 signals。

---

## ⚠️ 常见问题

### Q1: 请求没有发起？

**原因**：
- `start_urls` 为空
- `parse()` 没有 yield 新请求

**解决方案**：
```python
# 检查 start_urls
start_urls = ['https://example.com']  # 确保不为空

# 检查 yield
yield Request(url, callback=self.parse)  # 确保有 yield
```

### Q2: 请求被过滤了？

**原因**：
- URL 已爬取过（去重）
- OffsiteMiddleware 拦截（域名不在允许列表）

**解决方案**：
```python
# 禁用去重（调试用）
DUPEFILTER_CLASS = 'crawlo.dupefilters.BaseDupeFilter'

# 添加允许域名
allowed_domains = ['example.com', 'api.example.com']
```

### Q3: 响应状态码 403？

**原因**：
- 被反爬机制拦截
- 缺少 User-Agent
- IP 被封禁

**解决方案**：
```python
# 使用浏览器渲染
yield Request(url, meta={'use_dynamic_loader': True})

# 使用代理
yield Request(url, meta={'proxy': 'http://proxy:8080'})
```

---

## 📚 相关文档

- [爬虫生命周期](spider-lifecycle.md)
- [中间件链](middleware-chain.md)
- [错误处理机制](error-handling.md)
- [配置指南](../guides/configuration/)

---

**需要更多帮助？** 查看 [常见问题](../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
