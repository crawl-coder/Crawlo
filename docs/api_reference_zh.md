# Crawlo API 参考

本文档提供了 Crawlo 框架中核心类和方法的详细信息。

## 核心类

### Spider

所有爬虫的基类。

#### 属性

- `name` (str)：爬虫的唯一标识符。必填。
- `allowed_domains` (list)：爬虫允许爬取的域名列表。
- `start_urls` (list)：爬虫开始爬取的 URL 列表。
- `custom_settings` (dict)：覆盖项目设置的设置字典。

#### 方法

- `start_requests()`：生成初始请求。重写此方法以提供自定义起始请求。
- `parse(response)`：解析响应并提取数据。必须由子类实现。

#### 示例

```python
from crawlo import Spider, Request

class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]

    def parse(self, response):
        # 从响应中提取数据
        yield {"title": response.css("title::text").get()}
        
        # 跟进链接
        for link in response.css("a::attr(href)").getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### Item

爬取项目的基类。

#### Field

表示项目中的字段。

##### 参数

- `description` (str)：字段的描述。
- `default` (any)：字段的默认值。

#### 示例

```python
from crawlo.items import Item, Field

class MyItem(Item):
    title = Field(description="页面标题")
    url = Field(description="页面 URL", default="")
```

### Request

表示 HTTP 请求。

#### 参数

- `url` (str)：请求的 URL。
- `callback` (callable)：用响应调用的函数。
- `method` (str)：HTTP 方法（默认："GET"）。
- `headers` (dict)：HTTP 头部。
- `body` (str)：请求体。
- `meta` (dict)：传递给回调的元数据。
- `dont_filter` (bool)：是否跳过重复过滤。

#### 示例

```python
from crawlo import Request

request = Request(
    url="https://example.com",
    callback=self.parse,
    method="POST",
    headers={"Content-Type": "application/json"},
    body='{"key": "value"}',
    meta={"custom_data": "example"}
)
```

### Response

表示 HTTP 响应。

#### 属性

- `url` (str)：响应的 URL。
- `status_code` (int)：HTTP 状态码。
- `headers` (dict)：HTTP 头部。
- `body` (bytes)：响应体。
- `meta` (dict)：来自请求的元数据。

#### 方法

- `css(selector)`：使用 CSS 选择器提取数据。
- `xpath(selector)`：使用 XPath 选择器提取数据。
- `json()`：将响应体解析为 JSON。
- `text`：获取响应体为文本。

#### 示例

```python
def parse(self, response):
    # 使用 CSS 选择器提取数据
    title = response.css("title::text").get()
    
    # 使用 XPath 提取数据
    links = response.xpath("//a/@href").getall()
    
    # 解析 JSON 响应
    data = response.json()
```

## 配置

### 设置

可以在 `settings.py` 中配置设置，或通过爬虫中的 `custom_settings` 属性配置。

#### 核心设置

- `PROJECT_NAME` (str)：项目名称。
- `CONCURRENCY` (int)：并发请求数。
- `DOWNLOAD_DELAY` (float)：请求之间的延迟（秒）。
- `DOWNLOAD_TIMEOUT` (int)：请求超时（秒）。

#### 下载器设置

- `DOWNLOADER` (str)：下载器类的完整路径。
- `DOWNLOADER_TYPE` (str)：简化下载器名称（"aiohttp"、"httpx"、"curl_cffi"）。
- `VERIFY_SSL` (bool)：是否验证 SSL 证书。
- `USE_SESSION` (bool)：是否使用会话进行请求。

#### 管道设置

- `PIPELINES` (list)：要使用的管道类列表。

#### 中间件设置

- `MIDDLEWARES` (list)：要使用的中间件类列表。

#### 分布式设置

- `RUN_MODE` (str)："standalone" 或 "distributed"。
- `QUEUE_TYPE` (str)："memory" 或 "redis"。
- `SCHEDULER` (str)：分布式模式的调度器类。
- `FILTER_CLASS` (str)：用于重复检测的过滤器类。
- `REDIS_HOST` (str)：Redis 主机。
- `REDIS_PORT` (int)：Redis 端口。
- `REDIS_PASSWORD` (str)：Redis 密码。
- `REDIS_DB` (int)：Redis 数据库编号。

## 管道

### ConsolePipeline

将项目输出到控制台。

### JsonPipeline

将项目保存到 JSON 文件。

#### 设置

- `JSON_FILE` (str)：JSON 文件的路径。

### CsvPipeline

将项目保存到 CSV 文件。

#### 设置

- `CSV_FILE` (str)：CSV 文件的路径。

### AsyncmyMySQLPipeline

使用 asyncmy 将项目存储在 MySQL 数据库中。

#### 设置

- `MYSQL_HOST` (str)：MySQL 主机。
- `MYSQL_PORT` (int)：MySQL 端口。
- `MYSQL_USER` (str)：MySQL 用户。
- `MYSQL_PASSWORD` (str)：MySQL 密码。
- `MYSQL_DB` (str)：MySQL 数据库。
- `MYSQL_TABLE` (str)：MySQL 表。

## 中间件

### RequestIgnoreMiddleware

根据自定义逻辑过滤请求。

### DownloadDelayMiddleware

在请求之间添加延迟。

### DefaultHeaderMiddleware

向请求添加默认头部。

### ProxyMiddleware

处理请求的代理配置。

### RetryMiddleware

为失败的请求实现重试逻辑。

#### 设置

- `MAX_RETRY_TIMES` (int)：最大重试次数。
- `RETRY_HTTP_CODES` (list)：要重试的 HTTP 状态码。

### ResponseCodeMiddleware

处理响应代码并处理错误。

## 实用工具

### get_logger

返回配置的记录器。

#### 参数

- `name` (str)：记录器名称。

#### 示例

```python
from crawlo.utils.log import get_logger

logger = get_logger(__name__)
logger.info("这是一条日志消息")
```

### request_fingerprint

为请求生成指纹以检测重复。

#### 参数

- `request` (Request)：要生成指纹的请求。

#### 示例

```python
from crawlo.utils.request import request_fingerprint

fp = request_fingerprint(request)
```