<!-- markdownlint-disable MD033 MD041 -->
<div align="center">
  <h1 align="center">Crawlo</h1>
  <p align="center">异步分布式爬虫框架</p>
  <p align="center"><strong>基于 asyncio 的高性能异步分布式爬虫框架，支持单机和分布式部署</strong></p>
  
  <p align="center">
    <a href="https://www.python.org/downloads/">
      <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python Version">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    </a>
    <a href="https://crawlo.readthedocs.io/">
      <img src="https://img.shields.io/badge/docs-latest-brightgreen" alt="Documentation">
    </a>
    <a href="https://github.com/crawlo/crawlo/actions">
      <img src="https://github.com/crawlo/crawlo/workflows/CI/badge.svg" alt="CI Status">
    </a>
  </p>
  
  <p align="center">
    <a href="#-特性">特性</a> •
    <a href="#-快速开始">快速开始</a> •
    <a href="#-命令行工具">命令行工具</a> •
    <a href="#-示例项目">示例项目</a>
  </p>
</div>

<br />

<!-- 特性 section -->
<div align="center">
  <h2>🌟 特性</h2>

  <table>
    <thead>
      <tr>
        <th>特性</th>
        <th>描述</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>⚡ <strong>异步高性能</strong></td>
        <td>基于 asyncio 实现，充分利用现代 CPU 夯性能</td>
      </tr>
      <tr>
        <td>🌐 <strong>分布式支持</strong></td>
        <td>内置 Redis 队列，轻松实现分布式部署</td>
      </tr>
      <tr>
        <td>🔧 <strong>模块化设计</strong></td>
        <td>中间件、管道、扩展组件系统，易于定制和扩展</td>
      </tr>
      <tr>
        <td>🔄 <strong>智能去重</strong></td>
        <td>多种去重策略（内存、Redis、Bloom Filter）</td>
      </tr>
      <tr>
        <td>⚙️ <strong>灵活配置</strong></td>
        <td>支持多种配置方式，适应不同场景需求</td>
      </tr>
      <tr>
        <td>📋 <strong>高级日志</strong></td>
        <td>支持日志轮转、结构化日志、JSON格式等高级功能</td>
      </tr>
      <tr>
        <td>📚 <strong>丰富文档</strong></td>
        <td>完整的中英文双语文档和示例项目</td>
      </tr>
    </tbody>
  </table>
</div>

<br />

---

<!-- 快速开始 section -->
<h2 align="center">🚀 快速开始</h2>

### 安装

```bash
pip install crawlo
```

### 创建项目

```bash
# 创建默认项目
crawlo startproject myproject

# 创建分布式模板项目
crawlo startproject myproject distributed

# 创建项目并选择特定模块
crawlo startproject myproject --modules mysql,redis,proxy

cd myproject
```

### 生成爬虫

```bash
# 在项目目录中生成爬虫
crawlo genspider news_spider news.example.com
```

### 编写爬虫

``python
from crawlo import Spider, Request, Item

class MyItem(Item):
    title = ''
    url = ''

class MySpider(Spider):
    name = 'myspider'
    
    async def start_requests(self):
        yield Request('https://httpbin.org/get', callback=self.parse)
    
    async def parse(self, response):
        yield MyItem(
            title='Example Title',
            url=response.url
        )
```

### 运行爬虫

```bash
# 使用命令行工具运行爬虫（推荐）
crawlo run myspider

# 使用项目自带的 run.py 脚本运行
python run.py

# 运行所有爬虫
crawlo run all

# 在项目子目录中也能正确运行
cd subdirectory
crawlo run myspider
```

---

<!-- 命令行工具 section -->
<h2 align="center">🔧 命令行工具</h2>

Crawlo 提供了丰富的命令行工具，简化项目创建和管理。

### crawlo startproject

创建新的爬虫项目。

```bash
# 创建默认项目
crawlo startproject myproject

# 创建指定模板的项目
crawlo startproject myproject simple
crawlo startproject myproject distributed
```

### crawlo genspider

在现有项目中生成新的爬虫。

```bash
# 在当前目录生成爬虫
crawlo genspider myspider http://example.com

