# 去重机制详解

在 Crawlo 框架中，存在两种不同层面的去重机制：

## 1. 请求去重 (Request Deduplication)

### 机制说明
请求去重是 Crawlo 框架内置的功能，主要防止重复发送相同的请求。

### 工作原理
```python
# 在框架内部自动处理
from crawlo.utils.request import request_fingerprint

# 基于请求的 URL、方法、参数等生成指纹
fingerprint = request_fingerprint(request)

# 在 Redis 中存储已见过的请求指纹
redis_client.sadd('requests_seen', fingerprint)
```

### 适用场景
- 防止重复爬取相同的页面
- 节省网络带宽和服务器资源
- 提高爬取效率

### 配置示例
```python
# settings.py
DUPEFILTER_CLASS = 'crawlo.dupefilters.RedisDupeFilter'
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'
```

## 2. 数据项去重 (Item Deduplication)

### 机制说明
数据项去重是在数据管道中实现的，主要防止保存重复的数据结果。

### 工作原理
```python
# 在数据管道中处理
class RedisDeduplicationPipeline:
    def process_item(self, item, spider):
        # 基于数据项的关键字段生成指纹
        fingerprint = self._generate_item_fingerprint(item)
        
        # 检查数据项是否已存在
        is_new = redis_client.sadd('items_seen', fingerprint)
        
        if not is_new:
            # 丢弃重复的数据项
            raise DropItem(f"Duplicate item: {fingerprint}")
        else:
            # 保存新数据项
            return item
```

### 适用场景
- 防止保存重复的数据记录
- 确保数据结果的唯一性
- 在分布式环境中协调多个节点的数据去重

## 两种去重机制的对比

| 特性 | 请求去重 | 数据项去重 |
|------|----------|------------|
| 作用层面 | 网络请求 | 解析结果 |
| 去重时机 | 发送请求前 | 保存数据前 |
| 去重依据 | URL、方法、参数 | 数据项关键字段 |
| 性能影响 | 减少网络请求 | 减少数据存储 |
| 配置方式 | 框架内置 | 管道配置 |

## 实际应用示例

### 场景1：列表页直接获取数据
```python
class ApiDataSpider(Spider):
    def start_requests(self):
        # 生成所有页面请求
        for page in range(1, 1000):
            yield Request(
                url=f'https://api.example.com/data?page={page}',
                callback=self.parse
            )
    
    def parse(self, response):
        data_list = response.json().get('data', [])
        for item_data in data_list:
            item = ApiDataItem()
            item['id'] = item_data['id']
            item['name'] = item_data['name']
            # 请求去重防止重复访问相同页面
            # 数据项去重防止保存重复记录
            yield item
```

### 场景2：列表-详情页模式
```python
class ListDetailSpider(Spider):
    def parse(self, response):
        # 从列表页提取详情页链接
        detail_links = response.css('.item-link::attr(href)').getall()
        for link in detail_links:
            # 请求去重防止重复访问相同详情页
            yield Request(url=link, callback=self.parse_detail)
    
    def parse_detail(self, response):
        item = MyItem()
        item['title'] = response.css('h1::text').get()
        # 数据项去重防止保存重复的详情数据
        yield item
```

## 推荐使用策略

### 仅使用请求去重
适用于：
- 列表页直接获取完整数据的场景
- 每个请求对应唯一数据的场景
- 对数据重复性要求不高的场景

### 同时使用两种去重
适用于：
- 需要确保数据结果绝对唯一的场景
- 多个请求可能返回相同数据的场景
- 分布式环境中需要协调数据去重的场景

通过合理组合使用这两种去重机制，可以构建高效且可靠的分布式爬虫系统。