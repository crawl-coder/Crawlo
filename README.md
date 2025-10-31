<p align="center">
  <img src="assets/logo.svg" alt="Crawlo Logo" width="150"/>
</p>

<h1 align="center">Crawlo</h1>

<p align="center">
  <strong>一个基于 asyncio 的现代化、高性能 Python 异步爬虫框架。</strong>
</p>

<p align="center">
  <a href="#核心特性">核心特性</a> •
  <a href="#项目架构">架构</a> •
  <a href="#安装">安装</a> •
  <a href="#配置模式详解">配置模式</a> •
  <a href="https://github.com/yourusername/crawlo">文档</a>
</p>

## 核心特性

- 🚀 **高性能异步架构**：基于 asyncio 和 aiohttp，充分利用异步 I/O 提升爬取效率
- 🎯 **智能调度系统**：优先级队列、并发控制、自动重试、智能限速
- 🔄 **灵活的配置模式**：
  - **Standalone 模式**：单机开发测试，使用内存队列
  - **Distributed 模式**：多节点分布式部署，严格要求 Redis（不允许降级）
  - **Auto 模式**：智能检测 Redis 可用性，自动选择最佳配置（推荐）
- 📦 **丰富的组件生态**：
  - 内置 Redis 和 MongoDB 支持
  - MySQL 异步连接池（基于 asyncmy和aiomysql分别实现）
  - 多种过滤器和去重管道（Memory/Redis）
  - 代理中间件支持（简单代理/动态代理）
  - 多种下载器（aiohttp、httpx、curl-cffi）
- 🛠 **开发友好**：
  - 类 Scrapy 的项目结构和 API 设计
  - 配置工厂模式（`CrawloConfig.auto()`）
  - 自动爬虫发现机制
  - 完善的日志系统

## 项目架构

Crawlo 框架采用模块化设计，核心组件包括：

![Crawlo 框架架构图](images/Crawlo%20框架架构图.png)

- **Engine**：核心引擎，协调各个组件工作
- **Scheduler**：调度器，管理请求队列和去重
- **Downloader**：下载器，支持多种 HTTP 客户端
- **Spider**：爬虫基类，定义数据提取逻辑
- **Pipeline**：数据管道，处理和存储数据
- **Middleware**：中间件，处理请求和响应

![Crawlo 数据流图](images/Crawlo%20数据流图.png)

## 示例项目

查看 [`examples/`](examples/) 目录下的完整示例项目：

- **ofweek_standalone** - Auto 模式示例（智能检测）
- **ofweek_spider** - Auto 模式示例
- **ofweek_distributed** - Distributed 模式示例（严格分布式）

## 安装

```bash
# 基础安装
pip install crawlo
```

## 配置模式详解

> ⚠️ **重要**：配置模式的选择直接影响爬虫的运行方式、性能和可靠性，请仔细阅读本节内容。

Crawlo 提供三种配置模式，满足不同场景需求：

### 三种模式对比

| 配置项 | Standalone | Distributed | Auto |
|--------|-----------|-------------|------|
| **RUN_MODE** | `standalone` | `distributed` | `auto` |
| **队列类型** | 内存队列 | Redis 队列 | 自动检测 |
| **Redis 要求** | 不需要 | **必需** | 可选 |
| **Redis 不可用时** | N/A | 🚫 **报错退出** | ✅ 降级到内存 |
| **配置自动更新** | ❌ 否 | ❌ 否 | ✅ 是 |
| **过滤器** | Memory | Redis | Redis/Memory |
| **去重管道** | Memory | Redis | Redis/Memory |
| **适用场景** | 开发测试 | 多节点部署 | 生产环境 |
| **并发数默认值** | 8 | 16 | 12 |
| **推荐指数** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 1. Auto 模式（推荐）

**智能检测，自动适配，推荐用于生产环境。**

```python
from crawlo.config import CrawloConfig

config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,
    download_delay=1.0
)
locals().update(config.to_dict())
```

**运行机制**：
- 配置阶段不依赖 Redis
- 运行时才检测 Redis 可用性
- Redis 可用 → 使用 `RedisPriorityQueue` + `AioRedisFilter`
- Redis 不可用 → 降级到 `MemoryQueue` + `MemoryFilter`
- 自动更新配置（`QUEUE_TYPE`、`FILTER_CLASS`、`DEFAULT_DEDUP_PIPELINE`）

**优势**：
- ✅ 开发环境无需配置 Redis，直接启动
- ✅ 生产环境 Redis 故障时自动降级，保证系统可用性
- ✅ 同一份代码可在不同环境运行，无需修改配置
- ✅ 最佳的灵活性和可靠性

