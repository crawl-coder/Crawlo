# 爬虫生命周期

理解爬虫的生命周期有助于正确初始化资源、处理数据和清理连接。

---

## 📊 爬虫生命周期概览

```
创建爬虫 → 打开爬虫 → 执行爬取 → 关闭爬虫
    ↓          ↓          ↓          ↓
 __init__  open_spider   parse()   close_spider
```

---

## 1️⃣ 创建阶段（`__init__`）

### 1.1 爬虫初始化

爬虫实例化时调用 `__init__`：

```python
class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 初始化自定义属性
        self.db_connection = None
        self.item_count = 0
        
        # 从命令行参数获取配置
        self.category = kwargs.get('category', 'default')
```

### 1.2 自定义设置

```python
class MySpider(Spider):
    name = 'myspider'
    
    # 爬虫级配置（覆盖 settings.py）
    custom_settings = {
        'CONCURRENCY': 16,
        'DOWNLOAD_DELAY': 0.5,
        'USER_AGENT': 'MySpider/1.0',
    }
```

### 1.3 命令行参数

```bash
# 传递参数
crawlo run myspider -a category=tech -a pages=10
```

在爬虫中接收：

```python
class MySpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = getattr(self, 'category', 'default')
        self.pages = int(getattr(self, 'pages', 10))
```

---

## 2️⃣ 打开阶段（`open_spider`）

### 2.1 爬虫启动

爬虫开始运行前调用 `open_spider`：

```python
class MySpider(Spider):
    async def open_spider(self):
        """爬虫启动时调用"""
        
        # 1. 初始化数据库连接
        self.db_connection = await create_connection(
            host='localhost',
            port=3306,
            user='root',
            password='password'
        )
        
        # 2. 创建数据表
        await self.db_connection.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                url VARCHAR(500)
            )
        ''')
        
        # 3. 初始化计数器
        self.item_count = 0
        self.error_count = 0
        
        self.logger.info("爬虫已启动，数据库连接成功")
```

### 2.2 资源分配

```python
class MySpider(Spider):
    async def open_spider(self):
        # 打开文件
        self.log_file = open('spider.log', 'w')
        
        # 创建连接池
        self.redis_pool = await aioredis.create_redis_pool(
            'redis://localhost'
        )
        
        # 加载配置
        self.config = await self.load_config()
```

### 2.3 事件监听

```python
from crawlo.event import CrawlerEvent

class MySpider(Spider):
    async def open_spider(self):
        # 订阅响应事件
        async def on_response(response, spider):
            self.logger.info(f"收到响应: {response.url}")
        
        self.crawler.subscriber.subscribe(
            CrawlerEvent.RESPONSE_RECEIVED,
            on_response
        )
        
        # 订阅错误事件
        async def on_error(exception, request, spider):
            self.logger.error(f"请求失败: {request.url}")
        
        self.crawler.subscriber.subscribe(
            CrawlerEvent.SPIDER_ERROR,
            on_error
        )
```

**注意**：Crawlo 使用事件系统而不是 Scrapy 的 signals。
    
    async def on_error(self, failure, request, spider):
        self.logger.error(f"请求失败: {request.url}")
```

---

## 3️⃣ 执行阶段（`parse`）

### 3.1 主要爬取逻辑

`parse()` 方法是爬虫的核心：

```python
class MySpider(Spider):
    async def parse(self, response):
        """解析响应"""
        
        # 1. 提取数据
        items = []
        for element in response.css('div.item'):
            item = {
                'title': element.css('h2::text').get(),
                'url': element.css('a::attr(href)').get(),
                'price': element.css('.price::text').get(),
            }
            items.append(item)
        
        # 2. 返回数据（交给 Pipeline）
        for item in items:
            self.item_count += 1
            yield item
        
        # 3. 提取下一页
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

### 3.2 多回调函数

```python
class MySpider(Spider):
    start_urls = ['https://example.com/list']
    
    async def parse_list(self, response):
        """解析列表页"""
        # 提取详情页链接
        for link in response.css('a.detail::attr(href)').getall():
            yield response.follow(link, callback=self.parse_detail)
        
        # 提取下一页
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_list)
    
    async def parse_detail(self, response):
        """解析详情页"""
        yield {
            'title': response.css('h1::text').get(),
            'content': response.css('.content::text').get(),
            'images': response.css('img::attr(src)').getall(),
        }
```

### 3.3 错误处理

```python
class MySpider(Spider):
    async def parse(self, response):
        try:
            # 正常解析逻辑
            data = response.css('div.data::text').get()
            yield {'data': data}
            
        except Exception as e:
            # 记录错误
            self.error_count += 1
            self.logger.error(f"解析错误: {e}")
            
            # 可以选择重试
            if self.error_count < 3:
                yield Request(response.url, callback=self.parse)
```

---

## 4️⃣ 关闭阶段（`close_spider`）

### 4.1 爬虫关闭

爬虫完成或停止时调用 `close_spider`：