# 指定模板生成爬虫
crawlo genspider myspider http://example.com --template basic
```

### crawlo run

运行指定的爬虫。

```bash
# 运行单个爬虫
crawlo run myspider

# 运行所有爬虫
crawlo run all

# 以JSON格式输出结果
crawlo run myspider --json

# 禁用统计信息
crawlo run myspider --no-stats
```

### crawlo list

列出项目中的所有爬虫。

```bash
crawlo list
```

### crawlo check

检查项目配置和爬虫实现。

```bash
# 检查所有爬虫
crawlo check

# 检查特定爬虫
crawlo check myspider
```

### crawlo stats

查看爬虫统计信息。

```bash
# 查看统计信息
crawlo stats
```

---

<!-- 配置方式 section -->
<h2 align="center">⚙️ 配置方式</h2>

Crawlo 提供了多种灵活的配置方式，以适应不同的使用场景和开发需求。

### 三种配置方式详解

#### 1. 配置工厂方式（推荐）

使用 `CrawloConfig` 配置工厂是推荐的配置方式，它提供了类型安全和智能提示。

```python
from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess

# 单机模式配置
config = CrawloConfig.standalone(
    concurrency=8,
    download_delay=1.0
)

# 分布式模式配置
config = CrawloConfig.distributed(
    redis_host='127.0.0.1',
    redis_port=6379,
    project_name='myproject',
    concurrency=16
)

# 自动检测模式配置
config = CrawloConfig.auto(concurrency=12)

# 从环境变量读取配置
config = CrawloConfig.from_env()

# 创建爬虫进程
process = CrawlerProcess(settings=config.to_dict())
```

#### 2. 直接配置方式

直接在 `settings.py` 文件中配置各项参数，适合需要精细控制的场景。

```
# settings.py
PROJECT_NAME = 'myproject'
RUN_MODE = 'standalone'  # 或 'distributed' 或 'auto'
CONCURRENCY = 8
DOWNLOAD_DELAY = 1.0

# 分布式模式下需要配置Redis
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''

# 其他配置...
```

#### 3. 环境变量方式

通过环境变量配置，适合部署和CI/CD场景。

```bash
# 设置环境变量
export CRAWLO_MODE=standalone
export CONCURRENCY=8
export DOWNLOAD_DELAY=1.0
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
```

```python
# 在代码中读取环境变量
from crawlo.config import CrawloConfig
config = CrawloConfig.from_env()
process = CrawlerProcess(settings=config.to_dict())
```

### 不同运行模式下的最佳配置方式

#### 单机模式 (standalone)

适用于开发调试、小规模数据采集、个人项目。

**推荐配置方式：**
```python
from crawlo.config import CrawloConfig
config = CrawloConfig.standalone(concurrency=4, download_delay=1.0)
process = CrawlerProcess(settings=config.to_dict())
```

**特点：**
- 简单易用，资源占用少
- 无需额外依赖（如Redis）
- 适合个人开发环境

#### 分布式模式 (distributed)

适用于大规模数据采集、多节点协同工作、高并发需求。

**推荐配置方式：**
```python
from crawlo.config import CrawloConfig
config = CrawloConfig.distributed(
    redis_host='your_redis_host',
    redis_port=6379,
    project_name='myproject',
    concurrency=16
)
process = CrawlerProcess(settings=config.to_dict())
```

**特点：**
- 支持多节点扩展
- 高并发处理能力
- 需要Redis支持

#### 自动检测模式 (auto)

适用于希望根据环境自动选择最佳运行方式。

**推荐配置方式：**
```python
from crawlo.config import CrawloConfig
config = CrawloConfig.auto(concurrency=12)
process = CrawlerProcess(settings=config.to_dict())
```

**特点：**
- 智能检测环境配置
- 自动选择运行模式
- 适合在不同环境中使用同一套配置

### 组件配置说明

Crawlo框架的中间件、管道和扩展组件采用模块化设计，框架会自动加载默认组件，用户只需配置自定义组件。

#### 中间件配置

框架默认加载以下中间件：
- RequestIgnoreMiddleware：忽略无效请求
- DownloadDelayMiddleware：控制请求频率
- DefaultHeaderMiddleware：添加默认请求头
- ProxyMiddleware：设置代理
- OffsiteMiddleware：站外请求过滤
- RetryMiddleware：失败请求重试
- ResponseCodeMiddleware：处理特殊状态码
- ResponseFilterMiddleware：响应内容过滤

用户可以通过`CUSTOM_MIDDLEWARES`配置自定义中间件：

```python
# settings.py
CUSTOM_MIDDLEWARES = [
    'myproject.middlewares.CustomMiddleware',
]
```

#### 管道配置

框架默认加载以下管道：
- ConsolePipeline：控制台输出
- 默认去重管道（根据运行模式自动选择）

用户可以通过`CUSTOM_PIPELINES`配置自定义管道：

```python
# settings.py
CUSTOM_PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

