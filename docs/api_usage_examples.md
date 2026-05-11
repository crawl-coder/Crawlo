# Crawlo API 使用示例

本文档提供 Crawlo 框架的完整 API 使用示例,涵盖从基础到高级的所有场景。

## 目录

- [1. 快速开始](#1-快速开始)
- [2. Request API](#2-request-api)
- [3. Response API](#3-response-api)
- [4. Item API](#4-item-api)
- [5. Spider API](#5-spider-api)
- [6. Pipeline API](#6-pipeline-api)
- [7. Middleware API](#7-middleware-api)
- [8. Queue API](#8-queue-api)
- [9. Settings API](#9-settings-api)
- [10. 高级用法](#10-高级用法)

---

## 1. 快速开始

### 1.1 创建爬虫项目

```bash
# 创建项目
crawlo startproject myproject
cd myproject

# 创建爬虫
crawlo genspider example example.com
```

### 1.2 最小化爬虫示例

```python
# spiders/example_spider.py
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.items import Item


class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['http://example.com']
    
    def parse(self, response):
        """解析响应"""
        # 提取数据
        item = Item()
        item['url'] = response.url
        item['title'] = response.css('title::text').get()
        item['content'] = response.css('body::text').get()
        
        yield item
        
        # 提取链接并跟进
        for link in response.css('a::attr(href)').getall():
            yield Request(link, callback=self.parse)
```

### 1.3 运行爬虫

```bash
# 运行爬虫
crawlo run example

# 调试模式
crawlo run example --loglevel=DEBUG

# 忽略检查点从头开始
crawlo run example --fresh
```

---

## 2. Request API

### 2.1 基础用法

```python
from crawlo.network.request import Request

# 最简单的 GET 请求
request = Request(url='http://example.com')

# POST 请求
request = Request(
    url='http://api.example.com/data',
    method='POST',
    body='{"key": "value"}',
    headers={'Content-Type': 'application/json'},
)
```

### 2.2 高级配置

```python
request = Request(
    url='http://example.com',
    method='GET',
    
    # Headers
    headers={
        'User-Agent': 'MyBot/1.0',
        'Accept': 'application/json',
    },
    
    # Meta 数据 (传递给回调函数)
    meta={
        'page': 1,
        'category': 'news',
        'retry_times': 0,
    },
    
    # 请求参数
    params={'q': 'search', 'page': 1},
    
    # 超时设置 (秒)
    timeout=30,
    
    # 优先级 (-10 到 10, 越高越优先)
    priority=5,
    
    # 代理
    proxy='http://proxy.example.com:8080',
    
    # Cookies
    cookies={'session': 'abc123'},
    
    # 不过滤重复请求
    dont_filter=True,
    
    # 回调函数
    callback=self.parse_detail,
    
    # 错误处理函数
    errback=self.handle_error,
)
```

### 2.3 请求序列化

```python
from crawlo.network.request import Request
from crawlo.utils.request import request_to_dict, request_from_dict

# 创建请求
request = Request(
    url='http://example.com',
    meta={'key': 'value'},
)

# 序列化为字典
request_dict = request_to_dict(request)

# 从字典恢复请求
restored_request = request_from_dict(request_dict, spider=self)
```

### 2.4 请求拷贝

```python
import copy

original = Request(url='http://example.com', meta={'page': 1})

# 浅拷贝
shallow_copy = original.replace(url='http://example.com/page/2')

# 深拷贝
deep_copy = copy.deepcopy(original)
```

---

## 3. Response API

### 3.1 基础用法

```python
def parse(self, response):
    # 基本信息
    print(f"URL: {response.url}")
    print(f"Status: {response.status}")
    print(f"Headers: {response.headers}")
    print(f"Body length: {len(response.text)}")
```

### 3.2 CSS 选择器

```python
def parse(self, response):
    # 获取单个元素
    title = response.css('h1::text').get()
    
    # 获取多个元素
    links = response.css('a::attr(href)').getall()
    
    # 嵌套选择
    for item in response.css('.product'):
        name = item.css('.name::text').get()
        price = item.css('.price::text').get()
    
    # 正则匹配
    emails = response.css('a::text').re(r'[\w.-]+@[\w.-]+\.\w+')
    
    # 提取文本并清理
    text = response.css('p::text').getall()
    clean_text = ' '.join(t.strip() for t in text if t.strip())
```

### 3.3 XPath 选择器

```python
def parse(self, response):
    # 基础 XPath
    title = response.xpath('//h1/text()').get()
    
    # 属性提取
    link = response.xpath('//a/@href').get()
    
    # 条件过滤
    items = response.xpath('//div[@class="product"]')
    
    # 位置过滤
    first_item = response.xpath('//ul/li[1]/text()').get()
    last_item = response.xpath('//ul/li[last()]/text()').get()
```

### 3.4 JSON 响应

```python
def parse_api(self, response):
    # 解析 JSON
    data = response.json()
    
    # 访问数据
    for item in data['results']:
        yield {
            'id': item['id'],
            'name': item['name'],
            'price': item['price'],
        }
    
    # 分页
    if data.get('next_page'):
        yield Request(
            url=data['next_page'],
            callback=self.parse_api,
        )
```

---

## 4. Item API

### 4.1 基础用法

```python
from crawlo.items import Item

def parse(self, response):
    item = Item()
    item['url'] = response.url
    item['title'] = response.css('h1::text').get()
    item['price'] = response.css('.price::text').get()
    item['description'] = response.css('.desc::text').get()
    
    yield item
```

### 4.2 动态字段

```python
from crawlo.items import Item

def parse(self, response):
    item = Item()
    item['url'] = response.url
    
    # 动态添加字段
    for field in response.css('.field'):
        name = field.css('.name::text').get()
        value = field.css('.value::text').get()
        item[name] = value
    
    # 嵌套数据
    item['metadata'] = {
        'scraped_at': datetime.now().isoformat(),
        'spider': self.name,
    }
    
    yield item
```

### 4.3 Item 验证

```python
from crawlo.items import Item

def parse(self, response):
    item = Item()
    item['url'] = response.url
    item['title'] = response.css('h1::text').get()
    
    # 验证必填字段
    if not item.get('title'):
        self.logger.warning(f"Missing title for {response.url}")
        return  # 丢弃该 Item
    
    yield item
```

---

## 5. Spider API

### 5.1 Spider 生命周期

```python
from crawlo.spider import Spider


class MySpider(Spider):
    name = 'myspider'
    
    def start_requests(self):
        """生成初始请求"""
        urls = ['http://example.com/page/1', 'http://example.com/page/2']
        for url in urls:
            yield Request(url, callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        # 提取数据
        item = Item()
        item['url'] = response.url
        yield item
        
        # 生成新请求
        next_page = response.css('.next::attr(href)').get()
        if next_page:
            yield Request(next_page, callback=self.parse)
    
    def closed(self, reason):
        """爬虫关闭时调用"""
        self.logger.info(f"Spider closed: {reason}")
```

### 5.2 多回调函数

```python
class MultiCallbackSpider(Spider):
    name = 'multi_callback'
    
    def start_requests(self):
        yield Request('http://example.com/list', callback=self.parse_list)
    
    def parse_list(self, response):
        """解析列表页"""
        for link in response.css('.item a::attr(href)').getall():
            yield Request(
                url=link,
                callback=self.parse_detail,
            )
    
    def parse_detail(self, response):
        """解析详情页"""
        item = Item()
        item['title'] = response.css('h1::text').get()
        item['content'] = response.css('.content::text').get()
        yield item
        
        # 解析评论
        yield Request(
            url=response.url + '/comments',
            callback=self.parse_comments,
        )
    
    def parse_comments(self, response):
        """解析评论"""
        for comment in response.css('.comment'):
            yield {
                'author': comment.css('.author::text').get(),
                'text': comment.css('.text::text').get(),
            }
```

### 5.3 错误处理

```python
class ErrorHandlingSpider(Spider):
    name = 'error_handler'
    
    def start_requests(self):
        yield Request(
            url='http://example.com',
            callback=self.parse,
            errback=self.handle_error,
        )
    
    def parse(self, response):
        yield {'url': response.url, 'status': response.status}
    
    def handle_error(self, failure):
        """处理请求失败"""
        self.logger.error(f"Request failed: {failure.value}")
        
        # 访问失败的请求
        request = failure.request
        self.logger.error(f"Failed URL: {request.url}")
        
        # 重试逻辑
        if request.meta.get('retry_times', 0) < 3:
            request.meta['retry_times'] += 1
            yield request
```

---

## 6. Pipeline API

### 6.1 基础 Pipeline

```python
from crawlo.pipelines import BasePipeline


class MyPipeline(BasePipeline):
    """自定义 Pipeline"""
    
    def open_spider(self, spider):
        """Spider 打开时调用"""
        self.file = open('output.json', 'w')
        self.logger.info("Spider opened")
    
    def process_item(self, item, spider):
        """处理每个 Item"""
        # 数据清洗
        if 'title' in item:
            item['title'] = item['title'].strip()
        
        # 数据验证
        if not item.get('url'):
            raise DropItem(f"Missing url in {item}")
        
        # 写入文件
        self.file.write(str(item) + '\n')
        
        return item
    
    def close_spider(self, spider):
        """Spider 关闭时调用"""
        self.file.close()
        self.logger.info("Spider closed")
```

### 6.2 数据库 Pipeline

```python
from crawlo.pipelines import DatabasePipeline


class MongoPipeline(DatabasePipeline):
    """MongoDB Pipeline"""
    
    def get_connection(self):
        """获取数据库连接"""
        from pymongo import MongoClient
        
        return MongoClient(
            host=self.settings.get('MONGO_HOST', 'localhost'),
            port=self.settings.get('MONGO_PORT', 27017),
        )
    
    def process_item(self, item, spider):
        """保存 Item 到 MongoDB"""
        collection = self.db[spider.name]
        collection.insert_one(dict(item))
        return item
```

### 6.3 Pipeline 配置

```python
# settings.py
ITEM_PIPELINES = {
    'myproject.pipelines.DataCleanPipeline': 100,  # 优先级 100 (先执行)
    'myproject.pipelines.ValidationPipeline': 200,
    'myproject.pipelines.MongoPipeline': 300,      # 优先级 300 (后执行)
}
```

---

## 7. Middleware API

### 7.1 Downloader Middleware

```python
from crawlo.middleware import BaseDownloaderMiddleware


class CustomDownloaderMiddleware(BaseDownloaderMiddleware):
    """自定义下载中间件"""
    
    def process_request(self, request, spider):
        """处理请求"""
        # 添加代理
        request.meta['proxy'] = 'http://proxy.example.com:8080'
        
        # 修改 headers
        request.headers['Custom-Header'] = 'value'
        
        # 返回 None 继续处理
        return None
    
    def process_response(self, request, response, spider):
        """处理响应"""
        # 检查响应
        if response.status == 404:
            # 丢弃响应
            return response
        
        # 修改响应
        # ...
        
        return response
    
    def process_exception(self, request, exception, spider):
        """处理异常"""
        self.logger.error(f"Request failed: {exception}")
        return None  # 继续处理异常
```

### 7.2 Spider Middleware

```python
from crawlo.middleware import BaseSpiderMiddleware


class CustomSpiderMiddleware(BaseSpiderMiddleware):
    """自定义爬虫中间件"""
    
    def process_spider_input(self, response, spider):
        """响应进入 Spider 前调用"""
        return None
    
    def process_spider_output(self, response, result, spider):
        """Spider 输出时调用"""
        for item in result:
            # 过滤或修改输出
            yield item
    
    def process_spider_exception(self, response, exception, spider):
        """Spider 异常时调用"""
        return None
```

### 7.3 Middleware 配置

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    'myproject.middleware.ProxyMiddleware': 100,
    'myproject.middleware.UserAgentMiddleware': 200,
}

SPIDER_MIDDLEWARES = {
    'myproject.middleware.DepthMiddleware': 100,
}
```

---

## 8. Queue API

### 8.1 内存队列

```python
from crawlo.queue.memory_queue import SpiderPriorityQueue
import asyncio


async def use_memory_queue():
    """使用内存优先级队列"""
    queue = SpiderPriorityQueue(maxsize=10000)
    
    # 放入请求
    for i in range(100):
        priority = i % 10
        request = Request(url=f'http://example.com/page/{i}')
        await queue.put((priority, request))
    
    # 取出请求 (按优先级)
    while not queue.empty():
        priority, request = await queue.get()
        print(f"Processing: {request.url} (priority: {priority})")
        queue.task_done()
```

### 8.2 Redis 队列

```python
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
import asyncio


async def use_redis_queue():
    """使用 Redis 分布式队列"""
    queue = RedisPriorityQueue(
        project_name='myproject',
        spider_name='myspider',
        redis_url='redis://localhost:6379',
    )
    
    # 连接 Redis
    await queue.connect()
    
    # 放入请求
    for i in range(100):
        request = Request(url=f'http://example.com/page/{i}')
        await queue.push(request, priority=0)
    
    # 获取队列大小
    size = await queue.size()
    print(f"Queue size: {size}")
    
    # 取出请求
    while await queue.size() > 0:
        request = await queue.pop()
        print(f"Processing: {request.url}")
    
    # 关闭连接
    await queue.close()
```

### 8.3 Queue Manager

```python
from crawlo.queue.queue_manager import QueueManager
import asyncio


async def use_queue_manager():
    """使用队列管理器"""
    manager = QueueManager(
        project_name='myproject',
        spider_name='myspider',
        queue_type='memory',  # 或 'redis'
    )
    
    # 初始化
    await manager.initialize()
    
    # 放入请求
    request = Request(url='http://example.com')
    await manager.put(request)
    
    # 获取队列大小
    size = await manager.size()
    
    # 取出请求
    request = await manager.get()
    
    # 清空队列
    await manager.clear()
    
    # 关闭
    await manager.close()
```

---

## 9. Settings API

### 9.1 读取配置

```python
# 在 Spider 中
class MySpider(Spider):
    def parse(self, response):
        # 读取配置
        timeout = self.settings.get('DOWNLOAD_TIMEOUT', 30)
        retry_times = self.settings.getint('RETRY_TIMES', 3)
        enabled = self.settings.getbool('PROXY_ENABLED', False)
        
        # 或使用辅助函数
        from crawlo.utils.misc import safe_get_config
        value = safe_get_config(
            self.settings,
            'CUSTOM_SETTING',
            default='default_value',
            expected_type=str,
        )
```

### 9.2 配置优先级

配置优先级 (从高到低):
1. Spider 属性 (`custom_settings`)
2. 命令行参数
3. 项目配置文件 (`settings.py`)
4. 默认配置

```python
class MySpider(Spider):
    name = 'myspider'
    
    # 最高优先级
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RETRY_TIMES': 5,
    }
```

---

## 10. 高级用法

### 10.1 异步爬虫

```python
class AsyncSpider(Spider):
    name = 'async_spider'
    
    async def parse(self, response):
        """异步解析"""
        # 异步 HTTP 请求
        async with aiohttp.ClientSession() as session:
            async with session.get('http://api.example.com/data') as resp:
                data = await resp.json()
                yield data
        
        # 异步数据库操作
        await db.insert_one(dict(item))
        
        # 并发请求
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.fetch(url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        for result in results:
            yield result
    
    async def fetch(self, url):
        """异步抓取"""
        # ...
```

### 10.2 分布式爬虫

```python
# settings.py
# 启用 Redis 队列
QUEUE_TYPE = 'redis'
REDIS_HOST = 'redis-cluster.example.com'
REDIS_PORT = 6379

# 启用分布式去重
DUPEFILTER_CLASS = 'crawlo.filters.RedisDupeFilter'

# 多个爬虫实例共享 Redis
```

### 10.3 自定义扩展

```python
from crawlo.extension import BaseExtension


class MyExtension(BaseExtension):
    """自定义扩展"""
    
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal='spider_opened')
        crawler.signals.connect(ext.spider_closed, signal='spider_closed')
        return ext
    
    def spider_opened(self, spider):
        spider.logger.info("Extension: Spider opened")
    
    def spider_closed(self, spider):
        spider.logger.info("Extension: Spider closed")


# settings.py
EXTENSIONS = {
    'myproject.extensions.MyExtension': 500,
}
```

### 10.4 Shell 调试

```bash
# 启动 Shell
crawlo shell http://example.com

# 在 Shell 中测试
>>> response.css('h1::text').get()
>>> fetch('http://example.com/page/2')
>>> view(response)  # 在浏览器中打开
```

---

## 相关资源

- [官方文档](https://crawlo.readthedocs.io/)
- [GitHub 仓库](https://github.com/yourusername/crawlo)
- [示例项目](https://github.com/yourusername/crawlo/examples)
- [问题反馈](https://github.com/yourusername/crawlo/issues)
