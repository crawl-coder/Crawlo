# 请求和响应

在 Crawlo 框架中，[Request](file:///d%3A/dowell/projects/Crawlo/crawlo/network/request.py#L51-L311) 和 [Response](file:///d%3A/dowell/projects/Crawlo/crawlo/network/response.py#L22-L270) 类是网络通信的核心组件。Request 用于定义要发送的 HTTP 请求，而 Response 用于封装从服务器接收到的 HTTP 响应。

## Request 类

[Request](file:///d%3A/dowell/projects/Crawlo/crawlo/network/request.py#L51-L311) 类封装了一个 HTTP 请求对象，用于表示一个待抓取的请求任务。

### 创建 Request

```python
from crawlo import Request

# 基本 GET 请求
request = Request(url="https://example.com")

# 带回调函数的请求
def parse(response):
    # 处理响应的函数
    pass

request = Request(
    url="https://example.com",
    callback=parse
)

# POST 请求 with JSON 数据
request = Request(
    url="https://api.example.com/data",
    method="POST",
    json_body={"key": "value"},
    callback=parse
)

# POST 请求 with 表单数据
request = Request(
    url="https://api.example.com/form",
    method="POST",
    form_data={"username": "user", "password": "pass"},
    callback=parse
)
```

### Request 参数

- `url` (str): 请求 URL（必须）
- `callback` (Callable): 成功回调函数
- `method` (str): HTTP 方法，默认 GET
- `headers` (Dict[str, str]): 请求头
- `body` (bytes/str/dict): 原始请求体
- `form_data` (Dict): 表单数据，自动转为 application/x-www-form-urlencoded
- `json_body` (Dict): JSON 数据，自动序列化并设置 Content-Type
- `cb_kwargs` (Dict): 传递给 callback 的额外参数
- `cookies` (Dict): Cookies 字典
- `meta` (Dict): 元数据（跨中间件传递数据）
- `priority` (int): 优先级（数值越小越优先）
- `dont_filter` (bool): 是否跳过去重
- `timeout` (float): 超时时间（秒）
- `proxy` (str): 代理地址，如 http://127.0.0.1:8080
- `allow_redirects` (bool): 是否允许重定向
- `auth` (tuple): 认证元组 (username, password)
- `verify` (bool): 是否验证 SSL 证书
- `flags` (List[str]): 标记（用于调试或分类）
- `encoding` (str): 字符编码，默认 utf-8

### Request 方法

#### copy()

创建当前请求的副本：

```python
new_request = request.copy()
```

#### set_meta(key, value)

设置 meta 中的某个键值，支持链式调用：

```python
request = request.set_meta('custom_key', 'custom_value')
```

#### add_header(key, value)

添加请求头，支持链式调用：

```python
request = request.add_header('X-Custom-Header', 'CustomValue')
```

#### add_headers(headers)

批量添加请求头，支持链式调用：

```python
request = request.add_headers({
    'X-Custom-Header1': 'Value1',
    'X-Custom-Header2': 'Value2'
})
```

#### set_proxy(proxy)

设置代理，支持链式调用：

```python
request = request.set_proxy('http://127.0.0.1:8080')
```

#### set_timeout(timeout)

设置超时时间，支持链式调用：

```python
request = request.set_timeout(30.0)
```

#### add_flag(flag) / remove_flag(flag)

添加或移除标记，支持链式调用：

```python
request = request.add_flag('important')
request = request.remove_flag('important')
```

### Request 属性

- `url`: 请求 URL
- `method`: HTTP 方法
- `headers`: 请求头
- `body`: 请求体
- `meta`: 元数据字典
- `priority`: 优先级
- `dont_filter`: 是否跳过去重
- `timeout`: 超时时间
- `proxy`: 代理地址
- `callback`: 回调函数
- `cb_kwargs`: 回调函数参数

## Response 类

[Response](file:///d%3A/dowell/projects/Crawlo/crawlo/network/response.py#L22-L270) 类封装了 HTTP 响应，提供数据解析的便捷方法。

### Response 属性

- `url`: 响应 URL
- `headers`: 响应头
- `body`: 响应体（bytes）
- `method`: HTTP 方法
- `status_code`: 状态码
- `text`: 响应体解码后的文本
- `is_success`: 是否成功响应 (2xx)
- `is_redirect`: 是否重定向响应 (3xx)
- `is_client_error`: 是否客户端错误 (4xx)
- `is_server_error`: 是否服务器错误 (5xx)
- `content_type`: Content-Type 头
- `content_length`: Content-Length 头

### Response 方法

#### json(default=None)

将响应文本解析为 JSON 对象：

```python
data = response.json()
# 或者提供默认值
data = response.json(default={})
```

#### xpath(query) / css(query)

使用 XPath 或 CSS 选择器查询文档：

```python
# XPath
titles = response.xpath('//h1/text()').getall()

# CSS
titles = response.css('h1::text').getall()
```

#### xpath_text(query) / css_text(query)

使用 XPath 或 CSS 选择器提取并返回纯文本：

```python
# XPath
title = response.xpath_text('//h1')

# CSS
title = response.css_text('h1')
```

#### get_text(xpath_or_css, join_str=" ")

获取指定节点的纯文本：

```python
text = response.get_text('//div[@class="content"]')
```

#### get_all_text(xpath_or_css, join_str=" ")

获取多个节点的纯文本列表：

```python
texts = response.get_all_text('//div[@class="item"]//p')
```

#### re_search(pattern, flags=re.DOTALL) / re_findall(pattern, flags=re.DOTALL)

在响应文本上执行正则表达式搜索或查找：

```python
# 搜索
match = response.re_search(r'Price: \$(\d+\.\d+)')

# 查找所有
prices = response.re_findall(r'\$(\d+\.\d+)')
```

#### urljoin(url)

拼接 URL，自动处理相对路径：

```python
absolute_url = response.urljoin('/relative/path')
```

#### get_cookies()

从响应头中解析并返回 Cookies：

```python
cookies = response.get_cookies()
```

#### meta

获取关联的 Request 对象的 meta 字典：

```python
custom_data = response.meta.get('custom_key')
```

## 使用示例

### 基本爬虫示例

```python
from crawlo import Spider, Request

class ExampleSpider(Spider):
    name = "example"
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # 提取数据
        title = response.css('title::text').get()
        
        # 跟进链接
        for link in response.css('a::attr(href)').getall():
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail
            )
    
    def parse_detail(self, response):
        # 处理详情页
        item = {}
        item['title'] = response.css('h1::text').get()
        item['content'] = response.css('.content::text').getall()
        yield item
```

### 使用 Request 的高级功能

```python
def parse(self, response):
    # 设置自定义 meta 数据
    yield Request(
        url="https://api.example.com/data",
        callback=self.parse_api,
        meta={'category': 'electronics'},
        priority=1,  # 高优先级
        dont_filter=True,  # 跳过去重
        timeout=60.0,  # 60秒超时
        headers={
            'Authorization': 'Bearer token123',
            'Content-Type': 'application/json'
        }
    )

def parse_api(self, response):
    # 访问 meta 数据
    category = response.meta.get('category')
    
    # 解析 JSON 响应
    data = response.json()
    
    # 处理数据
    for item in data['items']:
        yield {
            'name': item['name'],
            'price': item['price'],
            'category': category
        }
```

## 最佳实践

1. **合理使用回调函数**：为不同的页面类型定义不同的回调函数
2. **正确设置优先级**：重要的页面设置更高的优先级（数值更小）
3. **使用 meta 传递数据**：在请求之间传递上下文信息
4. **处理编码问题**：让 Response 自动处理编码，或手动指定编码
5. **合理使用选择器**：XPath 和 CSS 选择器根据需要选择使用
6. **错误处理**：在回调函数中处理可能的解析错误
7. **避免循环请求**：使用 `dont_filter=False`（默认）来避免重复请求