**适用场景**：
- 生产环境部署（首选）
- 需要在多种环境运行的项目
- 希望系统具备容错能力

### 2. Standalone 模式

**单机模式，适合开发测试和中小规模爬取。**

```python
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)
locals().update(config.to_dict())
```

**运行机制**：
- 固定使用 `MemoryQueue`（内存队列）
- 固定使用 `MemoryFilter`（内存过滤器）
- 固定使用 `MemoryDedupPipeline`（内存去重）
- 不进行 Redis 检测
- 配置不会自动更新

**优势**：
- ✅ 无需任何外部依赖
- ✅ 启动速度快
- ✅ 适合快速开发调试

**限制**：
- ❌ 不支持分布式部署
- ❌ 重启后队列数据丢失
- ❌ 不适合大规模数据采集

**适用场景**：
- 本地开发调试
- 学习框架特性
- 中小规模数据采集（< 10万条）
- 单机运行的简单爬虫

### 3. Distributed 模式

**分布式模式，严格要求 Redis 可用，适合多节点协同工作。**

```python
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    concurrency=16
)
locals().update(config.to_dict())
```

**运行机制**：
- 必须使用 `RedisPriorityQueue`
- 必须使用 `AioRedisFilter`
- 必须使用 `RedisDedupPipeline`
- 启动时强制检查 Redis 连接
- **Redis 不可用时抛出 `RuntimeError` 并退出（不允许降级）**

**为什么要严格要求 Redis？**

1. **数据一致性**：防止不同节点使用不同的队列类型
2. **去重有效性**：确保多节点间的去重功能正常工作
3. **任务分配**：防止任务被重复执行
4. **问题早发现**：启动失败比运行时失败更容易发现和修复
5. **明确的意图**：分布式模式就应该是分布式的，不应该静默降级

**Redis 不可用时的错误信息**：

```bash
$ crawlo run my_spider

2025-10-25 22:00:00 - [queue_manager] - ERROR: 
Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
错误信息: Connection refused
Redis URL: redis://127.0.0.1:6379/0
请检查：
  1. Redis 服务是否正在运行
  2. Redis 连接配置是否正确
  3. 网络连接是否正常

RuntimeError: Distributed 模式要求 Redis 可用，但无法连接到 Redis 服务器。
```

**优势**：
- ✅ 支持多节点协同爬取
- ✅ 数据持久化，重启后可继续
- ✅ 严格的分布式一致性保证
- ✅ 适合大规模数据采集

**适用场景**：
- 多服务器协同采集
- 大规模数据采集（> 百万条）
- 需要严格保证分布式一致性
- 生产环境多节点部署

### 模式选择建议

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 生产环境（单节点或多节点） | **Auto** | 自动适配，容错能力强 |
| 开发环境 | **Standalone** 或 **Auto** | 无需配置 Redis |
| 严格的多节点分布式部署 | **Distributed** | 保证分布式一致性 |
| 学习和测试 | **Standalone** | 最简单，无依赖 |
| 中小规模爬取 | **Standalone** 或 **Auto** | 简单高效 |
| 大规模爬取 | **Auto** 或 **Distributed** | 性能和可靠性 |

> 📖 **完整文档**：更多详细信息请参考 [配置模式完全指南](docs/tutorials/configuration_modes.md)

## 配置优先级

Crawlo 框架支持多层级的配置系统，了解配置优先级对于正确使用框架至关重要。

### 配置来源与优先级

从**低到高**的优先级顺序：

```
1. default_settings.py (框架默认配置)                    ⭐
   ↓
2. 环境变量 (CRAWLO_*)                                   ⭐⭐
   (在 default_settings.py 中通过 EnvConfigManager 读取)
   ↓
3. 用户 settings.py (项目配置文件)                       ⭐⭐⭐
   ↓
4. Spider.custom_settings (Spider 自定义配置)            ⭐⭐⭐⭐
   ↓
5. 运行时 settings 参数 (crawl() 传入的配置)             ⭐⭐⭐⭐⭐
```

### 环境变量配置

所有环境变量都使用 `CRAWLO_` 前缀：

```bash
# 基础配置
export CRAWLO_MODE=auto                    # 运行模式
export CRAWLO_PROJECT_NAME=myproject       # 项目名称
export CRAWLO_CONCURRENCY=16               # 并发数

# Redis 配置
export CRAWLO_REDIS_HOST=127.0.0.1         # Redis 主机
export CRAWLO_REDIS_PORT=6379              # Redis 端口
export CRAWLO_REDIS_PASSWORD=your_password # Redis 密码
export CRAWLO_REDIS_DB=0                   # Redis 数据库
```

