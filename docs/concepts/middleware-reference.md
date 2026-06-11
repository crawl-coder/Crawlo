# 中间件参考 (Middleware Reference)

> Crawlo 内置 13 个中间件，覆盖重试、代理、Header、限速、跨域、反爬等场景。

## 中间件链模型

Crawlo 使用洋葱模型：请求从外向内经过 `process_request`，响应从内向外经过 `process_response`。

```
Request → Retry → Proxy → Header → DynamicRender → Downloader
Response ← Retry ← Proxy ← Header ← DynamicRender ← Downloader
```

优先级数值越小，越靠外层（越先处理请求、越后处理响应）。

## 内置中间件

### 1. RetryMiddleware — 自动重试

遇到网络错误或指定 HTTP 状态码时自动重试，支持指数退避和代理切换。

```python
# settings.py
MAX_RETRY_TIMES = 3                   # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503]    # 触发热重试的状态码
IGNORE_HTTP_CODES = [404]             # 跳过不重试的状态码
RETRY_PRIORITY = 10                   # 重试请求的优先级增量
RETRY_EXCEPTIONS = []                 # 自定义异常类型
```

重试退避：第 1 次等 1s，第 2 次等 2s，第 3 次等 4s（`2^(n-1)`）。

开启代理时：网络错误 → 切换代理重试；HTTP 错误 → 继续使用当前代理。

### 2. ProxyMiddleware — 代理处理

自动为请求分配代理，支持静态列表和动态 API。

```python
PROXY_ENABLED = True
PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]
PROXY_API_URL = "http://proxy-api.com/get-proxy"
```

详见 [代理配置指南](../guides/proxy-guide.md)。

### 3. UserAgentMiddleware — 随机 User-Agent

为每个请求随机分配 User-Agent，模拟不同浏览器。

```python
USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
]
```

### 4. DefaultHeaderMiddleware — 默认请求头

为所有请求自动添加默认 Header：

```python
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
```

### 5. DownloadDelayMiddleware — 下载延迟

控制请求之间的最小间隔：

```python
DOWNLOAD_DELAY = 1.0                  # 请求间隔（秒）
RANDOMNESS = True                     # 是否加随机抖动（±50%）
```

### 6. DynamicRenderMiddleware — 动态渲染

检测页面是否需要浏览器渲染（SPA、动态加载内容），自动触发 HybridDownloader 切换。

```python
DYNAMIC_RENDER_ENABLED = True
DYNAMIC_RENDER_DOMAIN_PATTERNS = ['spa.example.com']
DYNAMIC_RENDER_URL_PATTERNS = [r'/app/', r'/#/']
```

### 7. CloudflareBypassMiddleware — Cloudflare 绕过

检测 Cloudflare 挑战页面，自动切换到隐身浏览器绕过。

```python
CLOUDFLARE_BYPASS_ENABLED = True
CLOUDFLARE_BYPASS_MAX_RETRIES = 2
CLOUDFLARE_BYPASS_DOWNLOADER = 'cloakbrowser'   # 或 camoufox / playwright
```

详见 [Cloudflare 绕过指南](../guides/cloudflare-bypass.md)。

### 8. OffsiteMiddleware — 跨域过滤

自动过滤 `allowed_domains` 之外的请求：

```python
# spider.py
allowed_domains = ['example.com']

# 自动生效，无需额外配置
```

### 9. PriorityMiddleware — 请求优先级

按配置调整请求优先级：

```python
DEPTH_PRIORITY = 1                    # 深度越深优先级越高（列表页优先）
# 或
DEPTH_PRIORITY = -1                   # 深度越浅优先级越高（详情页优先）
```

### 10. RequestIgnoreMiddleware — 请求忽略

根据用户定义的条件忽略特定请求：

```python
REQUEST_IGNORE_PATTERNS = [
    r'/logout',                        # 忽略登出链接
    r'/print',                         # 忽略打印页面
]
```

### 11. ResponseCodeMiddleware — 状态码处理

统一处理非 2xx 状态码：

```python
RESPONSE_CODE_ENABLED = True
RESPONSE_CODE_IGNORE = [404, 403]     # 忽略的状态码
RESPONSE_CODE_RETRY = [429, 500, 503] # 触发热重试的状态码
```

### 12. ResponseFilterMiddleware — 响应过滤

按内容类型过滤响应（例如只处理 HTML，跳过图片/JS）：

```python
RESPONSE_FILTER_TYPES = ['text/html']          # 只处理 HTML
RESPONSE_FILTER_MAX_SIZE = 10 * 1024 * 1024    # 最大响应体 10MB
```

### 13. FileMiddleware — 文件下载

处理文件下载请求（`file://` 协议或本地文件路径）：

```python
FILES_STORE = './downloads'            # 文件存储目录
```

---

## 优先级参考

| 中间件 | 默认优先级 | 说明 |
|--------|----------|------|
| RetryMiddleware | 600 | 靠外层，最早处理异常 |
| ProxyMiddleware | 650 | 代理在重试之后 |
| CloudflareBypass | 550 | 绕过在重试之前 |
| DynamicRender | 500 | 渲染在代理之后 |
| UserAgentMiddleware | 400 | 中间层 |
| DefaultHeaderMiddleware | 350 | 中间层 |
| DownloadDelayMiddleware | 700 | 延迟靠后 |
| OffsiteMiddleware | 500 | 跨域过滤在中间层 |
| PriorityMiddleware | 400 | 优先级在中间层 |
| RequestIgnoreMiddleware | 500 | 忽略在中间层 |
| ResponseCodeMiddleware | 600 | 状态码靠后 |
| ResponseFilterMiddleware | 500 | 过滤在中间层 |
| FileMiddleware | 700 | 文件下载靠后 |

## 自定义中间件

```python
# middlewares.py
class CustomMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler

    def process_request(self, request, spider):
        # 修改请求
        request.headers['X-Custom'] = 'value'
        return request

    def process_response(self, request, response, spider):
        # 修改响应
        return response

    def process_exception(self, request, exception, spider):
        # 处理异常
        return None  # 继续抛给下一个中间件
```

```python
# settings.py
MIDDLEWARES = {
    'myproject.middlewares.CustomMiddleware': 500,
}
```
