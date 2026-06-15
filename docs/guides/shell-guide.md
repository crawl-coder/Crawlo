# Crawlo Shell 使用指南

Crawlo Shell 是一个**交互式调试终端**，用于快速测试选择器、分析页面结构、验证提取逻辑，而无需编写和运行完整的 Spider。

---

## 快速开始

```bash
# 启动空 Shell
crawlo shell

# 启动并预抓取一个页面
crawlo shell https://www.baidu.com

# 从浏览器复制的 curl 命令启动
crawlo shell --curl 'curl https://www.baidu.com -H "Authorization: Bearer xxx"'
```

启动后自动加载项目配置（如果在项目根目录下运行），否则以 standalone 模式启动。

---

## 可用对象

Shell 启动后，以下对象注入到交互式命名空间中：

### 核心函数

| 函数 | 说明 |
|------|------|
| `fetch(url, **kwargs)` | 抓取 URL，自动更新 `request` 和 `response` 变量 |
| `from_curl(curl_cmd)` | 解析浏览器复制的 curl 命令并抓取 |
| `view(response)` | 在默认浏览器中打开响应 HTML |

### 环境变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `request` | `Request` | 最后一次请求的 Request 对象 |
| `response` | `Response` | 最后一次请求的 Response 对象 |
| `settings` | `dict` | 当前项目配置 |
| `Request` | class | Request 类本身，可用于手动构造 |

---

## 典型工作流

### 1. 测试选择器

```python
# 先抓取页面
fetch('https://www.baidu.com')

# 测试 CSS 选择器
response.css('title::text').get()
# → '百度一下，你就知道'

response.css('a::text').getall()[:5]
# → ['新闻', 'hao123', '地图', '视频', '贴吧']

# 测试 XPath
response.xpath('//a/text()').getall()[:5]
# → ['新闻', 'hao123', '地图', '视频', '贴吧']

# 提取属性
response.css('a::attr(href)').getall()[:3]
# → ['https://news.baidu.com', 'https://www.hao123.com', ...]
```

### 2. 分析响应结构

```python
# 查看响应状态码
response.status
# → 200

# 解析 JSON 响应
response.json()
# → {'items': [...], 'total': 42}

# 检查响应头
response.headers.get('Content-Type')
# → 'text/html; charset=utf-8'

# 使用正则提取
response.re_findall(r'https?://[^\s"<>]+')
# → ['https://www.baidu.com', 'https://www.baidu.com/s?wd=...', ...]

# 查看原始 HTML（前 500 字符）
response.text[:500]
```

### 3. 复杂请求测试

```python
# GET 请求带参数
fetch('https://www.baidu.com/s',
      params={'wd': 'python', 'pn': 10})

# POST 请求
fetch('https://www.baidu.com',
      method='POST',
      json_body={'key': 'value'})

# 表单提交
fetch('https://www.baidu.com',
      method='POST',
      form_data={'key': 'value'})

# 自定义请求头
fetch('https://www.baidu.com',
      headers={'User-Agent': 'Mozilla/5.0'})

# 设置 Cookie
fetch('https://www.baidu.com',
      cookies={'BAIDUID': 'abc123'})

# 使用代理
fetch('https://www.baidu.com',
      proxy='http://127.0.0.1:8080')

# 动态渲染（JS 页面）
fetch('https://www.baidu.com',
      meta={'use_dynamic_loader': True})
```

### 4. 从 curl 命令抓取

从浏览器 DevTools 复制请求为 cURL 命令，直接粘贴到 Shell：

```python
from_curl("curl 'https://www.baidu.com' \
  -H 'User-Agent: Mozilla/5.0' \
  -H 'Cookie: BAIDUID=abc123'")
```

自动解析 URL、Headers、Cookie 等。

### 5. 可视化预览

```python
# 在浏览器中查看页面结构
view(response)
```

生成临时 HTML 文件并在默认浏览器中打开，方便直观查看页面布局。

---

## 自适应选择器

Shell 支持自适应选择器模式，在网站改版导致选择器失效时自动修复：

```python
# 首次命中时自动保存元素指纹
response.css('.product-price', adaptive=True, identifier='price').get()

# 网站改版后，选择器失效时自动从指纹恢复
response.css('.product-price', adaptive=True, identifier='price').get()

# 查找结构相似的兄弟元素（如商品列表项）
response.find_similar('price', threshold=60)

# 自定义相似度匹配（跳过某些属性）
response.css('.item', adaptive=True, identifier='item',
             percentage=70.0, timeout=10.0).getall()
```