### 配置合并策略

**普通配置**（如 `CONCURRENCY`）：采用**覆盖策略**
```python
# 假设各处都有定义
default_settings.py:  8   →
环境变量:  12  →
settings.py:  16  →
Spider.custom_settings:  24  →
crawl(settings={...}):  32  ✅ 最终值 = 32
```

**列表配置**（如 `MIDDLEWARES`、`PIPELINES`、`EXTENSIONS`）：采用**合并策略**
```python
# default_settings.py
PIPELINES = ['crawlo.pipelines.console_pipeline.ConsolePipeline']

# settings.py
PIPELINES = ['myproject.pipelines.MySQLPipeline']

# 最终结果（合并）
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # 保留默认
    'myproject.pipelines.MySQLPipeline',                   # 追加用户
]
```

### Spider 级别配置

在 Spider 类中可以覆盖项目配置：

```python
class MySpider(Spider):
    name = 'myspider'
    
    custom_settings = {
        'CONCURRENCY': 32,           # 覆盖项目配置
        'DOWNLOAD_DELAY': 2.0,       # 覆盖项目配置
        'PIPELINES': [               # 会与默认管道合并
            'myproject.pipelines.SpecialPipeline',
        ]
    }
```

### 运行时动态配置

```python
from crawlo import CrawlerProcess

process = CrawlerProcess()
await process.crawl(
    MySpider,
    settings={
        'CONCURRENCY': 64,        # 最高优先级
        'DOWNLOAD_DELAY': 0.1,
    }
)
```

### ⚠️ 常见陷阱

**陷阱1：环境变量被项目配置覆盖**
```python
# 环境变量
export CRAWLO_REDIS_HOST=192.168.1.100

# settings.py（这会覆盖环境变量！）
REDIS_HOST = 'localhost'  # ❌ 会覆盖环境变量

# 解决方案：不在 settings.py 中重复设置，或使用 CrawloConfig.auto()
```

**陷阱2：误以为列表配置会被清空**
```python
# settings.py
PIPELINES = ['myproject.pipelines.MySQLPipeline']

# 实际结果（默认管道会被保留并合并）
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',  # 默认保留
    'myproject.pipelines.MySQLPipeline',                   # 用户追加
]

# 如果想完全替换，需要先清空
PIPELINES = []  # 清空
PIPELINES.append('myproject.pipelines.MySQLPipeline')
```

> 📖 **详细文档**：完整的配置优先级说明请参考 [配置优先级详解](docs/配置优先级详解.md)

## 快速开始

### 1. 创建项目

```bash
# 创建新项目
crawlo startproject myproject
cd myproject

# 创建爬虫
crawlo genspider example example.com
```

### 2. 配置项目（推荐使用 Auto 模式）

```python
# myproject/settings.py
from crawlo.config import CrawloConfig

# 使用 Auto 模式：智能检测 Redis，自动选择最佳配置
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,          # 并发数
    download_delay=1.0       # 下载延迟（秒）
)

# 将配置应用到当前模块
locals().update(config.to_dict())

# 爬虫模块配置
SPIDER_MODULES = ['myproject.spiders']

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/myproject.log'

# 可选：添加数据管道
# PIPELINES = [
#     'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
# ]

# 可选：Redis 配置（Auto 模式会自动检测）
# REDIS_HOST = '127.0.0.1'
# REDIS_PORT = 6379
```

**其他配置模式：**

```python
# Standalone 模式：单机开发测试
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)

# Distributed 模式：多节点分布式（必须配置 Redis）
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    redis_port=6379,
    redis_password='your_password',
    concurrency=16
)
```

### 3. 编写爬虫

```python
# myproject/spiders/example.py
from crawlo import Spider
from crawlo.http import Request

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['https://example.com']
    
    async def parse(self, response):
        # 提取数据
        title = response.css('h1::text').get()
        
        # 返回数据
        yield {
            'title': title,
            'url': response.url
        }
        
        # 跟进链接
        for href in response.css('a::attr(href)').getall():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse
            )
```

### 4. 运行爬虫

```bash
# 运行指定爬虫
crawlo run example

# 指定日志级别
crawlo run example --log-level DEBUG
```

## 核心功能

### Response 对象

Crawlo 的 [`Response`](crawlo/http/response.py) 对象提供了强大的网页处理能力：