#### 扩展配置

框架默认加载以下扩展：
- LogIntervalExtension：定时日志
- LogStats：统计信息
- CustomLoggerExtension：自定义日志

用户可以通过`CUSTOM_EXTENSIONS`配置自定义扩展：

```python
# settings.py
CUSTOM_EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]
```

<!-- 架构设计 section -->
<h2 align="center">🏗️ 架构设计</h2>

### 核心组件说明

Crawlo 框架由以下核心组件构成：

<table>
  <thead>
    <tr>
      <th>组件</th>
      <th>功能描述</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Crawler</strong></td>
      <td>爬虫运行实例，管理Spider与引擎的生命周期</td>
    </tr>
    <tr>
      <td><strong>Engine</strong></td>
      <td>引擎组件，协调Scheduler、Downloader、Processor</td>
    </tr>
    <tr>
      <td><strong>Scheduler</strong></td>
      <td>调度器，管理请求队列和去重过滤</td>
    </tr>
    <tr>
      <td><strong>Downloader</strong></td>
      <td>下载器，负责网络请求，支持多种实现(aiohttp, httpx, curl-cffi)</td>
    </tr>
    <tr>
      <td><strong>Processor</strong></td>
      <td>处理器，处理响应数据和管道</td>
    </tr>
    <tr>
      <td><strong>QueueManager</strong></td>
      <td>统一的队列管理器，支持内存队列和Redis队列的自动切换</td>
    </tr>
    <tr>
      <td><strong>Filter</strong></td>
      <td>请求去重过滤器，支持内存和Redis两种实现</td>
    </tr>
    <tr>
      <td><strong>Middleware</strong></td>
      <td>中间件系统，处理请求/响应的预处理和后处理</td>
    </tr>
    <tr>
      <td><strong>Pipeline</strong></td>
      <td>数据处理管道，支持多种存储方式(控制台、数据库等)和去重功能</td>
    </tr>
    <tr>
      <td><strong>Spider</strong></td>
      <td>爬虫基类，定义爬取逻辑</td>
    </tr>
  </tbody>
</table>

### 运行模式

Crawlo支持三种运行模式：

<table>
  <thead>
    <tr>
      <th>模式</th>
      <th>描述</th>
      <th>队列类型</th>
      <th>过滤器类型</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>standalone</strong></td>
      <td>单机模式</td>
      <td>内存队列</td>
      <td>内存过滤器</td>
    </tr>
    <tr>
      <td><strong>distributed</strong></td>
      <td>分布式模式</td>
      <td>Redis队列</td>
      <td>Redis过滤器</td>
    </tr>
    <tr>
      <td><strong>auto</strong></td>
      <td>自动检测模式</td>
      <td>根据环境自动选择最佳运行方式</td>
      <td>根据环境自动选择</td>
    </tr>
  </tbody>
</table>

> **运行模式说明**: distributed模式为多节点分布式设计，强制使用Redis队列和去重；standalone+auto为单机智能模式，根据环境自动选择内存或Redis队列与去重策略，零配置启动。

#### 运行模式选择指南

##### 1. 单机模式 (standalone)
- **适用场景**：
  - 开发和测试阶段
  - 小规模数据采集（几千到几万条数据）
  - 学习和演示用途
  - 对目标网站负载要求不高的场景
- **优势**：
  - 配置简单，无需额外依赖
  - 资源消耗低
  - 启动快速
  - 适合本地开发调试