```python
class MySpider(Spider):
    async def close_spider(self, reason):
        """
        爬虫关闭时调用
        
        参数:
            reason: 关闭原因
                - 'finished': 正常完成
                - 'shutdown': 手动停止（Ctrl+C）
                - 'cancelled': 被取消
                - 'error': 错误退出
        """
        
        self.logger.info(f"爬虫关闭，原因: {reason}")
        self.logger.info(f"共抓取 {self.item_count} 条数据")
        self.logger.info(f"共 {self.error_count} 个错误")
        
        # 1. 关闭数据库连接
        if self.db_connection:
            await self.db_connection.close()
            self.logger.info("数据库连接已关闭")
        
        # 2. 关闭文件
        if hasattr(self, 'log_file'):
            self.log_file.close()
            self.logger.info("日志文件已关闭")
        
        # 3. 清理资源
        if hasattr(self, 'redis_pool'):
            self.redis_pool.close()
            await self.redis_pool.wait_closed()
```

### 4.2 保存检查点

```python
class MySpider(Spider):
    async def close_spider(self, reason):
        # 保存检查点（断点续爬）
        if reason in ['shutdown', 'cancelled']:
            checkpoint = {
                'last_url': self.last_url,
                'item_count': self.item_count,
                'timestamp': datetime.now().isoformat(),
            }
            
            await self.save_checkpoint(checkpoint)
            self.logger.info("检查点已保存")
```

### 4.3 发送通知

```python
class MySpider(Spider):
    async def close_spider(self, reason):
        # 发送完成通知
        stats = self.crawler.stats.get_stats()
        
        message = f"""
爬虫: {self.name}
状态: {reason}
数据量: {self.item_count}
错误数: {self.error_count}
耗时: {stats.get('elapsed_time', 0)}s
        """
        
        await self.send_notification(message)
```

---

## 🎯 生命周期钩子

### 完整示例

```python
from crawlo import Spider
from crawlo import Request


class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'CONCURRENCY': 8,
    }
    
    def __init__(self, *args, **kwargs):
        """1. 初始化阶段"""
        super().__init__(*args, **kwargs)
        
        # 初始化属性
        self.db = None
        self.item_count = 0
        self.error_count = 0
        
        # 接收参数
        self.category = kwargs.get('category', 'default')
        
        self.logger.info(f"爬虫初始化，category={self.category}")
    
    async def open_spider(self):
        """2. 打开阶段"""
        # 初始化资源
        self.db = await self.connect_db()
        self.logger.info("数据库连接成功")
    
    async def parse(self, response):
        """3. 执行阶段"""
        try:
            # 提取数据
            items = response.css('div.item').getall()
            
            for item in items:
                data = {
                    'title': item.css('h2::text').get(),
                    'url': item.css('a::attr(href)').get(),
                }
                self.item_count += 1
                yield data
            
            # 跟进下一页
            next_page = response.css('a.next::attr(href)').get()
            if next_page:
                yield response.follow(next_page, callback=self.parse)
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"解析错误: {e}")
    
    async def close_spider(self, reason):
        """4. 关闭阶段"""
        # 清理资源
        if self.db:
            await self.db.close()
            self.logger.info("数据库连接已关闭")
        
        # 打印统计
        self.logger.info(f"爬虫关闭: {reason}")
        self.logger.info(f"数据量: {self.item_count}")
        self.logger.info(f"错误数: {self.error_count}")
```

---

## 📊 生命周期时序图

```
时间线 →

用户启动爬虫
    ↓
框架创建爬虫实例
    ↓
调用 __init__()
    ↓
调用 open_spider()
    ↓
创建起始请求（start_urls）
    ↓
下载请求 → 调用 parse()
    ↓
    ├─ yield Item → Pipeline 处理
    ├─ yield Request → 加入队列
    └─ 无更多请求 → 队列空
    ↓
调用 close_spider(reason)
    ↓
爬虫退出
```

---

## ⚠️ 常见问题

### Q1: `open_spider` 中初始化失败怎么办？

**问题**：数据库连接失败，但爬虫继续运行

**解决方案**：

```python
async def open_spider(self):
    try:
        self.db = await self.connect_db()
    except Exception as e:
        self.logger.error(f"数据库连接失败: {e}")
        raise  # 抛出异常，阻止爬虫启动
```

### Q2: `close_spider` 没有被调用？

**原因**：
- 爬虫被强制杀死（kill -9）
- 进程崩溃

**解决方案**：
- 使用信号处理确保调用
- 定期检查点保存

```python
# settings.py
CHECKPOINT_ENABLED = True
CHECKPOINT_INTERVAL = 300  # 每 5 分钟保存
```

### Q3: 如何在爬虫之间共享资源？

**方案1**: 使用全局单例

```python
# 全局连接池
db_pool = None

class MySpider(Spider):
    async def open_spider(self):
        global db_pool
        if db_pool is None:
            db_pool = await create_pool()
        self.db = db_pool
```

**方案2**: 使用 Redis

```python
# 所有爬虫共享 Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
```

---

## 📚 相关文档

- [请求生命周期](request-lifecycle.md)
- [中间件链](middleware-chain.md)
- [错误处理机制](error-handling.md)
- [检查点系统](checkpoint-guide.md)

---

**需要更多帮助？** 查看 [常见问题](../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