**1. 智能编码检测**

```python
# 自动检测并正确解码页面内容
# 优先级：Content-Type → HTML meta → chardet → utf-8
response.text      # 已正确解码的文本
response.encoding  # 检测到的编码
```

**2. CSS/XPath 选择器**

```python
# CSS 选择器（推荐）
title = response.css('h1::text').get()
links = response.css('a::attr(href)').getall()

# XPath 选择器
title = response.xpath('//title/text()').get()
links = response.xpath('//a/@href').getall()

# 支持默认值
title = response.css('h1::text').get(default='无标题')
```

**3. URL 处理**

```python
response.url          # 自动规范化（移除 fragment）
response.original_url # 保留原始 URL

# 智能 URL 拼接
response.urljoin('/path')           # 绝对路径
response.urljoin('../path')         # 相对路径
response.urljoin('//cdn.com/img')   # 协议相对路径
```

**4. 便捷提取方法**

```python
# 提取单个/多个元素文本
title = response.extract_text('h1')
paragraphs = response.extract_texts('.content p')

# 提取单个/多个元素属性
link = response.extract_attr('a', 'href')
all_links = response.extract_attrs('a', 'href')
```

### 配置工厂模式

Crawlo 提供了便捷的配置工厂方法，无需手动配置繁琐的参数：

```python
from crawlo.config import CrawloConfig

# Auto 模式（推荐）：智能检测，自动适配
config = CrawloConfig.auto(
    project_name='myproject',
    concurrency=12,
    download_delay=1.0
)

# Standalone 模式：单机开发
config = CrawloConfig.standalone(
    project_name='myproject',
    concurrency=8
)

# Distributed 模式：严格分布式
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='localhost',
    redis_port=6379,
    concurrency=16
)

# 应用到 settings.py
locals().update(config.to_dict())
```

**三种模式的核心区别**：

- **Auto**：智能检测 Redis，自动选择最佳配置，**推荐用于生产环境**
- **Standalone**：固定使用内存队列，适合开发测试，无外部依赖
- **Distributed**：严格要求 Redis，不允许降级，保证分布式一致性

