# 实战案例

本章节提供真实的 Crawlo 爬虫案例，帮助你快速上手。

---

## 📖 案例列表

### 基础案例
- [案例1: 简单网页抓取](#案例1-简单网页抓取) - 静态页面
- [案例2: 分页抓取](#案例2-分页抓取) - 多页数据
- [案例3: 表单提交](#案例3-表单提交) - POST 请求

### 进阶案例
- [案例4: 动态渲染](#案例4-动态渲染) - JavaScript 页面
- [案例5: API 抓取](#案例5-api-抓取) - JSON 数据
- [案例6: 登录抓取](#案例6-登录抓取) - 需要认证

### 生产案例
- [案例7: 分布式抓取](#案例7-分布式抓取) - 多节点
- [案例8: 定时任务](#案例8-定时任务) - 自动化
- [案例9: 数据监控](#案例9-数据监控) - 变化检测

---

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

## 进阶案例

### 案例4: 动态渲染

**场景**：抓取 JavaScript 渲染的页面

**目标网站**：https://example.com/dynamic

**完整代码**：

```python
from crawlo import Spider


class DynamicSpider(Spider):
    """动态页面爬虫"""
    
    name = 'dynamic'
    start_urls = ['https://example.com/dynamic']
    
    async def parse(self, response):
        # 使用浏览器渲染
        # 方式1: 在请求中指定
        yield Request(
            url='https://example.com/dynamic',
            callback=self.parse_dynamic,
            meta={'use_dynamic_loader': True}
        )
    
    async def parse_dynamic(self, response):
        # 现在可以提取 JavaScript 渲染的内容
        yield {
            'title': response.css('h1::text').get(),
            'data': response.css('.dynamic-content::text').get(),
        }
```

**配置**：
```python
# settings.py
DYNAMIC_LOADER_ENABLED = True
```

---

### 案例5: API 抓取

**场景**：抓取 REST API 返回的 JSON 数据

**目标网站**：https://api.example.com/data

**完整代码**：

```python
import json
from crawlo import Spider
from crawlo import Request


class APISpider(Spider):
    """API 爬虫"""
    
    name = 'api'
    
    async def start_requests(self):
        # 请求 API
        yield Request(
            url='https://api.example.com/data',
            headers={'Authorization': 'Bearer YOUR_TOKEN'},
            callback=self.parse_api
        )
    
    async def parse_api(self, response):
        # 解析 JSON
        data = json.loads(response.text)
        
        # 提取数据
        for item in data.get('results', []):
            yield {
                'id': item.get('id'),
                'name': item.get('name'),
                'value': item.get('value'),
            }
        
        # 处理分页
        if data.get('next_page'):
            yield Request(
                url=data['next_page'],
                callback=self.parse_api
            )
```

---

### 案例6: 登录抓取

**场景**：先登录，再抓取需要认证的数据

**目标网站**：https://example.com/login

**完整代码**：

```python
from crawlo import Spider
from crawlo import Request


class LoginSpider(Spider):
    """登录爬虫"""
    
    name = 'login'
    login_url = 'https://example.com/login'
    start_urls = ['https://example.com/dashboard']
    
    async def start_requests(self):
        # 先登录
        yield Request(
            url=self.login_url,
            method='POST',
            form_data={
                'username': 'your_username',
                'password': 'your_password',
            },
            callback=self.after_login
        )
    
    async def after_login(self, response):
        # 检查登录是否成功
        if 'logout' in response.text:
            self.logger.info("登录成功")
            
            # 登录后抓取
            for url in self.start_urls:
                yield Request(url, callback=self.parse_dashboard)
        else:
            self.logger.error("登录失败")
    
    async def parse_dashboard(self, response):
        # 提取需要登录才能看到的数据
        yield {
            'user_info': response.css('.user-info::text').get(),
            'data': response.css('.private-data::text').get(),
        }
```

---

## 生产案例

### 案例7: 分布式抓取

**场景**：使用多节点并行抓取大量数据，支持 ACK 确认、故障转移和自动协调退出

**配置**（使用分布式系统模式）：

```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis_stream'

# Redis 配置
REDIS_HOST = 'redis.example.com'
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_password'

# 并发控制
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5

# 集群配置（可选，默认自动启用）
CLUSTER_HEARTBEAT_INTERVAL = 15
CLUSTER_WORKER_TIMEOUT = 90
CLUSTER_FAILOVER_CHECK_INTERVAL = 30
```

> 详细说明见：[部署模式](../concepts/architecture.md#2-部署模式-deployment-modes)、[Redis Key 说明](../concepts/redis-keys.md)

**爬虫代码**：

```python
from crawlo import Spider
from crawlo import Request


class DistributedSpider(Spider):
    """分布式爬虫"""
    
    name = 'distributed'
    start_urls = ['https://example.com/list']
    
    async def parse(self, response):
        # 提取详情页链接
        for link in response.css('a.detail::attr(href)').getall():
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail
            )
        
        # 提取下一页
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
    
    async def parse_detail(self, response):
        yield {
            'title': response.css('h1::text').get(),
            'content': response.css('.content::text').get(),
        }
```

**启动多个 Worker**：

```bash
# 终端 1 — Worker 1
cd examples/ofweek_distributed
python run.py

# 终端 2 — Worker 2（间隔若干秒启动）
python run.py

# 终端 3~N
python run.py
```

各 Worker 自动注册到 Redis，通过 Consumer Group 分配任务。
当所有任务完成时，Leader Worker 自动广播 shutdown 信号，所有 Worker 优雅退出。

---

### 案例8: 定时任务

**场景**：每天定时运行爬虫

**方式1: 使用 Crontab（Linux/Mac）**

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点运行）
0 2 * * * cd /path/to/project && crawlo run myspider -o output.json
```

**方式2: 使用 Python 脚本**

```python
import asyncio
from datetime import datetime, time
from crawlo.crawler import Crawler


async def run_spider_daily():
    """每天运行爬虫"""
    
    while True:
        now = datetime.now()
        
        # 如果是凌晨2点
        if now.hour == 2 and now.minute == 0:
            print(f"开始运行爬虫: {now}")
            
            # 运行爬虫
            crawler = Crawler()
            await crawler.crawl('myspider')
            
            # 等待1小时，避免重复运行
            await asyncio.sleep(3600)
        
        # 每分钟检查一次
        await asyncio.sleep(60)


if __name__ == '__main__':
    asyncio.run(run_spider_daily())
```

---

### 案例9: 数据监控

**场景**：监控商品价格变化

**完整代码**：

```python
from crawlo import Spider


class PriceMonitorSpider(Spider):
    """价格监控爬虫"""
    
    name = 'price_monitor'
    start_urls = [
        'https://example.com/product/1',
        'https://example.com/product/2',
        'https://example.com/product/3',
    ]
    
    async def parse(self, response):
        # 提取当前价格
        current_price = response.css('.price::text').get()
        product_name = response.css('h1::text').get()
        
        # 获取历史价格（从数据库）
        old_price = await self.get_old_price(response.url)
        
        # 检查价格变化
        if old_price and current_price != old_price:
            self.logger.warning(
                f"价格变化: {product_name}\n"
                f"  旧价格: {old_price}\n"
                f"  新价格: {current_price}"
            )
            
            # 发送通知
            await self.send_notification(
                f"价格提醒: {product_name} 从 {old_price} 变为 {current_price}"
            )
        
        # 保存当前价格
        await self.save_price(response.url, current_price)
        
        yield {
            'product': product_name,
            'price': current_price,
            'changed': current_price != old_price,
        }
    
    async def get_old_price(self, url):
        """从数据库获取旧价格"""
        # 实现数据库查询逻辑
        pass
    
    async def save_price(self, url, price):
        """保存价格到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def send_notification(self, message):
        """发送通知"""
        # 实现通知逻辑（邮件、飞书、钉钉等）
        pass
```

**配置**：

```python
# settings.py
# 定时运行
CHECKPOINT_ENABLED = True
CHECKPOINT_INTERVAL = 3600  # 每小时保存一次

# 通知配置
NOTIFICATION_ENABLED = True
NOTIFICATION_ON_ERROR = True
NOTIFICATION_CHANNELS = ['feishu']
```

---

## 📚 更多案例

查看 [examples/](https://github.com/crawl-coder/Crawlo/tree/main/examples) 目录获取更多示例：

- **ofweek_standalone** - 内存模式示例
- **ofweek_spider** - 基础爬虫示例
- **ofweek_distributed** - 分布式示例
- **eastmoney_fin_report_crawler** - 财务报告爬虫
- **listed_companies_market_value_info** - 上市公司市值爬虫

---

## 💡 最佳实践

### 1. 错误处理

```python
async def parse(self, response):
    try:
        # 正常解析
        data = response.css('div.data::text').get()
        yield {'data': data}
    except Exception as e:
        self.logger.error(f"解析失败: {e}")
        yield {'error': str(e), 'url': response.url}
```

### 2. 限速控制

```python
# settings.py
DOWNLOAD_DELAY = 1.0  # 1秒延迟
RANDOMNESS = True     # 随机抖动
CONCURRENCY = 8       # 适中并发
```

### 3. 数据验证

```python
class ValidationPipeline:
    def process_item(self, item, spider):
        # 验证必填字段
        if not item.get('title'):
            raise DropItem(f"缺少 title: {item}")
        
        # 验证数据格式
        if item.get('price'):
            try:
                float(item['price'])
            except ValueError:
                raise DropItem(f"价格格式错误: {item}")
        
        return item
```

---

**需要更多帮助？** 查看 [教程系列](../tutorials/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
