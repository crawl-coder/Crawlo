# AioHttpDownloader

AioHttpDownloader是基于aiohttp库的高性能下载器。它是Crawlo的默认下载器，为大多数网页爬取任务提供出色的性能。

## 概述

AioHttpDownloader利用aiohttp库提供异步HTTP客户端功能。它针对以下方面进行了优化：

- 高并发
- 连接池
- 高效的内存使用
- HTTP/1.1支持

## 主要特性

### 性能优化

- **连接池**：重用连接以减少开销
- **Keep-Alive支持**：维护持久连接
- **并发请求**：同时处理多个请求
- **高效内存使用**：每个请求的内存占用最小

### 配置选项

AioHttpDownloader支持各种配置选项：

```python
# 在settings.py中
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"

# AioHttp特定设置
CONNECTION_POOL_LIMIT = 50
CONNECTION_TTL_DNS_CACHE = 300
CONNECTION_KEEPALIVE_TIMEOUT = 15
AIOHTTP_AUTO_DECOMPRESS = True
AIOHTTP_FORCE_CLOSE = False
```

### 中间件集成

AioHttpDownloader与中间件系统集成以提供：

- 请求预处理
- 响应后处理
- 异常处理
- 统计跟踪

## API参考

### `AioHttpDownloader(crawler)`

创建一个新的AioHttpDownloader实例。

**参数：**
- `crawler`：拥有此下载器的爬虫实例

### `async download(request)`

使用aiohttp客户端下载请求。

**参数：**
- `request`：要下载的请求

**返回：**
- `Response`：下载的响应

### `open()`

初始化下载器并创建aiohttp客户端会话。

### `async close()`

清理资源并关闭aiohttp客户端会话。

### `idle()`

检查下载器是否空闲（无活动请求）。

**返回：**
- `bool`：如果下载器空闲则为True

## 配置设置

| 设置 | 描述 | 默认值 |
|------|------|--------|
| `CONNECTION_POOL_LIMIT` | 连接池中的最大连接数 | 50 |
| `CONNECTION_TTL_DNS_CACHE` | DNS缓存TTL（秒） | 300 |
| `CONNECTION_KEEPALIVE_TIMEOUT` | Keep-alive超时（秒） | 15 |
| `AIOHTTP_AUTO_DECOMPRESS` | 自动解压缩响应 | True |
| `AIOHTTP_FORCE_CLOSE` | 每个请求后强制关闭连接 | False |

## 使用示例

```python
from crawlo.downloader import AioHttpDownloader

# 在settings.py中配置
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"

# 或直接创建（不推荐用于生产环境）
downloader = AioHttpDownloader(crawler)
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

- 根据目标服务器容量调整[CONNECTION_POOL_LIMIT](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/downloader/aiohttp_downloader.py#L23)
- 使用适当的超时设置以避免挂起请求
- 为压缩内容启用[AIOHTTP_AUTO_DECOMPRESS](https://github.com/crawl-coder/Crawlo/blob/master/crawlo/downloader/aiohttp_downloader.py#L26)
- 监控连接重用统计信息以优化性能

## 何时使用AioHttpDownloader

推荐在以下情况下使用AioHttpDownloader：

- 通用网页爬取
- 高并发场景
- 静态内容下载
- 需要最大性能时
- 大多数标准网页爬取任务

可能不适用于：

- JavaScript密集型网站（请改用Selenium或Playwright）
- 需要浏览器指纹识别的情况（请改用CurlCffi）
- 具有严格反机器人措施的网站（请考虑替代方案）