自适应模式支持参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `adaptive` | `False` | 是否启用自适应模式 |
| `identifier` | `''` | 指纹标识名，用于跨会话恢复 |
| `percentage` | `50.0` | 相似度阈值（0-100） |
| `timeout` | `5.0` | 自适应匹配超时（秒） |

---

## Response 对象参考

### 状态检查

```python
response.is_success       # → True (2xx)
response.is_redirect      # → False (3xx)
response.is_client_error  # → False (4xx)
response.is_server_error  # → False (5xx)
```

### 数据提取

| 方法 | 说明 |
|------|------|
| `response.css(query)` | CSS 选择器，返回 SelectorList |
| `response.xpath(query)` | XPath 选择器，返回 SelectorList |
| `response.get(query)` | 获取第一个匹配元素的文本 |
| `response.getall(query)` | 获取所有匹配元素的文本列表 |
| `response.attr(query, name)` | 获取第一个匹配元素的属性值 |
| `response.attrs(query, name)` | 获取所有匹配元素的属性值列表 |
| `response.get_outer(query)` | 获取第一个匹配元素的完整 HTML |
| `response.getall_outer(query)` | 获取所有匹配元素的完整 HTML 列表 |
| `response.json()` | 将响应体解析为 JSON |
| `response.re_findone(pattern)` | 返回第一个正则匹配 |
| `response.re_findall(pattern)` | 返回所有正则匹配列表 |
| `response.re_search(pattern)` | 返回正则 Match 对象 |
| `response.re_css(query, pattern)` | 从选择器匹配元素中提取正则 |

### URL 处理

```python
# 拼接相对 URL
response.urljoin('/about')
# → 'https://www.baidu.com/about'

# 创建跟随链接的 Request
response.follow('/more')
```

---

## Request 对象参考

```python
# 手动构造 Request
req = Request('https://www.baidu.com',
              method='GET',
              headers={'User-Agent': 'Mozilla/5.0'},
              cookies={'BAIDUID': 'abc'},
              meta={'retry_times': 0})

# 链式 API
req = Request.get('https://www.baidu.com')
    .add_header('User-Agent', 'Mozilla/5.0')
    .set_proxy('http://127.0.0.1:8080')
    .set_timeout(30)
    .add_flag('important')

req.to_dict()  # 序列化为字典
req.copy()     # 深拷贝
```

---

## 实用技巧

### 使用 IPython（推荐）

```bash
pip install ipython
```

Crawlo Shell 检测到 IPython 时自动使用增强模式，支持语法高亮、自动补全、异步执行：

```python
# IPython 中可直接 await
await fetch_async('https://www.baidu.com')
await from_curl_async('curl https://www.baidu.com')
```

### 快速验证提取规则

```python
# 在 Shell 中确认选择器效果后，直接复制到 Spider
# Shell 中：
prices = response.css('.price::text').re(r'\d+\.\d+')
print(prices[:5])
# → ['29.99', '49.99', ...]

# Spider 中：
def parse(self, response):
    for item in response.css('.product'):
        yield {
            'price': item.css('.price::text').re_first(r'\d+\.\d+'),
            'title': item.css('.title::text').get(),
        }
```

### 调试中间件效果

```python
# 测试代理链是否生效
fetch('https://www.baidu.com', proxy='http://proxy:8080')
response.status
# → 200

# 验证请求头是否正确传递
fetch('https://www.baidu.com',
      headers={'User-Agent': 'Mozilla/5.0'})
response.status
# → 200
```

---

## 常见问题

**Q: Shell 如何加载项目配置？**

Shell 从当前目录向上查找 `crawlo.cfg` 或 `settings.py`，找到后自动加载项目配置。如果未找到，以 standalone 模式启动。

**Q: 如何在 Shell 中使用自定义中间件？**

Shell 默认绕过中间件链直接调用下载器。如需测试中间件效果，建议运行完整的 Crawler。

**Q: Shell 支持异步操作吗？**

在标准 Python 控制台中，`fetch()` 和 `from_curl()` 是同步阻塞的。安装 IPython 后可使用 `await fetch_async()` 异步执行。