- **限制**：
  - 无法跨会话去重
  - 无法分布式部署
  - 内存占用随数据量增长

##### 2. 分布式模式 (distributed)
- **适用场景**：
  - 大规模数据采集（百万级以上）
  - 需要多节点协同工作
  - 要求跨会话、跨节点去重
  - 生产环境部署
- **优势**：
  - 支持水平扩展
  - 跨节点任务协调
  - 持久化去重过滤
  - 高可用性
- **要求**：
  - 需要Redis服务器
  - 网络环境稳定
  - 更复杂的配置管理

##### 3. 自动模式 (auto)
- **适用场景**：
  - 希望根据环境自动选择最佳配置
  - 开发和生产环境使用同一套代码
  - 动态适应运行环境
- **工作机制**：
  - 检测Redis可用性
  - Redis可用时自动切换到分布式模式
  - Redis不可用时回退到单机模式
- **优势**：
  - 环境适应性强
  - 部署灵活
  - 开发和生产环境配置统一

#### 队列类型选择指南

Crawlo支持三种队列类型，可通过`QUEUE_TYPE`配置项设置：

- **memory**：使用内存队列，适用于单机模式
- **redis**：使用Redis队列，适用于分布式模式
- **auto**：自动检测模式，根据Redis可用性自动选择

推荐使用`auto`模式，让框架根据环境自动选择最适合的队列类型。

<!-- 配置系统 section -->
<h2 align="center">🎛️ 配置系统</h2>

### 传统配置方式

```
# settings.py
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
QUEUE_TYPE = 'memory'  # 单机模式
# QUEUE_TYPE = 'redis'   # 分布式模式

# Redis 配置 (分布式模式下使用)
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ''

# 数据管道配置
# 注意：框架默认管道已自动加载，此处仅用于添加自定义管道
CUSTOM_PIPELINES = [
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',      # MySQL存储管道
]

# 高级日志配置
LOG_FILE = 'logs/spider.log'
LOG_LEVEL = 'INFO'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
LOG_JSON_FORMAT = False  # 设置为True启用JSON格式

# 启用高级日志扩展
ADVANCED_LOGGING_ENABLED = True

# 启用日志监控
LOG_MONITOR_ENABLED = True
LOG_MONITOR_INTERVAL = 30
LOG_MONITOR_DETAILED_STATS = True

# 添加扩展（注意：框架默认扩展已自动加载，此处仅用于添加自定义扩展）
CUSTOM_EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]
```

### MySQL 管道配置

Crawlo 提供了现成的 MySQL 管道实现，可以轻松将爬取的数据存储到 MySQL 数据库中：

```
# 在 settings.py 中启用 MySQL 管道
CUSTOM_PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# MySQL 数据库配置
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'your_username'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'your_database'
MYSQL_TABLE = 'your_table_name'

# 可选的批量插入配置
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = True
```

MySQL 管道特性：
- **异步操作**：基于 asyncmy 驱动，提供高性能的异步数据库操作
- **连接池**：自动管理数据库连接，提高效率
- **批量插入**：支持批量插入以提高性能
- **事务支持**：确保数据一致性
- **灵活配置**：支持自定义表名、批量大小等参数

### 命令行配置

```
# 运行单个爬虫
crawlo run myspider

# 运行所有爬虫
crawlo run all

# 在项目子目录中也能正确运行
cd subdirectory
crawlo run myspider
```

---

<!-- 核心组件 section -->
<h2 align="center">🧩 核心组件</h2>

### Request类

Request类是Crawlo框架中用于封装HTTP请求的核心组件，提供了丰富的功能来处理各种类型的HTTP请求。

#### 基本用法

```python
from crawlo import Request

# 创建一个基本的GET请求
request = Request('https://example.com')

# 创建带回调函数的请求
request = Request('https://example.com', callback=self.parse)
```

#### params参数（GET请求参数）

使用`params`参数来添加GET请求的查询参数，这些参数会自动附加到URL上：

