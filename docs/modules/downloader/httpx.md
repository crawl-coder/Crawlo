# HttpXDownloader

HttpXDownloader是基于httpx库的下载器，提供HTTP/2支持和出色的异步功能。当需要HTTP/2支持时，它是AioHttpDownloader的良好替代品。

## 概述

HttpXDownloader使用httpx库提供具有HTTP/2支持的高级HTTP客户端功能。它针对以下方面进行了优化：

- HTTP/2协议支持
- 现代化的async/await接口
- 全面的HTTP功能
- 出色的兼容性

## 主要特性

### HTTP/2支持

HttpXDownloader支持HTTP/2协议，提供：

- 在单个连接上多路复用请求
- 头部压缩
- 服务器推送（当支持时）
- 为现代网站提供改进的性能

### 配置选项

HttpXDownloader支持各种配置选项：

```python
# 在settings.py中
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# HttpX特定设置
HTTPX_HTTP2 = True
HTTPX_FOLLOW_REDIRECTS = True
CONNECTION_POOL_LIMIT = 50
CONNECTION_TTL_DNS_CACHE = 300
```

### 中间件集成

HttpXDownloader与中间件系统集成以提供：

- 请求预处理
- 响应后处理
- 异常处理
- 统计跟踪

## API参考

### `HttpXDownloader(crawler)`

创建一个新的HttpXDownloader实例。

**参数：**
- `crawler`：拥有此下载器的爬虫实例

### `async download(request)`

使用httpx客户端下载请求。

**参数：**
- `request`：要下载的请求

**返回：**
- `Response`：下载的响应

### `open()`

初始化下载器并创建httpx客户端。

### `async close()`

清理资源并关闭httpx客户端。

### `idle()`

检查下载器是否空闲（无活动请求）。

**返回：**
- `bool`：如果下载器空闲则为True

## 配置设置

| 设置 | 描述 | 默认值 |
|------|------|--------|
| `HTTPX_HTTP2` | 启用HTTP/2支持 | True |
| `HTTPX_FOLLOW_REDIRECTS` | 自动跟随重定向 | True |
| `CONNECTION_POOL_LIMIT` | 连接池中的最大连接数 | 50 |
| `CONNECTION_TTL_DNS_CACHE` | DNS缓存TTL（秒） | 300 |

## 使用示例

```python
from crawlo.downloader import HttpXDownloader

# 在settings.py中配置
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# 或直接创建（不推荐用于生产环境）
downloader = HttpXDownloader(crawler)
await downloader.open()

# 下载请求
response = await downloader.download(request)

# 检查是否空闲
if downloader.idle():
    print("无活动下载")

# 清理
await downloader.close()
```

## 性能考虑

- HTTP/2可以显著提高支持它的网站的性能
- 连接池有助于减少多个请求的开销
- 根据目标服务器容量调整[CONNECTION_POOL_LIMIT](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/downloader/httpx_downloader.py#L22)
- 监控HTTP/2连接重用统计信息

## 何时使用HttpXDownloader

推荐在以下情况下使用HttpXDownloader：

- 支持HTTP/2的网站
- 需要HTTP/2性能优势的情况
- 现代Web应用程序
- 当您需要最新的HTTP功能时
- 从HTTP/2多路复用中受益的API

可能不适用于：

- 仅支持HTTP/1.1的旧网站
- 需要最大原始性能的情况（AioHttp可能更快）
- 具有特定兼容性要求的网站