# Crawlo 核心组件 API 文档

> Crawlo 分布式爬虫框架核心组件 API 参考

## 目录

- [异常体系](#异常体系)
- [错误分类](#错误分类)
- [Engine 引擎](#engine-引擎)
- [TaskManager 任务管理](#taskmanager-任务管理)
- [MiddlewareManager 中间件管理](#middlewaremanager-中间件管理)
- [StatsCollector 统计收集](#statscollector-统计收集)

---

## 异常体系

### CrawloException

框架基础异常类，所有框架异常的基类。

```python
from crawlo.exceptions import CrawloException
```

**属性**:
- `message: str` - 异常消息

**示例**:
```python
try:
    # 爬虫代码
    pass
except CrawloException as e:
    print(f"框架异常: {e.message}")
```

### 异常分类

| 异常类 | 说明 | 使用场景 |
|--------|------|----------|
| `SpiderException` | 爬虫相关异常 | 爬虫实例化失败、类型错误 |
| `ComponentInitException` | 组件初始化异常 | 中间件/管道/扩展初始化失败 |
| `DataException` | 数据处理异常 | Item 验证错误、数据丢弃 |
| `RequestException` | 请求/响应异常 | 下载失败、重试耗尽 |
| `OutputException` | 输出异常 | 输出类型错误 |
| `ConfigException` | 配置异常 | 配置缺失、配置错误 |
| `ScheduleException` | 调度异常 | 队列满、队列空 |
| `DetailedException` | 详细错误异常 | 带上下文的错误 |

### 常用异常

#### DownloadError

下载错误，包含 URL 和状态码信息。

```python
from crawlo.exceptions import DownloadError

raise DownloadError(
    message="Connection timeout",
    url="https://example.com",
    status_code=504
)
```

#### IgnoreRequestError

请求被忽略，用于流程控制。

```python
from crawlo.exceptions import IgnoreRequestError

raise IgnoreRequestError("Offsite request filtered")
```

#### ItemDiscard / DropItem

Item 被丢弃，用于去重等场景。

```python
from crawlo.exceptions import ItemDiscard

raise ItemDiscard("Duplicate item")
# 或使用别名
from crawlo.exceptions import DropItem
raise DropItem("Duplicate item")
```

---

## 错误分类

### ErrorClassifier

错误分类器，用于判断错误类型和重试策略。

```python
from crawlo.core.error_types import ErrorClassifier
```

**方法**:

#### is_critical(error: Exception) -> bool

判断是否为关键错误（需要立即停止爬虫）。

```python
if ErrorClassifier.is_critical(error):
    self.logger.critical("关键错误，停止爬虫")
    raise
```

#### is_network_error(error: Exception) -> bool

判断是否为网络错误（通常可重试）。

```python
if ErrorClassifier.is_network_error(error):
    return await self.retry_request(request)
```

#### should_retry(error: Exception) -> bool

判断错误是否应该重试。

```python
if ErrorClassifier.should_retry(error):
    return await self.retry(request)
```

#### get_error_category(error: Exception) -> str

获取错误分类名称。

```python
category = ErrorClassifier.get_error_category(error)
# 返回: 'critical', 'network', 'data', 'resource', 'unknown'
```

---

## Engine 引擎

Engine 是 Crawlo 框架的核心协调器，负责管理整个爬取流程。

### 初始化

```python
from crawlo.core.engine import Engine

engine = Engine(crawler)
```

**配置参数**:

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CONCURRENCY` | int | 8 | 并发数 |
| `DEPTH_PRIORITY` | int | 1 | 深度优先级调整系数。正数=深度优先（详情页优先），负数=广度优先（列表页优先），0=不调整 |
| `SCHEDULER_MAX_QUEUE_SIZE` | int | 200 | 调度器队列最大大小 |
| `REQUEST_GENERATION_BATCH_SIZE` | int | 10 | 请求生成批处理大小 |
| `REQUEST_GENERATION_INTERVAL` | float | 0.01 | 请求生成间隔（秒） |
| `BACKPRESSURE_RATIO` | float | 0.9 | 背压触发比例 |
| `ENABLE_CONTROLLED_REQUEST_GENERATION` | bool | False | 启用受控请求生成 |

### 关键方法

#### async start_spider(spider, resume=True)

启动爬虫。

```python
await engine.start_spider(spider, resume=True)
```

**参数**:
- `spider: Spider` - 爬虫实例
- `resume: bool` - 是否从检查点恢复

#### async crawl()

主爬取循环。

```python
await engine.crawl()
```

#### async close_spider(reason='finished')

关闭爬虫。

```python
await engine.close_spider(reason='finished')
```

**参数**:
- `reason: str` - 关闭原因（'finished' 或 'shutdown'）

### 并发统计

Engine 在关闭时会自动输出并发统计：

```python
{
    'concurrency_limit': 12,           # 配置并发
    'max_concurrent_seen': 12,         # 峰值并发
    'concurrency_utilization': 100.0,  # 利用率 %
    'avg_response_time_ms': 1000.0,    # 平均响应时间
}
```

---

## TaskManager 任务管理

TaskManager 统一管理异步任务的创建、执行和监控。

### 初始化

```python
from crawlo.core.task_manager import TaskManager

task_manager = TaskManager(total_concurrency=8)
```

**参数**:
- `total_concurrency: int` - 最大并发数

### 关键方法

#### async create_task(coroutine, timeout=None) -> Task

创建受控的异步任务。

```python
task = await task_manager.create_task(
    coroutine=my_coroutine(),
    timeout=30.0  # 可选超时时间
)
```

**参数**:
- `coroutine` - 协程对象
- `timeout: float` - 任务超时时间（秒）

**返回**:
- `asyncio.Task` - 任务对象

#### all_done() -> bool

检查所有任务是否完成。

```python
if task_manager.all_done():
    print("所有任务已完成")
```

#### record_response_time(response_time: float)

记录响应时间，用于动态调整并发数。

```python
task_manager.record_response_time(response_time=1.5)
```

#### get_stats() -> Dict

获取任务管理器统计信息。

```python
stats = task_manager.get_stats()
print(stats)
# {
#     'concurrency_limit': 8,
#     'max_concurrent_seen': 6,
#     'concurrency_utilization': 75.0,
#     'avg_response_time': 1.2,
#     'total_tasks': 100,
#     'active_tasks': 6,
# }
```

---

## MiddlewareManager 中间件管理

MiddlewareManager 管理中间件的生命周期和执行。

### 初始化

```python
from crawlo.middleware.middleware_manager import MiddlewareManager

middleware_manager = MiddlewareManager(crawler)
```

### 生命周期方法

#### async open()

初始化所有中间件。

```python
await middleware_manager.open()
```

**功能**:
- 调用每个中间件的 `open()` 方法（如果存在）
- 支持同步和异步方法

#### async close()

关闭所有中间件。

```python
await middleware_manager.close()
```

**功能**:
- 反向关闭中间件（与初始化顺序相反）
- 调用每个中间件的 `close()` 方法（如果存在）

### 中间件开发指南

#### 基础中间件

```python
from crawlo.middleware import BaseMiddleware

class MyMiddleware(BaseMiddleware):
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)
    
    async def open(self):
        """初始化资源"""
        self.connection = await create_connection()
    
    async def process_request(self, request):
        """处理请求"""
        request.headers['X-Custom'] = 'value'
        return request
    
    async def process_response(self, request, response):
        """处理响应"""
        return response
    
    async def close(self):
        """清理资源"""
        await self.connection.close()
```

---

## StatsCollector 统计收集

StatsCollector 收集和管理爬虫统计信息。

### 初始化

```python
from crawlo.stats.collector import StatsCollector

stats = StatsCollector(crawler)
```

### 关键方法

#### inc_value(key: str, count: int = 1, start: int = 0)

增加统计值。

```python
stats.inc_value('request_count', count=1)
stats.inc_value('error_count', count=1, start=0)
```

#### get_value(key: str, default=None) -> Any

获取统计值。

```python
count = stats.get_value('request_count', default=0)
```

#### get_stats() -> Dict

获取所有统计信息。

```python
all_stats = stats.get_stats()
```

#### close_spider(spider, reason: str)

爬虫关闭时记录信息。

```python
stats.close_spider(spider, reason='finished')
```

**自动记录的指标**:
- `spider_name` - 爬虫名称
- `reason` - 关闭原因
- `start_time` - 开始时间
- `end_time` - 结束时间
- `elapsed_time` - 耗时
- `items_per_minute` - 每分钟处理 Item 数
- `pages_per_minute` - 每分钟处理页面数
- `concurrency_limit` - 配置并发数
- `max_concurrent_seen` - 峰值并发数
- `concurrency_utilization` - 并发利用率
- `avg_response_time_ms` - 平均响应时间（毫秒）

### 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `STATS_DUMP` | bool | True | 是否在关闭时输出统计 |
| `STATS_CLASS` | str | - | 统计后端类路径 |

---

## 使用示例

### 完整爬虫示例

```python
from crawlo import Crawler
from crawlo.spider import Spider
from crawlo import Request, Item

class MySpider(Spider):
    name = 'my_spider'
    start_urls = ['https://example.com']
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)
    
    def parse(self, response):
        # 解析数据
        item = MyItem()
        item['title'] = response.css('h1::text').get()
        yield item

# 运行爬虫
crawler = Crawler(MySpider)
crawler.crawl()
```

### 错误处理示例

```python
from crawlo.core.error_types import ErrorClassifier

async def process_request(request):
    try:
        response = await download(request)
        return response
    except Exception as e:
        if ErrorClassifier.is_critical(e):
            # 关键错误，停止爬虫
            raise
        elif ErrorClassifier.should_retry(e):
            # 网络错误，重试
            return await retry(request)
        else:
            # 其他错误，记录日志
            logger.error(f"Request failed: {e}")
            return None
```

### 中间件示例

```python
from crawlo.middleware import BaseMiddleware

class CustomMiddleware(BaseMiddleware):
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)
    
    async def open(self):
        # 初始化
        self.cache = {}
    
    async def process_request(self, request):
        # 添加自定义头
        request.headers['X-API-Key'] = 'xxx'
        return request
    
    async def close(self):
        # 清理
        self.cache.clear()
```

---

## 版本信息

- **当前版本**: v0.2.0
- **发布日期**: 2026-04-19
- **Python 版本**: >= 3.8

## 更多信息

- [架构文档](../../concepts/architecture.md)
- [配置指南](../../guides/configuration/index.md)
- [实战案例](../../examples/index.md)
