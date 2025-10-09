# API 参考

欢迎查阅 Crawlo 框架的完整 API 参考文档。本文档详细介绍了框架中各个模块和类的使用方法。

## 核心模块

### [crawlo.crawler](crawlo_crawler.md)
爬虫进程管理和运行时核心功能模块。

核心类：
- `Crawler` - 单个爬虫运行实例
- `CrawlerProcess` - 爬虫进程管理器

### [crawlo.spider](crawlo_spider___init__.md)
爬虫基类和相关功能模块。

核心类：
- `Spider` - 爬虫基类
- `SpiderMeta` - 爬虫元类

## 网络模块

### [crawlo.network.request](crawlo_network_request.md)
HTTP 请求对象实现。

核心类：
- `Request` - 请求对象

### [crawlo.network.response](crawlo_network_response.md)
HTTP 响应对象实现。

核心类：
- `Response` - 响应对象

## 数据处理模块

### [crawlo.items](crawlo_items_items.md)
数据项定义和处理。

核心类：
- `Item` - 数据项基类
- `ItemMeta` - 数据项元类

## 下载器模块

### [crawlo.downloader](crawlo_downloader___init__.md)
HTTP 客户端下载器实现。

核心类：
- `DownloaderBase` - 下载器基类
- `AioHttpDownloader` - 基于 aiohttp 的下载器
- `HttpXDownloader` - 基于 httpx 的下载器
- `CurlCffiDownloader` - 基于 curl-cffi 的下载器

## 调度器模块

### [crawlo.core.scheduler](crawlo_core_scheduler.md)
请求调度和去重管理。

核心类：
- `Scheduler` - 调度器

## 队列模块

### [crawlo.queue](crawlo_queue___init__.md)
请求队列管理。

核心类：
- `QueueManager` - 队列管理器

## 过滤器模块

### [crawlo.filters](crawlo_filters___init__.md)
请求去重过滤。

核心类：
- `BaseFilter` - 过滤器基类
- `MemoryFilter` - 内存过滤器
- `RedisFilter` - Redis 过滤器
- `BloomFilter` - 布隆过滤器

## 中间件模块

### [crawlo.middleware](crawlo_middleware___init__.md)
请求/响应处理中间件。

核心类：
- `Middleware` - 中间件基类
- `MiddlewareManager` - 中间件管理器

## 管道模块

### [crawlo.pipelines](crawlo_pipelines___init__.md)
数据处理和存储管道。

核心类：
- `Pipeline` - 管道基类
- `PipelineManager` - 管道管理器

### 内置管道

- [crawlo.pipelines.bloom_dedup_pipeline](crawlo_pipelines_bloom_dedup_pipeline.md) - 布隆去重管道
- [crawlo.pipelines.console_pipeline](crawlo_pipelines_console_pipeline.md) - 控制台输出管道
- [crawlo.pipelines.csv_pipeline](crawlo_pipelines_csv_pipeline.md) - CSV 输出管道
- [crawlo.pipelines.database_dedup_pipeline](crawlo_pipelines_database_dedup_pipeline.md) - 数据库去重管道
- [crawlo.pipelines.json_pipeline](crawlo_pipelines_json_pipeline.md) - JSON 输出管道
- [crawlo.pipelines.memory_dedup_pipeline](crawlo_pipelines_memory_dedup_pipeline.md) - 内存去重管道
- [crawlo.pipelines.mongo_pipeline](crawlo_pipelines_mongo_pipeline.md) - MongoDB 输出管道
- [crawlo.pipelines.mysql_pipeline](crawlo_pipelines_mysql_pipeline.md) - MySQL 输出管道
- [crawlo.pipelines.redis_dedup_pipeline](crawlo_pipelines_redis_dedup_pipeline.md) - Redis 去重管道

## 扩展模块

### [crawlo.extension](crawlo_extension___init__.md)
框架扩展功能。

核心类：
- `Extension` - 扩展基类
- `ExtensionManager` - 扩展管理器

## 工具模块

### [crawlo.utils.log](crawlo_utils_log.md)
日志系统工具。

核心函数：
- `configure_logging` - 配置日志系统
- `get_logger` - 获取日志记录器

## 使用示例

```python
from crawlo.crawler import Crawler
from crawlo.spider import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # 解析逻辑
        pass

# 创建并运行爬虫
crawler = Crawler(MySpider)
await crawler.crawl()
```