```python
# GET请求带参数
request = Request(
    url='https://httpbin.org/get',
    params={'key1': 'value1', 'key2': 'value2', 'page': 1},
    callback=self.parse
)
# 实际请求URL会变成: https://httpbin.org/get?key1=value1&key2=value2&page=1

# 复杂参数示例
request = Request(
    url='https://api.example.com/search',
    params={
        'q': 'python爬虫',
        'sort': 'date',
        'order': 'desc',
        'limit': 20
    },
    callback=self.parse_results
)
```

对于GET请求，如果同时指定了[params](file:///Users/oscar/projects/Crawlo/crawlo/network/request.py#L55-L55)和[form_data](file:///Users/oscar/projects/Crawlo/crawlo/network/request.py#L53-L53)参数，它们都会被作为查询参数附加到URL上。

#### form_data参数（POST表单数据）

使用`form_data`参数发送表单数据，会根据请求方法自动处理：

```python
# POST请求发送表单数据
request = Request(
    url='https://httpbin.org/post',
    method='POST',
    form_data={
        'username': 'crawlo_user',
        'password': 'secret_password',
        'remember_me': 'true'
    },
    callback=self.parse_login
)

# GET请求使用form_data（会自动转换为查询参数）
request = Request(
    url='https://httpbin.org/get',
    method='GET',
    form_data={
        'search': 'crawlo framework',
        'category': 'documentation'
    },
    callback=self.parse_search
)
```

对于POST请求，[form_data](file:///Users/oscar/projects/Crawlo/crawlo/network/request.py#L53-L53)会被编码为`application/x-www-form-urlencoded`格式并作为请求体发送。

#### json_body参数（JSON请求体）

使用`json_body`参数发送JSON数据：

```python
# 发送JSON数据
request = Request(
    url='https://api.example.com/users',
    method='POST',
    json_body={
        'name': 'Crawlo User',
        'email': 'user@example.com',
        'preferences': {
            'theme': 'dark',
            'notifications': True
        }
    },
    callback=self.parse_response
)

# PUT请求更新资源
request = Request(
    url='https://api.example.com/users/123',
    method='PUT',
    json_body={
        'name': 'Updated Name',
        'email': 'updated@example.com'
    },
    callback=self.parse_update
)
```

使用[json_body](file:///Users/oscar/projects/Crawlo/crawlo/network/request.py#L54-L54)时，会自动设置`Content-Type: application/json`请求头，并将数据序列化为JSON格式。

#### 混合使用参数

可以同时使用多种参数类型，框架会自动处理：

```python
# GET请求同时使用params和form_data（都会作为查询参数）
request = Request(
    url='https://api.example.com/search',
    params={'category': 'books'},           # 作为查询参数
    form_data={'q': 'python', 'limit': 10}, # 也作为查询参数
    callback=self.parse_search
)

# POST请求使用form_data和headers
request = Request(
    url='https://api.example.com/upload',
    method='POST',
    form_data={'title': 'My Document'},
    headers={'Authorization': 'Bearer token123'},
    callback=self.parse_upload
)
```

#### 请求配置

Request类支持丰富的配置选项：

```python
request = Request(
    url='https://example.com',
    method='GET',
    headers={'User-Agent': 'Crawlo Bot'},
    cookies={'session_id': 'abc123'},
    priority=RequestPriority.HIGH,
    timeout=30,
    proxy='http://proxy.example.com:8080',
    dont_filter=True,  # 跳过去重检查
    meta={'custom_key': 'custom_value'},  # 传递自定义元数据
    callback=self.parse
)
```

#### 链式调用

Request类支持链式调用来简化配置：

```python
request = Request('https://example.com')\
    .add_header('User-Agent', 'Crawlo Bot')\
    .set_proxy('http://proxy.example.com:8080')\
    .set_timeout(30)\
    .add_flag('important')\
    .set_meta('custom_key', 'custom_value')
```

#### 优先级设置

Crawlo提供了多种预定义的请求优先级：

```python
from crawlo import Request, RequestPriority

# 设置不同的优先级
urgent_request = Request('https://example.com', priority=RequestPriority.URGENT)
high_request = Request('https://example.com', priority=RequestPriority.HIGH)
normal_request = Request('https://example.com', priority=RequestPriority.NORMAL)
low_request = Request('https://example.com', priority=RequestPriority.LOW)
background_request = Request('https://example.com', priority=RequestPriority.BACKGROUND)
```

#### 动态加载器

对于需要JavaScript渲染的页面，可以启用动态加载器：

```python
# 启用动态加载器
request = Request('https://example.com')\
    .set_dynamic_loader(use_dynamic=True)

# 或者使用链式调用
request = Request('https://example.com')\
    .set_dynamic_loader(True, {'wait_time': 3, 'timeout': 30})
```

### 中间件系统
灵活的中间件系统，支持请求预处理、响应处理和异常处理。

Crawlo框架内置了多种中间件，其中代理中间件有两种实现：

1. **ProxyMiddleware（复杂版）**：
   - 动态从API获取代理
   - 代理池管理
   - 健康检查和成功率统计
   - 复杂的代理提取逻辑
   - 适用于需要高级代理管理功能的场景

2. **SimpleProxyMiddleware（简化版）**：
   - 基于固定代理列表的简单实现
   - 轻量级，代码简洁
   - 易于配置和使用
   - 适用于只需要基本代理功能的场景

如果需要使用简化版代理中间件，可以在配置文件中替换默认的代理中间件：

```python
# settings.py
MIDDLEWARES = [
    # 注释掉复杂版代理中间件
    # 'crawlo.middleware.proxy.ProxyMiddleware',
    # 启用简化版代理中间件
    'crawlo.middleware.simple_proxy.SimpleProxyMiddleware',
]

# 配置代理列表
PROXY_ENABLED = True
PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
]
```

有关代理中间件的详细使用说明，请参考[代理中间件示例项目](examples/simple_proxy_example/)。

### 管道系统
可扩展的数据处理管道，支持多种存储方式（控制台、数据库等）和去重功能：
- **ConsolePipeline**: 控制台输出管道
- **JsonPipeline**: JSON文件存储管道
- **RedisDedupPipeline**: Redis去重管道，基于Redis集合实现分布式去重
- **AsyncmyMySQLPipeline**: MySQL数据库存储管道，基于asyncmy驱动

### 扩展组件
功能增强扩展，包括日志、监控、性能分析等：
- **LogIntervalExtension**: 定时日志扩展
- **LogStats**: 统计日志扩展
- **CustomLoggerExtension**: 自定义日志扩展
- **MemoryMonitorExtension**: 内存监控扩展（监控爬虫进程内存使用情况）
- **PerformanceProfilerExtension**: 性能分析扩展
- **HealthCheckExtension**: 健康检查扩展
- **RequestRecorderExtension**: 请求记录扩展

### 过滤系统
智能去重过滤，支持多种去重策略（内存、Redis、Bloom Filter）。

---

<!-- 示例项目 section -->
<h2 align="center">📦 示例项目</h2>

- [OFweek分布式爬虫](examples/ofweek_distributed/) - 复杂的分布式爬虫示例，包含Redis去重功能
- [OFweek独立爬虫](examples/ofweek_standalone/) - 独立运行的爬虫示例
- [OFweek混合模式爬虫](examples/ofweek_spider/) - 支持单机和分布式模式切换的爬虫示例

---

<!-- 文档 section -->
<h2 align="center">📚 文档</h2>

完整的文档请访问 [Crawlo Documentation](https://crawlo.readthedocs.io/)

- [快速开始指南](docs/modules/index.md)
- [模块化文档](docs/modules/index.md)
- [核心引擎文档](docs/modules/core/engine.md)
- [调度器文档](docs/modules/core/scheduler.md)
- [下载器文档](docs/modules/downloader/index.md)
- [中间件文档](docs/modules/middleware/index.md)
- [管道文档](docs/modules/pipeline/index.md)
- [队列文档](docs/modules/queue/index.md)
- [过滤器文档](docs/modules/filter/index.md)
- [扩展组件文档](docs/modules/extension/index.md)

---

<!-- 贡献 section -->
<h2 align="center">🤝 贡献</h2>

欢迎提交 Issue 和 Pull Request 来帮助改进 Crawlo！

---

<!-- 许可证 section -->
<h2 align="center">📄 许可证</h2>

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE) 文件。