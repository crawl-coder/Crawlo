# 创建第一个爬虫

本教程将带你从零开始，创建并运行你的第一个 Crawlo 爬虫。

## 🎯 学习目标

完成本教程后，你将能够：
- 创建 Crawlo 项目
- 编写爬虫代码
- 提取网页数据
- 保存数据到文件

---

## 步骤1: 创建项目

打开终端，运行以下命令：

```bash
# 创建项目
crawlo startproject myfirstspider

# 进入项目目录
cd myfirstspider
```

**项目结构**：

```
myfirstspider/
├── spiders/              # 爬虫目录
│   └── __init__.py
├── settings.py           # 配置文件
├── items.py              # 数据模型（可选）
├── pipelines.py          # 数据管道（可选）
└── middlewares.py        # 中间件（可选）
```

---

## 步骤2: 生成爬虫

使用 CLI 工具生成爬虫模板：

```bash
# 生成爬虫
crawlo genspider quotes quotes.toscrape.com
```

这会在 `spiders/` 目录下创建 `quotes.py` 文件。

---

## 步骤3: 编写爬虫代码

打开 `spiders/quotes.py`，编写爬虫逻辑：

```python
from crawlo import Spider
from crawlo import Request


class QuotesSpider(Spider):
    """名言爬虫"""
    
    name = 'quotes'
    start_urls = ['https://quotes.toscrape.com/']
    
    async def parse(self, response):
        """解析名言列表页"""
        # 提取所有名言
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('a.tag::text').getall(),
            }
        
        # 翻页
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

**代码说明**：
- `name`: 爬虫名称，用于运行爬虫时指定
- `start_urls`: 起始URL列表
- `parse()`: 默认回调函数，处理响应
- `response.css()`: 使用CSS选择器提取数据
- `yield`: 返回提取的数据或新的请求

---

## 步骤4: 运行爬虫

```bash
# 运行爬虫
crawlo run quotes

# 保存数据到 JSON 文件
crawlo run quotes -o quotes.json

# 保存数据到 CSV 文件
crawlo run quotes -o quotes.csv

# 查看详细日志
crawlo run quotes --log-level DEBUG
```

---

## 步骤5: 查看结果

运行完成后，查看生成的 `quotes.json` 文件：

```json
[
  {
    "text": ""The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking."",
    "author": "Albert Einstein",
    "tags": ["change", "deep-thoughts", "thinking", "world"]
  },
  {
    "text": ""It is our choices, Harry, that show what we truly are, far more than our abilities."",
    "author": "J.K. Rowling",
    "tags": ["abilities", "choices"]
  }
]
```

恭喜！你已经成功创建了第一个爬虫！🎉

---

## 🔍 进阶技巧

### 技巧1: 添加请求头

```python
class QuotesSpider(Spider):
    name = 'quotes'
    start_urls = ['https://quotes.toscrape.com/']
    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml',
        }
    }
    
    async def parse(self, response):
        # 你的代码
        pass
```

### 技巧2: 使用 Item 类

创建 `items.py`：

```python
from crawlo import Item


class QuoteItem(Item):
    """名言数据模型"""
    text: str
    author: str
    tags: list
```

在爬虫中使用：

```python
from items import QuoteItem

async def parse(self, response):
    for quote in response.css('div.quote'):
        item = QuoteItem()
        item['text'] = quote.css('span.text::text').get()
        item['author'] = quote.css('small.author::text').get()
        item['tags'] = quote.css('a.tag::text').getall()
        yield item
```

### 技巧3: 添加下载延迟

```python
class QuotesSpider(Spider):
    name = 'quotes'
    start_urls = ['https://quotes.toscrape.com/']
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,  # 1秒延迟
    }
```

### 技巧4: 限制爬取深度

```python
async def parse(self, response):
    # 提取数据
    # ...
    
    # 翻页（限制最多5页）
    next_page = response.css('li.next a::attr(href)').get()
    if next_page and response.request.meta.get('depth', 0) < 5:
        yield response.follow(
            next_page,
            callback=self.parse,
            meta={'depth': response.request.meta.get('depth', 0) + 1}
        )
```

---

## 📚 下一步

- 📖 [5分钟快速上手](5min-quickstart.md) - 完整的快速入门教程
- 🎯 [实战案例](../examples/) - 学习更多爬虫技巧
- 📊 [配置指南](../guides/configuration/) - 了解配置选项
- ❓ [常见问题 FAQ](../faq/) - 解决问题

---

**遇到问题？** 查看 [FAQ](../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)
