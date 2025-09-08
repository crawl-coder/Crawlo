# Crawlo 框架文档

## 目录
1. [介绍](#介绍)
2. [安装](#安装)
3. [快速开始](#快速开始)
4. [项目结构](#项目结构)
5. [核心组件](#核心组件)
6. [配置](#配置)
7. [爬虫](#爬虫)
8. [项目](#项目)
9. [管道](#管道)
10. [中间件](#中间件)
11. [分布式爬取](#分布式爬取)
12. [命令行界面](#命令行界面)
13. [最佳实践](#最佳实践)
14. [故障排除](#故障排除)

## 介绍

Crawlo 是一个现代化、高性能的 Python 异步网络爬虫框架，旨在简化网络爬虫的开发和部署。它支持单机和分布式模式，适用于从小规模开发到大规模生产环境的各种场景。

### 主要特性

- **多种执行模式**：单机模式（默认）、分布式模式（基于 Redis）和自动检测模式
- **命令行界面**：`crawlo startproject`、`crawlo genspider` 和 `crawlo run` 等工具简化项目创建和执行
- **自动爬虫发现**：自动从 `spiders/` 目录加载爬虫模块，无需手动注册
- **智能配置系统**：链式配置方法和预设配置，适用于不同环境
- **高性能架构**：基于 `asyncio` 构建，支持多种下载器（aiohttp、httpx、curl-cffi），并包含智能中间件用于去重、重试和代理支持
- **监控和管理**：实时统计、结构化日志记录、健康检查和性能分析工具

## 安装

要安装 Crawlo，您可以使用 pip：

```bash
# 克隆仓库
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo

# 以开发模式安装
pip install -e .
```

### 依赖项

Crawlo 需要 Python 3.10+，并具有以下关键依赖项：

- aiohttp~=3.12.14
- aiomysql==0.2.0
- asyncmy==0.2.10
- cssselect==1.2.0
- dateparser==1.2.2
- httpx[http2]==0.27.0
- curl-cffi==0.13.0
- lxml==5.2.1
- motor==3.7.0
- parsel==1.9.1
- pydantic==2.11.7
- pymongo==4.11
- PyMySQL==1.1.1
- python-dateutil==2.9.0.post0
- redis==6.2.0
- requests==2.32.4
- six==1.17.0
- ujson==5.9.0
- urllib3==2.5.0
- w3lib==2.1.2
- psutil~=7.0.0
- anyio~=4.3.0
- httpcore~=1.0.5
- rich>=13.0.0
- astor>=0.8.0
- watchdog>=3.0.0

## 快速开始

### 创建新项目

要创建一个新的 Crawlo 项目，请使用 `startproject` 命令：

```bash
crawlo startproject myproject
cd myproject
```

这将创建以下目录结构：

```
myproject/
├── crawlo.cfg          # 项目配置
├── myproject/
│   ├── __init__.py
│   ├── settings.py     # 设置文件
│   ├── items.py        # 数据项定义
│   └── spiders/        # 爬虫目录
└── run.py              # 运行脚本
```

### 生成爬虫

要生成爬虫模板，请使用 `genspider` 命令：

```bash
crawlo genspider example example.com
```

这将在 `spiders/` 目录中创建一个爬虫，结构如下：

```python
from crawlo import Spider, Request
from myproject.items import ExampleItem

class ExampleSpider(Spider):
    name = "example"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # 提取数据
        item = ExampleItem()
        item['title'] = response.css('title::text').get()
        item['url'] = response.url
        yield item
        
        # 跟进链接
        for link in response.css('a::attr(href)').getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### 运行爬虫

您可以通过以下几种方式运行爬虫：

```bash
# 单机模式（默认）
python run.py example

# 分布式模式
python run.py example --distributed

# 开发环境
python run.py example --env development --debug

# 自定义并发数
python run.py example --concurrency 20 --delay 0.5

# 使用预设配置
python run.py example --env production
```

## 项目结构

典型的 Crawlo 项目遵循以下结构：

```
project_name/
├── crawlo.cfg              # 项目配置文件
├── run.py                  # 主执行脚本
├── logs/                   # 日志目录
├── project_name/           # 主 Python 包
│   ├── __init__.py         # 包初始化器
│   ├── settings.py         # 配置设置
│   ├── items.py            # 数据项定义
│   ├── middlewares.py      # 自定义中间件
│   ├── pipelines.py        # 数据处理管道
│   └── spiders/            # 爬虫实现
│       ├── __init__.py     # 爬虫包初始化器
│       └── *.py            # 单个爬虫文件
```

### 关键文件

1. **crawlo.cfg**：项目配置文件，标识项目根目录
2. **run.py**：运行爬虫的主脚本
3. **settings.py**：项目的配置设置
4. **items.py**：数据项定义
5. **spiders/\*.py**：单个爬虫实现

## 核心组件

### 引擎

引擎是协调爬取过程的核心组件。它管理调度器、下载器和处理器组件。

### 调度器

调度器管理请求队列并处理请求去重。它支持基于内存和基于 Redis 的实现，分别用于单机和分布式模式。

### 下载器

下载器负责获取网页。Crawlo 支持多个下载器：

- **aiohttp**：高性能默认下载器
- **httpx**：支持 HTTP/2
- **curl-cffi**：浏览器指纹模拟

### 处理器

处理器处理从响应中提取的数据，并将项目通过管道传递。

## 配置

Crawlo 提供了灵活的配置系统，有多种方式来配置您的项目。

### 传统配置

在 `settings.py` 中：

```python
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
QUEUE_TYPE = 'memory'  # 单机模式
# QUEUE_TYPE = 'redis'   # 分布式模式
```

### 智能配置工厂

```python
from crawlo.config import CrawloConfig

# 单机模式
config = CrawloConfig.standalone().set_concurrency(16)

# 分布式模式
config = CrawloConfig.distributed(redis_host='192.168.1.100')

# 预设配置
config = CrawloConfig.presets().production()

# 链式调用
config = (CrawloConfig.standalone()
    .set_concurrency(20)
    .set_delay(1.5)
    .enable_debug()
    .enable_mysql())

# 环境变量配置
config = CrawloConfig.from_env()
```

### 预设配置

| 配置 | 使用场景 | 特性 |
|---------------|----------|----------|
| `development()` | 开发和调试 | 低并发、详细日志、调试友好 |
| `production()` | 生产环境 | 高性能、自动模式、稳定可靠 |
| `large_scale()` | 大规模爬取 | 分布式、内存优化、批处理 |
| `gentle()` | 温和模式 | 低负载、对目标服务器友好 |

## 爬虫

爬虫是定义如何爬取和解析特定网站或网站集的类。

### 基本爬虫结构

```python
from crawlo import Spider, Request
from myproject.items import MyItem

class MySpider(Spider):
    name = "myspider"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # 提取数据并生成项目
        item = MyItem()
        item['title'] = response.css('title::text').get()
        yield item
        
        # 跟进链接
        for link in response.css('a::attr(href)').getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### 爬虫属性

- `name`：爬虫的唯一标识符
- `allowed_domains`：爬虫允许爬取的域名列表
- `start_urls`：爬虫开始爬取的 URL 列表
- `custom_settings`：覆盖项目设置的设置字典

### 爬虫方法

- `start_requests()`：生成初始请求
- `parse(response)`：解析响应并提取数据

## 项目

项目是爬取数据的容器。它们定义了您想要提取的数据结构。

### 定义项目

```python
from crawlo.items import Item, Field

class MyItem(Item):
    title = Field(description="页面标题")
    url = Field(description="页面 URL")
    content = Field(description="页面内容")
```

### 使用项目

```python
def parse(self, response):
    item = MyItem()
    item['title'] = response.css('title::text').get()
    item['url'] = response.url
    item['content'] = response.css('body').get()
    yield item
```

## 管道

管道在爬虫提取项目后处理它们。它们可以清理、验证和存储数据。

### 内置管道

- `ConsolePipeline`：将项目输出到控制台
- `JsonPipeline`：将项目保存到 JSON 文件
- `CsvPipeline`：将项目保存到 CSV 文件
- `AsyncmyMySQLPipeline`：将项目存储在 MySQL 数据库中
- `MongoPipeline`：将项目存储在 MongoDB 中

### 配置管道

在 `settings.py` 中：

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

### 自定义管道

```python
class CustomPipeline:
    def process_item(self, item, spider):
        # 处理项目
        return item
```

## 中间件

中间件组件在请求和响应通过系统时处理它们。

### 内置中间件

- `RequestIgnoreMiddleware`：过滤请求
- `DownloadDelayMiddleware`：控制下载延迟
- `DefaultHeaderMiddleware`：添加默认头部
- `ProxyMiddleware`：处理代理
- `RetryMiddleware`：实现重试逻辑
- `ResponseCodeMiddleware`：处理响应代码

### 配置中间件

在 `settings.py` 中：

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
]
```

## 分布式爬取

Crawlo 使用 Redis 支持分布式爬取，以协调多个节点之间的爬取。

### 架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  节点 A     │    │  节点 B     │    │  节点 N     │
│ (爬虫)      │    │ (爬虫)      │    │ (爬虫)      │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
              ┌───────────▼────────────┐
              │     Redis 集群        │
              │ ┌─────────────────────┐│
              │ │ 任务队列            ││
              │ │ 去重集合            ││
              │ │ 统计信息            ││
              │ └─────────────────────┘│
              └─────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │    共享存储            │
              │   MySQL / MongoDB      │
              └─────────────────────────┘
```

### 分布式特性

- **自动负载均衡**：任务在节点间自动分配
- **分布式去重**：防止跨节点重复爬取
- **水平扩展**：动态添加或删除节点
- **故障恢复**：节点故障不影响整体操作

### 配置

要启用分布式爬取，请在 `settings.py` 中配置以下内容：

```python
# 分布式模式配置
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# 并发设置
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# 调度器配置
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# 分布式去重
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'
```

### 运行分布式爬虫

```bash
# 启动 Redis 服务器
redis-server

# 运行分布式爬虫
python run.py myspider --distributed

# 多节点部署
# 节点 1
python run.py myspider --distributed --redis-host 192.168.1.100

# 节点 2
python run.py myspider --distributed --redis-host 192.168.1.100 --concurrency 20
```

## 命令行界面

Crawlo 提供了全面的命令行界面来管理项目和爬虫。

### 可用命令

| 命令 | 功能 | 示例 |
|---------|----------|---------|
| `startproject` | 创建新项目 | `crawlo startproject myproject` |
| `genspider` | 生成爬虫 | `crawlo genspider news news.com` |
| `list` | 列出所有爬虫 | `crawlo list` |
| `check` | 检查爬虫合规性 | `crawlo check` |
| `run` | 运行爬虫 | `crawlo run news --distributed` |
| `stats` | 查看统计信息 | `crawlo stats news` |

### 命令示例

```bash
# 创建新项目
crawlo startproject myproject

# 生成爬虫
crawlo genspider example example.com

# 列出可用爬虫
crawlo list

# 检查爬虫语法
crawlo check example

# 运行爬虫
crawlo run example

# 查看统计信息
crawlo stats example
```

## 最佳实践

### 开发阶段

```bash
# 使用开发配置，低并发和详细日志
python run.py my_spider --env development --debug
```

### 测试阶段

```bash
# 干运行模式以验证逻辑
python run.py my_spider --dry-run
```

### 生产环境

```bash
# 使用生产配置或分布式模式
python run.py my_spider --env production
python run.py my_spider --distributed --concurrency 50
```

### 大规模爬取

```bash
# 使用大规模配置和分布式模式
python run.py my_spider --env large-scale
```

### 下载器选择最佳实践

```python
# 开发/测试 - 使用 httpx（稳定，兼容性好）
DOWNLOADER_TYPE = 'httpx'

# 生产 - 使用 aiohttp（高性能）
DOWNLOADER_TYPE = 'aiohttp'

# 反爬虫场景 - 使用 curl_cffi（浏览器指纹）
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'
```

## 故障排除

### 常见问题

1. **导入错误**
   ```
   ImportError: No module named 'myproject'
   ```
   **解决方案**：确保您在包含 `crawlo.cfg` 的项目根目录中运行脚本。

2. **Redis 连接失败**
   ```
   Redis connection failed: localhost:6379
   ```
   **解决方案**：检查 Redis 服务状态并使用 `--check-redis` 测试连接。

3. **配置文件错误**
   ```
   crawlo.cfg not found
   ```
   **解决方案**：确保在运行框架命令时在包含 `crawlo.cfg` 的目录中。

4. **找不到爬虫类**
   ```
   No spider found for: myspider
   ```
   **解决方案**：检查爬虫文件是否具有正确的 `name` 属性。

### 调试方法

```bash
# 启用调试模式
python run.py myspider --debug

# 限制数据进行测试
python run.py myspider --max-pages 5

# 检查配置
python -c "from myproject import settings; print(settings.CONCURRENCY)"
```

### 性能调优

```python
# 并发控制
CONCURRENCY = 16                    # 并发请求数
DOWNLOAD_DELAY = 1.0               # 下载延迟
CONNECTION_POOL_LIMIT = 100        # 全局连接池大小
CONNECTION_POOL_LIMIT_PER_HOST = 30 # 每个主机的连接数

# 重试策略
MAX_RETRY_TIMES = 3                # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503] # 重试状态码

# 统计和监控
DOWNLOADER_STATS = True            # 启用下载器统计
DOWNLOAD_STATS = True              # 记录下载时间和大小
DOWNLOADER_HEALTH_CHECK = True     # 下载器健康检查
REQUEST_STATS_ENABLED = True       # 请求统计
```