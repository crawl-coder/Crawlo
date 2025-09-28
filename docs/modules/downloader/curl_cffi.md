# CurlCffiDownloader

CurlCffiDownloader是基于curl-cffi的下载器，提供浏览器指纹模拟功能。它特别适用于绕过检测自动化请求的反机器人措施。

## 概述

CurlCffiDownloader使用curl-cffi库提供具有浏览器指纹模拟功能的HTTP客户端。它针对以下方面进行了优化：

- 浏览器指纹模拟
- 绕过反机器人措施
- 类JavaScript的请求行为
- 与真实浏览器的高度兼容性

## 主要特性

### 浏览器指纹模拟

CurlCffiDownloader可以模拟各种浏览器指纹：

- Chrome、Edge、Safari、Firefox浏览器签名
- TLS指纹识别
- HTTP/2指纹识别
- JA3指纹识别抵抗

### 配置选项

CurlCffiDownloader支持各种配置选项：

```python
# 在settings.py中
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# CurlCffi特定设置
CURL_BROWSER_TYPE = "chrome"
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101",
    "safari": "safari184",
    "firefox": "firefox135",
}
```

### 中间件集成

CurlCffiDownloader与中间件系统集成以提供：

- 请求预处理
- 响应后处理
- 异常处理
- 统计跟踪

## API参考

### `CurlCffiDownloader(crawler)`

创建一个新的CurlCffiDownloader实例。

**参数：**
- `crawler`：拥有此下载器的爬虫实例

### `async download(request)`

使用curl-cffi客户端下载请求。

**参数：**
- `request`：要下载的请求

**返回：**
- `Response`：下载的响应

### `open()`

初始化下载器并创建curl-cffi客户端。

### `async close()`

清理资源并关闭curl-cffi客户端。

### `idle()`

检查下载器是否空闲（无活动请求）。

**返回：**
- `bool`：如果下载器空闲则为True

## 配置设置

| 设置 | 描述 | 默认值 |
|------|------|--------|
| `CURL_BROWSER_TYPE` | 要模拟的浏览器类型 | "chrome" |
| `CURL_BROWSER_VERSION_MAP` | 浏览器版本映射 | 见上文 |

## 使用示例

```python
from crawlo.downloader import CurlCffiDownloader

# 在settings.py中配置
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# 配置浏览器类型
CURL_BROWSER_TYPE = "chrome136"

# 或直接创建（不推荐用于生产环境）
downloader = CurlCffiDownloader(crawler)
await downloader.open()

# 下载请求
response = await downloader.download(request)

# 检查是否空闲
if downloader.idle():
    print("无活动下载")

# 清理
await downloader.close()
```

## 浏览器模拟

CurlCffiDownloader可以模拟不同的浏览器：

```python
# 模拟Chrome
CURL_BROWSER_TYPE = "chrome"

# 模拟Firefox
CURL_BROWSER_TYPE = "firefox"

# 模拟Safari
CURL_BROWSER_TYPE = "safari"

# 模拟Edge
CURL_BROWSER_TYPE = "edge"
```

## 性能考虑

- 浏览器指纹模拟会增加一些开销
- 连接重用可能不如纯HTTP客户端高效
- 内存使用量可能比简单下载器更高
- 某些高级功能可能不可用

## 何时使用CurlCffiDownloader

推荐在以下情况下使用CurlCffiDownloader：

- 具有强反机器人措施的网站
- 关注浏览器指纹检测的情况
- 阻止标准HTTP客户端的网站
- 当您需要更像真实浏览器时
- 具有高级机器人保护的电子商务网站

可能不适用于：

- 没有反机器人措施的简单网站
- 需要最大性能的情况
- 偏好最小依赖的情况
- 内部API或简单Web服务