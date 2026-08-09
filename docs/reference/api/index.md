# Crawlo 核心组件 API 文档

> Crawlo 分布式爬虫框架核心组件 API 参考

## 目录

- [异常体系](#异常体系)
- [错误分类](#错误分类)
- [Engine 引擎](#engine-引擎)
- [TaskManager 任务管理](#taskmanager-任务管理)
- [MiddlewareManager 中间件管理](#middlewaremanager-中间件管理)
- [StatsCollector 统计收集](#statscollector-统计收集)
- [下载器（Downloaders）](#下载器downloaders)
- [队列（Queues）](#队列queues)
- [管道（Pipelines）](#管道pipelines)
- [扩展（Extensions）](#扩展extensions)
- [配置（Configuration）](#配置configuration)
- [通知（Notifications）](#通知notifications)

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
from crawlo.core.errors import ErrorClassifier
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
from crawlo.core.errors import ErrorClassifier

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

## 下载器（Downloaders）

下载器负责把 `Request` 转成 `Response`。框架内置多协议 + 多浏览器引擎，统一通过 `DOWNLOADER` 配置或 `HybridDownloader` 自动路由。

**基类**：`crawlo.downloader.DownloaderBase`

```python
from crawlo.downloader import DownloaderBase
```

下载器核心方法：

| 方法 | 说明 |
|---|---|
| `open()` | 打开下载器（可选） |
| `download(request)` | 下载请求，返回 `Response` 或 `None` |
| `close()` | 关闭下载器、释放浏览器/连接资源 |

**内置下载器**：

| 下载器 | 定位 |
|---|---|
| `AioHttpDownloader` | 默认 aiohttp 下载器，RingBuffer 统计 p99 响应时间 |
| `HttpXDownloader` | httpx 下载器，支持 HTTP/2 + 分层超时 |
| `CurlCffiDownloader` | curl-cffi 下载器，JA3/TLS 指纹模拟 |
| `PlaywrightDownloader` | Playwright 浏览器引擎，单浏览器多标签页池 |
| `CloakBrowserDownloader` / `CamoufoxDownloader` / `DrissionPageDownloader` | 隐身浏览器引擎 |
| `HybridDownloader` | 5 级检测路由（meta → URL 正则 → 域名 → 扩展名 → 默认） |

**扩展点（P3-2）**：

```python
from crawlo.downloader import register_downloader, unregister_downloader

register_downloader('my_downloader', MyDownloader)
# settings: DOWNLOADER = 'my_downloader'
```

---

## 队列（Queues）

统一入口 `crawlo.queue.QueueManager`，按 `QUEUE_TYPE` 自动选择后端；支持内存 / Redis 优先级队列 / Redis Stream 三种后端，外加背压控制。

```python
from crawlo.queue import QueueManager, QueueConfig, QueueType

config = QueueConfig(queue_type='memory', max_queue_size=1000)
manager = QueueManager(config)
await manager.initialize()
await manager.put(request)
request = await manager.get_blocking(timeout=30)
```

**后端**：

| 后端 | 类 | 说明 |
|---|---|---|
| 内存 | `SpiderPriorityQueue` | asyncio 优先级队列，`maxsize=0` 无限制 |
| Redis | `RedisPriorityQueue` | ZSET 排序，支持集群连接池 |
| Redis Stream | `RedisStreamQueue` | 消费组 + ACK/NACK + 心跳 + 故障转移 + DLQ |
| 磁盘 | `DiskQueue` | 磁盘持久化队列 |

**扩展点（P3-2）**：

```python
from crawlo.queue import register_queue_backend

async def build_my_queue(manager):
    return MyQueue(manager)

register_queue_backend(QueueType.MEMORY, build_my_queue)  # 覆盖内置后端
```

**任务追踪**：`crawlo.queue.task_tracker.TaskTracker` / `TaskResult`（RETRY / DEAD_LETTER / ACK）。

---

## 管道（Pipelines）

统一入口 `crawlo.pipelines.PipelineManager`；单条管道继承 `BasePipeline`，推荐基于 `ResourceManagedPipeline` 实现。

```python
from crawlo.pipelines.base_pipeline import BasePipeline, ResourceManagedPipeline
```

**通用模板**：

| 类 | 说明 |
|---|---|
| `GenericSQLPipeline` | 数据库无关的 SQL 管道基类（子类实现 `_initialize_pool`/`_do_insert` 等） |
| `GenericDocumentPipeline` | 文档型存储管道基类 |
| `MemoryDedupPipeline` / `RedisDedupPipeline` / `BloomDedupPipeline` | 去重管道 |

**错误分类**：`crawlo.utils.db.pipeline_utils.ErrorClassifier`（`is_skipable` / `is_retryable` / `extract_error_code`）。

---

## 扩展（Extensions）

扩展通过事件驱动（声明方法即订阅）接入引擎生命周期。监控类扩展继承 `BaseMonitorExtension`（`crawlo.extensions.monitor.base`），自带注册到 `MonitorManager` 的能力。

```python
from crawlo.extensions.health_check import HealthCheckExtension
from crawlo.extensions.monitor.performance_monitor import PerformanceMonitor
from crawlo.extensions.monitor.monitor_manager import get_monitor_manager
```

内置扩展：事件循环延迟探针（`PerformanceMonitor`）、健康检查（`HealthCheckExtension`）、背压监控、告警去重、请求录制（`RequestRecorder`，JSONL + 文件轮转）。

---

## 配置（Configuration）

**SettingManager**（`crawlo.settings.setting_manager`）：`MutableMapping` 风格配置容器，支持类型安全读取。

```python
from crawlo.settings.setting_manager import SettingManager

s = SettingManager()
s.set('CONCURRENCY', 8)
s.get_int('CONCURRENCY')
```

**CrawloConfig**（`crawlo.core.config.CrawloConfig`）：配置工厂，提供 `standalone()` / `auto()` / `distributed()` 三种运行模式与链式 `set()`。

```python
from crawlo.core.config import CrawloConfig

config = CrawloConfig.distributed(project_name='my_project', concurrency=16)
settings = config.to_dict()
```

**安全读取**：`crawlo.utils.misc.safe_get_config(settings, key, default, value_type)`。

---

## 通知（Notifications）

统一入口 `NotificationDispatcher`（`crawlo.extensions.notifications.core.notifier`），支持钉钉 / 飞书 / 企业微信 / 邮件 / 短信 5 个渠道，内置消息去重与 30+ 模板。

```python
from crawlo.extensions.notifications import get_notifier
from crawlo.extensions.notifications.core.models import NotificationMessage

notifier = get_notifier()
resp = notifier.send_notification(
    NotificationMessage(title='爬虫完成', content='抓取 100 条数据')
)
```

渠道类：`crawlo.extensions.notifications.channels.{dingtalk,feishu,wecom,email,sms}`。注意：短信渠道当前为文档化模拟实现，接入真实服务商需自行实现（见 P3 跟踪项）。

---

## 版本信息

- **当前版本**: v1.7.3
- **发布日期**: 2026-08-10
- **Python 版本**: >= 3.8

## 更多信息

- [架构文档](../../concepts/architecture.md)
- [配置指南](../../guides/configuration/index.md)
- [实战案例](../../examples/index.md)
