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
    <a href="#-架构设计">架构设计</a> •
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
        <td>基于 asyncio 实现，充分利用现代 CPU 多核性能</td>
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
        <td>📊 <strong>可视化架构</strong></td>
        <td>提供完整的架构图和组件关系图，便于理解和使用</td>
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

```python
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
<h2 align="center">📜 命令行工具</h2>

Crawlo 提供了丰富的命令行工具来帮助开发和管理爬虫项目：

### 获取帮助

```bash
# 显示帮助信息
crawlo -h
crawlo --help
crawlo help
```

### crawlo startproject

创建新的爬虫项目。

```bash
# 基本用法
crawlo startproject <project_name> [template_type] [--modules module1,module2]

# 示例
crawlo startproject my_spider_project
crawlo startproject news_crawler simple
crawlo startproject ecommerce_spider distributed --modules mysql,proxy
```

**参数说明：**
- `project_name`: 项目名称（必须是有效的Python标识符）
- `template_type`: 模板类型（可选）
  - `default`: 默认模板 - 通用配置，适合大多数项目
  - `simple`: 简化模板 - 最小配置，适合快速开始
  - `distributed`: 分布式模板 - 针对分布式爬取优化
  - `high-performance`: 高性能模板 - 针对大规模高并发优化
  - `gentle`: 温和模板 - 低负载配置，对目标网站友好
- `--modules`: 选择要包含的模块组件（可选）
  - `mysql`: MySQL数据库支持
  - `mongodb`: MongoDB数据库支持
  - `redis`: Redis支持（分布式队列和去重）
  - `proxy`: 代理支持
  - `monitoring`: 监控和性能分析
  - `dedup`: 去重功能
  - `httpx`: HttpX下载器
  - `aiohttp`: AioHttp下载器
  - `curl`: CurlCffi下载器

### crawlo genspider

在现有项目中生成新的爬虫。

```bash
# 基本用法
crawlo genspider <spider_name> <domain>

# 示例
crawlo genspider news_spider news.example.com
crawlo genspider product_spider shop.example.com
```

**参数说明：**
- `spider_name`: 爬虫名称（必须是有效的Python标识符）
- `domain`: 目标域名

### crawlo run

运行爬虫。

```bash
# 基本用法
crawlo run <spider_name>|all [--json] [--no-stats]

# 示例
crawlo run myspider
crawlo run all
crawlo run all --json --no-stats
```

**参数说明：**
- `spider_name`: 要运行的爬虫名称
- `all`: 运行所有爬虫
- `--json`: 以JSON格式输出结果
- `--no-stats`: 不记录统计信息

### crawlo list

列出项目中所有可用的爬虫。

```bash
# 基本用法
crawlo list [--json]

# 示例
crawlo list
crawlo list --json
```

**参数说明：**
- `--json`: 以JSON格式输出结果

### crawlo check

检查爬虫定义的合规性。

```bash
# 基本用法
crawlo check [--fix] [--ci] [--json] [--watch]

# 示例
crawlo check
crawlo check --fix
crawlo check --ci
crawlo check --watch
```

**参数说明：**
- `--fix`: 自动修复常见问题
- `--ci`: CI模式输出（简洁格式）
- `--json`: 以JSON格式输出结果
- `--watch`: 监听模式，文件更改时自动检查

### crawlo stats

查看爬虫运行统计信息。

```bash
# 基本用法
crawlo stats [spider_name] [--all]