> 💡 详细配置说明请查看前面的 [配置模式详解](#配置模式详解) 章节

### 日志系统

Crawlo 提供了完善的日志系统，支持控制台和文件双输出：

```python
from crawlo.logging import get_logger

logger = get_logger(__name__)

logger.debug('调试信息')
logger.info('普通信息')
logger.warning('警告信息')
logger.error('错误信息')
```

**日志配置：**

```python
# settings.py
LOG_LEVEL = 'INFO'          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = 'logs/spider.log'
LOG_ENCODING = 'utf-8'      # 明确指定日志文件编码
STATS_DUMP = True           # 是否输出统计信息
```

**高级功能：**

```python
from crawlo.logging import configure_logging

# 分别配置控制台和文件日志级别
configure_logging(
    LOG_LEVEL='INFO',
    LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示 WARNING 及以上
    LOG_FILE_LEVEL='DEBUG',       # 文件记录 DEBUG 及以上
    LOG_FILE='logs/app.log',
    LOG_MAX_BYTES=10*1024*1024,   # 10MB
    LOG_BACKUP_COUNT=5
)
```

### 爬虫自动发现

Crawlo 支持自动发现爬虫，无需手动导入：

```bash
# 自动发现并运行（推荐）
crawlo run spider_name

# 指定文件路径运行
crawlo run -f path/to/spider.py -s SpiderClassName
```

框架会自动在 `SPIDER_MODULES` 配置的模块中查找爬虫。

### 跨平台支持

Crawlo 在 Windows、macOS、Linux 上均可无缝运行：

- **Windows**：自动使用 ProactorEventLoop，正确处理控制台编码
- **macOS/Linux**：使用默认的 SelectorEventLoop
- 兼容不同平台的路径格式

> 💡 **Windows 用户提示**：如需日志轮转功能，建议安装 `concurrent-log-handler`：
> ```bash
> pip install concurrent-log-handler
> ```

![Crawlo 核心架构图](images/Crawlo%20核心架构图.png)

## 文档

完整文档请查看 [`docs/`](docs/) 目录：

### 📚 核心教程

- [配置模式完全指南](docs/tutorials/configuration_modes.md) - **强烈推荐阅读**
- [架构概述](docs/modules/architecture/index.md)
- [运行模式](docs/modules/architecture/modes.md)
- [配置系统](docs/modules/configuration/index.md)

### 🔧 核心模块

- [引擎 (Engine)](docs/modules/core/engine.md)
- [调度器 (Scheduler)](docs/modules/core/scheduler.md)
- [处理器 (Processor)](docs/modules/core/processor.md)
- [爬虫基类 (Spider)](docs/modules/core/spider.md)

### 📦 功能模块

- [下载器 (Downloader)](docs/modules/downloader/index.md)
- [队列 (Queue)](docs/modules/queue/index.md)
- [过滤器 (Filter)](docs/modules/filter/index.md)
- [中间件 (Middleware)](docs/modules/middleware/index.md)
- [管道 (Pipeline)](docs/modules/pipeline/index.md)
- [扩展 (Extension)](docs/modules/extension/index.md)

### 🛠 命令行工具

- [CLI 概述](docs/modules/cli/index.md)
- [startproject](docs/modules/cli/startproject.md) - 项目初始化
- [genspider](docs/modules/cli/genspider.md) - 爬虫生成
- [run](docs/modules/cli/run.md) - 爬虫运行
- [list](docs/modules/cli/list.md) - 查看爬虫列表
- [check](docs/modules/cli/check.md) - 配置检查
- [stats](docs/modules/cli/stats.md) - 统计信息

### 🚀 高级主题

- [分布式部署](docs/modules/advanced/distributed.md)
- [性能优化](docs/modules/advanced/performance.md)
- [故障排除](docs/modules/advanced/troubleshooting.md)
- [最佳实践](docs/modules/advanced/best_practices.md)

### 📝 性能优化报告

- [初始化优化报告](docs/initialization_optimization_report.md)
- [MySQL 连接池优化](docs/mysql_connection_pool_optimization.md)
- [MongoDB 连接池优化](docs/mongo_connection_pool_optimization.md)

### 📖 API 参考

- [完整 API 文档](docs/api/)

---

**在线文档**：
- [中文文档](https://crawlo.readthedocs.io/en/latest/README_zh/)
- [English Documentation](https://crawlo.readthedocs.io/en/latest/)

**本地构建文档**：
```bash
mkdocs serve
# 浏览器访问 http://localhost:8000
```

## 常见问题

### 1. 如何选择配置模式？

- **开发测试**：使用 `CrawloConfig.standalone()`
- **生产环境**：使用 `CrawloConfig.auto()`（推荐）
- **多节点部署**：使用 `CrawloConfig.distributed()`

### 2. Distributed 模式 Redis 不可用怎么办？

Distributed 模式**严格要求 Redis**，不可用时会抛出 `RuntimeError` 并退出。这是为了保证分布式一致性和数据安全。

如果希望 Redis 不可用时自动降级，请使用 **Auto 模式**。

### 3. Auto 模式如何工作？

Auto 模式在运行时智能检测：
- Redis 可用 → 使用 RedisPriorityQueue + AioRedisFilter
- Redis 不可用 → 降级到 MemoryQueue + MemoryFilter

详见 [配置模式完全指南](docs/tutorials/configuration_modes.md)。

### 4. 如何启用 MySQL 或 MongoDB 支持？

```python
# settings.py
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL
    # 或
    'crawlo.pipelines.mongo_pipeline.MongoDBPipeline',       # MongoDB
]

# MySQL 配置
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DB = 'mydb'
MYSQL_TABLE = 'items'

# MongoDB 配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'mydb'
MONGO_COLLECTION = 'items'
```

### 5. 如何使用代理？

```python
# settings.py

# 简单代理列表
PROXY_LIST = [
    "http://proxy1:8080",
    "http://proxy2:8080"
]

# 或使用动态代理 API
PROXY_API_URL = "http://your-proxy-api.com/get-proxy"
```

## 学习路径

如果您是 Crawlo 的新用户，建议按以下顺序学习：

1. **入门** - 阅读快速开始指南，运行第一个示例
2. **配置模式** - 学习三种配置模式，选择适合的模式（[配置模式指南](docs/tutorials/configuration_modes.md)）
3. **核心概念** - 了解框架架构和基本概念
4. **核心模块** - 深入学习引擎、调度器、处理器等核嘿组件
5. **功能模块** - 根据需求学习下载器、队列、过滤器等模块
6. **高级主题** - 掌握分布式部署、性能优化等高级功能

## 贡献

欢迎贡献！如果您想为 Crawlo 做出贡献：

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<p align="center">
  <i>如有问题或建议，欢迎提交 <a href="https://github.com/crawl-coder/Crawlo/issues">Issue</a></i>
</p>