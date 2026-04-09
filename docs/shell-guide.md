# Shell 交互式终端

Crawlo Shell 提供类似 `scrapy shell` 的实时交互环境，无需编写完整爬虫即可调试选择器、测试动态渲染和验证逻辑。

## 启动方式

```bash
# 启动空 Shell
crawlo shell

# 启动并预抓取 URL
crawlo shell https://example.com
```

启动后会自动加载当前项目的 `settings.py`，确保测试环境与生产一致。

## 可用对象

| 对象 | 说明 |
|------|------|
| `fetch(url)` | 抓取页面，自动更新 `request` 和 `response` |
| `view(response)` | 在浏览器中打开响应 HTML |
| `request` | 最近一次请求对象 |
| `response` | 最近一次响应对象 |
| `settings` | 项目配置 |

## 基本用法

### 抓取与选择器

```python
>>> fetch("https://example.com")
>>> response.css("h1::text").get()
'Example Domain'

>>> response.xpath("//p/text()").getall()
['This domain is for use in illustrative examples...']

>>> response.get(".title")           # 便捷方法：自动判断 CSS/XPath
'Example Domain'

>>> response.json()                   # JSON 响应解析
```

### 多次抓取

```python
>>> fetch("https://example.com/page1")
>>> response.css("h1::text").get()
'Page 1'

>>> fetch("https://example.com/page2")
>>> response.css("h1::text").get()
'Page 2'
```

每次 `fetch` 都会更新 `request` 和 `response`。

### 浏览器预览

```python
>>> fetch("https://example.com")
>>> view(response)    # 在默认浏览器中打开 HTML
```

### 自适应选择器

```python
>>> fetch("https://shop.example.com")
>>> response.css(".btn-buy", adaptive=True, identifier="buy_button").get()
# 框架将实时输出指纹匹配分数，方便调优权重
```

### 传递请求参数

```python
>>> fetch("https://api.example.com/data", meta={"use_dynamic_loader": True})
>>> fetch("https://api.example.com", headers={"X-Custom": "value"})
```

## 终端后端

| 后端 | 条件 | 特性 |
|------|------|------|
| **IPython** | 已安装 `ipython` | 语法高亮、自动补全、支持 `await` |
| **Python Console** | 未安装 IPython | 基础交互，自动降级 |

安装 IPython 获得更好体验：

```bash
pip install ipython
```

IPython 中可直接使用异步方法：

```python
>>> response = await fetch_async("https://example.com")
```

## 下载器策略

Shell 使用轻量级下载策略，绕过完整中间件链直接下载：

1. **AioHttpDownloader** — 框架下载器，自动管理 session
2. **_SimpleFetcher** — 纯 aiohttp 回退，无框架依赖

> **注意**：Shell 中不使用 HybridDownloader，因为其子下载器创建需要完整 Crawler 上下文。

## 常见场景

### 调试 CSS 选择器

```python
>>> fetch("https://news.example.com")
>>> response.css(".article-title::text").getall()
['标题1', '标题2', '标题3']

# 测试选择器精准度
>>> response.css(".article-title::text").get()
'标题1'
```

### 验证 JSON API

```python
>>> fetch("https://api.example.com/v1/items")
>>> data = response.json()
>>> len(data["items"])
25
>>> data["items"][0]["name"]
'Item A'
```

### 检查响应编码

```python
>>> fetch("https://gbk-site.example.com")
>>> response.encoding
'gbk'
>>> response.text[:100]
'...'
```

### 测试动态渲染请求

```python
>>> fetch("https://spa.example.com", meta={"use_dynamic_loader": True})
>>> response.css(".dynamic-content::text").get()
'动态加载的内容'
```

## 退出

```
Ctrl+D 或 exit()
```

退出时自动清理下载器 session 和临时文件。