# 示例
crawlo stats
crawlo stats myspider
crawlo stats myspider --all
```

**参数说明：**
- `spider_name`: 指定要查看统计信息的爬虫名称
- `--all`: 显示指定爬虫的所有历史运行记录

---

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

### 可视化架构图

为了更好地理解Crawlo的架构，我们提供了以下可视化图表：

1. [核心组件关系图](docs/architecture_diagram.md#核心组件关系图) - 展示各组件之间的关系
2. [请求处理流程图](docs/architecture_diagram.md#请求处理流程图) - 展示请求在框架中的处理流程
3. [运行模式切换图](docs/architecture_diagram.md#运行模式切换图) - 展示不同运行模式的切换逻辑
4. [扩展系统架构图](docs/extension_system.md#扩展组件架构图) - 展示扩展系统的架构
5. [下载器系统图](docs/downloader_system.md#下载器架构图) - 展示下载器系统的架构

这些图表使用Mermaid语法编写，您可以使用支持Mermaid的Markdown编辑器或在线工具来渲染查看。

### 模块层次结构

```
crawlo/
├── cli.py                          # 命令行接口
├── crawler.py                      # 爬虫运行实例
├── project.py                      # 项目管理
├── config.py                       # 配置管理
├── mode_manager.py                 # 运行模式管理器
├── stats_collector.py              # 统计收集器
├── subscriber.py                   # 事件订阅器
├── task_manager.py                 # 任务管理器
├── event.py                        # 事件定义
├── exceptions.py                   # 异常定义
├──
├── core/                           # 核心组件
│   ├── engine.py                   # 引擎
│   ├── scheduler.py                # 调度器
│   ├── processor.py                # 处理器
│
├── spider/                         # 爬虫基类
│   └── __init__.py                 # 爬虫元类和基类
│
├── network/                        # 网络相关
│   ├── request.py                  # 请求对象
│   └── response.py                 # 响应对象
│
├── downloader/                     # 下载器
│   ├── __init__.py                 # 下载器基类
│   ├── aiohttp_downloader.py      # AioHttp实现
│   ├── httpx_downloader.py        # HttpX实现
│   └── cffi_downloader.py         # CurlCffi实现
│
├── queue/                          # 队列管理
│   ├── __init__.py                 
│   ├── queue_manager.py           # 队列管理器
│   ├── pqueue.py                  # 内存优先队列
│   └── redis_priority_queue.py    # Redis优先队列
│
├── filters/                        # 过滤器
│   ├── __init__.py                 
│   ├── base_filter.py             # 过滤器基类
│   ├── memory_filter.py           # 内存过滤器
│   └── aioredis_filter.py         # Redis过滤器
│
├── middleware/                     # 中间件
│   ├── __init__.py                 
│   ├── middleware_manager.py      # 中间件管理器
│   ├── default_header.py          # 默认请求头
│   ├── download_delay.py          # 下载延迟
│   ├── proxy.py                   # 代理支持
│   ├── request_ignore.py          # 请求忽略
│   ├── response_code.py           # 响应码处理
│   ├── response_filter.py         # 响应过滤
│   └── retry.py                   # 重试机制
│
├── pipelines/                      # 数据管道
│   ├── __init__.py                 
│   ├── pipeline_manager.py        # 管道管理器
│   ├── base_pipeline.py           # 管道基类
│   ├── console_pipeline.py        # 控制台输出管道
│   ├── json_pipeline.py           # JSON存储管道
│   ├── redis_dedup_pipeline.py    # Redis去重管道
│   └── mysql_pipeline.py          # MySQL存储管道
│
├── extension/                      # 扩展组件
│   ├── __init__.py                 
│   ├── log_interval.py            # 定时日志
│   ├── log_stats.py               # 统计日志
│   ├── logging_extension.py       # 日志扩展
│   ├── advanced_logging_extension.py # 高级日志扩展
│   ├── log_monitor.py             # 日志监控扩展
│   ├── memory_monitor.py          # 内存监控
│   └── performance_profiler.py    # 性能分析
│
├── settings/                       # 配置系统
│   ├── __init__.py                 
│   ├── default_settings.py        # 默认配置
│   └── setting_manager.py         # 配置管理器
│
├── utils/                          # 工具库
│   ├── __init__.py                 
│   ├── log.py                     # 基础日志工具
│   ├── advanced_log.py            # 高级日志工具
│   ├── request.py                 # 请求工具
│   ├── request_serializer.py      # 请求序列化
│   └── func_tools.py              # 函数工具
│
└── templates/                      # 模板文件
    ├── project/                   
    └── spider/
```

---

<!-- 配置系统 section -->
<h2 align="center">🎛️ 配置系统</h2>

### 传统配置方式

```python
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
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',  # Redis去重管道
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

# 添加扩展
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.advanced_logging_extension.AdvancedLoggingExtension',
    'crawlo.extension.log_monitor.LogMonitorExtension',
]
```

### MySQL 管道配置

Crawlo 提供了现成的 MySQL 管道实现，可以轻松将爬取的数据存储到 MySQL 数据库中：

```python
# 在 settings.py 中启用 MySQL 管道
PIPELINES = [
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

### 中间件系统
灵活的中间件系统，支持请求预处理、响应处理和异常处理。

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
- **AdvancedLoggingExtension**: 高级日志扩展
- **LogMonitorExtension**: 日志监控扩展
- **MemoryMonitorExtension**: 内存监控扩展
- **PerformanceProfilerExtension**: 性能分析扩展

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
- [API参考](docs/api_reference.md)
- [配置最佳实践](docs/configuration_best_practices.md)
- [高级日志功能](docs/advanced_logging.md)
- [架构图解](docs/architecture_diagram.md)

---

<!-- 贡献 section -->
<h2 align="center">🤝 贡献</h2>

欢迎提交 Issue 和 Pull Request 来帮助改进 Crawlo！

---

<!-- 许可证 section -->
<h2 align="center">📄 许可证</h2>

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE) 文件。