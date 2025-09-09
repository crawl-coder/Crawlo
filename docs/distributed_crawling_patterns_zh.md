# 分布式爬虫模式详解

在 Crawlo 框架中，分布式爬虫可以应用于不同的数据采集场景。本文档将详细介绍两种主要的分布式爬虫模式及其技术实现。

## 1. 列表页直接获取数据模式

### 场景描述
在这种模式下，API 或网页列表页直接返回完整的数据，无需访问详情页。这是您当前电信设备许可证项目的情况。

### 技术优势
1. **高并发处理**：多个节点可以并行处理不同的页面
2. **负载均衡**：请求自动分配给空闲节点
3. **容错性**：节点故障不影响整体任务
4. **去重机制**：避免重复处理相同页面

### 配置要点
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# 高并发配置
CONCURRENCY = 32
DOWNLOAD_DELAY = 0.5
```

### 示例代码
```python
class ListOnlySpider(Spider):
    name = 'list_only'
    start_page = 1
    end_page = 1000
    
    def start_requests(self):
        """一次性生成所有页面请求"""
        for page in range(self.start_page, self.end_page + 1):
            yield Request(
                url=f'https://api.example.com/data?page={page}',
                callback=self.parse,
                meta={'page': page},
                dont_filter=False  # 启用去重
            )
    
    def parse(self, response):
        """直接从列表页提取完整数据"""
        data_list = response.json().get('data', [])
        for item_data in data_list:
            item = MyItem()
            item['field1'] = item_data['field1']
            item['field2'] = item_data['field2']
            # ... 其他字段
            yield item
```

### 启动方式
```bash
# 启动 Redis
redis-server

# 启动多个节点
# 终端1
python run.py list_only

# 终端2
python run.py list_only --concurrency 32

# 终端3
python run.py list_only --concurrency 24
```

## 2. 传统列表-详情页模式

### 场景描述
在这种模式下，需要先解析列表页获取详情页链接，然后访问详情页提取完整数据。

### 技术优势
1. **深度数据采集**：可以获取更详细的页面信息
2. **分布式去重**：避免重复访问相同的详情页
3. **任务协调**：多个节点协同处理列表页和详情页请求
4. **扩展性**：支持复杂的页面结构和数据提取逻辑

### 配置要点
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# 适度并发配置（详情页可能需要更多处理时间）
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
```

### 示例代码
```python
class ListDetailSpider(Spider):
    name = 'list_detail'
    start_urls = ['https://example.com/list']
    
    def parse(self, response):
        """解析列表页，提取详情页链接"""
        # 提取详情页链接
        detail_links = response.css('.item-link::attr(href)').getall()
        
        for link in detail_links:
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_detail,
                dont_filter=False  # 启用去重
            )
        
        # 处理分页
        next_page = response.css('.next-page::attr(href)').get()
        if next_page:
            yield Request(
                url=response.urljoin(next_page),
                callback=self.parse
            )
    
    def parse_detail(self, response):
        """解析详情页，提取完整数据"""
        item = MyItem()
        item['title'] = response.css('h1.title::text').get()
        item['content'] = response.css('.content::text').get()
        item['price'] = response.css('.price::text').get()
        # ... 其他字段
        
        yield item
```

### 启动方式
```bash
# 启动 Redis
redis-server

# 启动多个节点
# 终端1
python run.py list_detail

# 终端2
python run.py list_detail --concurrency 16

# 终端3
python run.py list_detail --concurrency 12
```

## 两种模式的对比

| 特性 | 列表页直接获取数据 | 传统列表-详情页模式 |
|------|-------------------|-------------------|
| 数据完整性 | 列表页已包含完整数据 | 需要详情页补充数据 |
| 并发效率 | 高（请求简单） | 中等（请求复杂） |
| 网络开销 | 低 | 高（更多请求） |
| 实现复杂度 | 简单 | 复杂 |
| 适用场景 | API数据采集、简单列表 | 复杂页面结构、深度信息 |

## 最佳实践

### 1. 列表页模式最佳实践
- 一次性生成所有页面请求
- 合理设置并发数（通常可以设置较高）
- 启用去重机制避免重复处理
- 监控请求频率，避免对服务器造成压力

### 2. 列表-详情页模式最佳实践
- 在列表页解析时就进行初步去重
- 合理设置延迟，避免被反爬虫机制封禁
- 使用中间件处理登录状态或Cookie
- 实现错误重试机制

## 配置优化建议

### Redis 配置
```python
# settings.py
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2
SCHEDULER_QUEUE_NAME = 'my_spider:requests'
REDIS_KEY = 'my_spider:fingerprint'
```

### 性能调优
```python
# settings.py
CONNECTION_POOL_LIMIT = 100
CONNECTION_POOL_LIMIT_PER_HOST = 30
MAX_RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504]
```

## 监控和调试

### 查看队列状态
```bash
# 查看请求队列长度
redis-cli llen my_spider:requests

# 查看去重集合大小
redis-cli scard my_spider:fingerprint
```

### 日志监控
```python
# settings.py
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/distributed_spider.log'
```

通过合理选择和配置这两种分布式爬虫模式，您可以根据具体的数据采集需求实现高效的分布式数据抓取。