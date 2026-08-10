# 基础爬虫示例

> 从 basic-examples 拆分：静态页面、分页、表单提交。

## 基础案例

### 案例1: 简单网页抓取

**场景**：抓取 Quotes to Scrape 网站的名言数据

**目标网站**：https://quotes.toscrape.com/

**完整代码**：

```python
from crawlo import Spider
from crawlo import Request


class QuotesSpider(Spider):
 """名言爬虫"""
 
 name = 'quotes'
 start_urls = ['https://quotes.toscrape.com/']
 
 async def parse(self, response):
 # 提取所有名言
 for quote in response.css('div.quote'):
 yield {
 'text': quote.css('span.text::text').get(),
 'author': quote.css('small.author::text').get(),
 'tags': quote.css('div.tags a.tag::text').getall(),
 }
 
 # 跟进下一页
 next_page = response.css('li.next a::attr(href)').get()
 if next_page:
 yield response.follow(next_page, callback=self.parse)
```

**运行**：
```bash
crawlo run quotes -o quotes.json
```

---

### 案例2: 分页抓取

**场景**：抓取商品列表，共100页

**目标网站**：https://example.com/products

**完整代码**：

```python
from crawlo import Spider


class ProductSpider(Spider):
 """商品爬虫"""
 
 name = 'products'
 start_urls = ['https://example.com/products?page=1']
 
 async def parse(self, response):
 # 提取商品
 for product in response.css('div.product'):
 yield {
 'name': product.css('h3::text').get(),
 'price': product.css('.price::text').get(),
 'url': product.css('a::attr(href)').get(),
 }
 
 # 提取当前页码
 current_page = response.css('.current-page::text').get()
 if current_page:
 page_num = int(current_page)
 
 # 抓取下一页（最多100页）
 if page_num < 100:
 next_page = f'https://example.com/products?page={page_num + 1}'
 yield Request(next_page, callback=self.parse)
```

---

### 案例3: 表单提交

**场景**：提交搜索表单，抓取结果

**目标网站**：https://example.com/search

**完整代码**：

```python
from crawlo import Spider
from crawlo import Request


class SearchSpider(Spider):
 """搜索爬虫"""
 
 name = 'search'
 
 async def start_requests(self):
 # 提交搜索表单
 yield Request(
 url='https://example.com/search',
 method='POST',
 form_data={
 'keyword': 'python',
 'category': 'books',
 },
 callback=self.parse_results
 )
 
 async def parse_results(self, response):
 # 提取搜索结果
 for result in response.css('div.result'):
 yield {
 'title': result.css('h2::text').get(),
 'link': result.css('a::attr(href)').get(),
 }
```

---
