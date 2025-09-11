# Crawlo - 异步分布式爬虫框架

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://crawlo.readthedocs.io/)

一个基于 asyncio 的高性能异步分布式爬虫框架，支持单机和分布式部署。

</div>

## 🌟 特性

- **异步高性能**: 基于 asyncio 实现，充分利用现代 CPU 多核性能
- **分布式支持**: 内置 Redis 队列，轻松实现分布式部署
- **模块化设计**: 中间件、管道、扩展组件系统，易于定制和扩展
- **智能去重**: 多种去重策略（内存、Redis、Bloom Filter）
- **灵活配置**: 支持多种配置方式，适应不同场景需求
- **丰富文档**: 完整的中英文双语文档和示例项目

## 🚀 快速开始

### 安装

```bash
pip install crawlo
```

### 创建项目

```bash
crawlo startproject myproject
cd myproject
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
crawlo crawl myspider
```

## 🏗️ 架构设计

### 组件交互图

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Crawler                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Spider     │  │   Engine     │  │      ExtensionManager     │  │
│  │              │  │              │  │                          │  │
│  │ start_urls   │  │  Scheduler ◄─┼──┼──► StatsCollector         │  │
│  │ parse()      │  │              │  │                          │  │
│  │              │  │ Downloader ◄─┼──┼──► MiddlewareManager     │  │
│  │              │  │              │  │                          │  │
│  │              │  │ Processor  ◄─┼──┼──► PipelineManager       │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────────┘  │
└──────────────────────────┼─────────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         Scheduler                   │
        │  ┌──────────────────────────────┐   │
        │  │       QueueManager           │   │
        │  │  ┌─────────┐  ┌────────────┐ │   │
        │  │  │ Memory  │  │   Redis    │ │   │
        │  │  │ Queue   │  │  Queue     │ │   │
        │  │  └─────────┘  └────────────┘ │   │
        │  └──────────────────────────────┘   │
        │  ┌──────────────────────────────┐   │
        │  │        Filter                │   │
        │  │  ┌─────────┐  ┌────────────┐ │   │
        │  │  │ Memory  │  │   Redis    │ │   │
        │  │  │ Filter  │  │  Filter    │ │   │
        │  │  └─────────┘  └────────────┘ │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         Downloader                  │
        │  ┌──────────────────────────────┐   │
        │  │    MiddlewareManager         │   │
        │  │                              │   │
        │  │ RequestMiddleware ◄────────┐ │   │
        │  │ ResponseMiddleware        │ │   │
        │  │ ExceptionMiddleware       │ │   │
        │  │                          ╱  │   │
        │  └─────────────────────────╱───┘   │
        │                           ╱        │
        │  ┌───────────────────────▼──┐      │
        │  │  Download Implementations │      │
        │  │  - AioHttpDownloader   │      │
        │  │  - HttpXDownloader     │      │
        │  │  - CurlCffiDownloader  │      │
        │  └──────────────────────────┘      │
        └─────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │          Processor                  │
        │  ┌──────────────────────────────┐   │
        │  │    PipelineManager           │   │
        │  │  ┌─────────────────────────┐ │   │
        │  │  │   Pipeline Stages       │ │   │
        │  │  │ - ValidationPipeline    │ │   │
        │  │  │ - ProcessingPipeline    │ │   │
        │  │  │ - StoragePipeline       │ │   │
        │  │  └─────────────────────────┘ │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
```

### 运行模式切换图

```
                    ┌─────────────────────┐
                    │   ModeManager       │
                    │  (运行模式管理器)    │
                    └─────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐   ┌─────────────────┐
│  Standalone   │    │   Distributed   │   │      Auto       │
│   (单机模式)   │    │   (分布式模式)   │   │   (自动检测模式)  │
└───────┬───────┘    └─────────┬───────┘   └─────────┬───────┘
        │                      │                     │
        ▼                      ▼                     ▼
┌───────────────┐    ┌─────────────────┐   ┌─────────────────┐
│ Memory Queue  │    │   Redis Queue   │   │  Auto Select    │
│ Memory Filter │    │  Redis Filter   │   │ Memory/Redis    │
└───────────────┘    └─────────────────┘   └─────────────────┘
```

### 数据流向图

```
┌─────────────┐    1.生成初始请求     ┌──────────────┐
│   Spider    ├─────────────────────►│  Scheduler   │
└─────────────┘                      └──────┬───────┘
                                            │ 2.去重检查
                                            ▼
                                  ┌─────────────────┐
                                  │     Filter      │
                                  └─────────┬───────┘
                                            │ 3.入队
                                            ▼
                                  ┌─────────────────┐
                                  │      Queue      │
                                  └─────────┬───────┘
                                            │ 4.获取请求
                                            ▼
                                  ┌─────────────────┐    5.下载请求    
                                  │   Downloader    ├──────────────────┐
                                  └─────────────────┘                  │
                                            │ 6.解析响应              │
                                            ▼                         ▼
                                  ┌─────────────────┐    7.生成数据    ┌─────────────┐
                                  │   Processor     ├────────────────►│   Pipeline  │
                                  └─────────────────┘                 └─────────────┘
                                            │ 8.存储数据
                                            ▼
                                  ┌─────────────────┐
                                  │     Items       │
                                  └─────────────────┘
```

### 模块层次结构图

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
│   └── mysql_pipeline.py          # MySQL存储管道
│
├── extension/                      # 扩展组件
│   ├── __init__.py                 
│   ├── log_interval.py            # 定时日志
│   ├── log_stats.py               # 统计日志
│   ├── logging_extension.py       # 日志扩展
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
│   ├── log.py                     # 日志工具
│   ├── request.py                 # 请求工具
│   ├── request_serializer.py      # 请求序列化
│   └── func_tools.py              # 函数工具
│
└── templates/                      # 模板文件
    ├── project/                   
    └── spider/
```

### 组件说明

- **Crawler**: 爬虫运行实例，管理Spider与引擎的生命周期
- **Engine**: 引擎组件，协调Scheduler、Downloader、Processor
- **Scheduler**: 调度器，管理请求队列和去重过滤
- **Downloader**: 下载器，负责网络请求，支持多种实现(aiohttp, httpx, curl-cffi)
- **Processor**: 处理器，处理响应数据和管道
- **QueueManager**: 统一的队列管理器，支持内存队列和Redis队列的自动切换
- **Filter**: 请求去重过滤器，支持内存和Redis两种实现
- **Middleware**: 中间件系统，处理请求/响应的预处理和后处理
- **Pipeline**: 数据处理管道，支持多种存储方式(控制台、数据库等)
- **Spider**: 爬虫基类，定义爬取逻辑

### 运行模式

Crawlo支持三种运行模式：
- **standalone**: 单机模式，使用内存队列和内存过滤器
- **distributed**: 分布式模式，使用Redis队列和Redis过滤器
- **auto**: 自动检测模式，根据环境自动选择最佳运行方式

## 🎛️ 配置系统

### 传统配置方式

```
# settings.py
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
QUEUE_TYPE = 'memory'  # 单机模式
# QUEUE_TYPE = 'redis'   # 分布式模式
```

### 命令行配置

```
crawlo crawl myspider --concurrency=32 --delay=0.5
```

## 🧩 核心组件

### 中间件系统
灵活的中间件系统，支持请求预处理、响应处理和异常处理。

### 管道系统
可扩展的数据处理管道，支持多种存储方式（控制台、数据库等）。

### 扩展组件
功能增强扩展，包括日志、监控、性能分析等。

### 过滤系统
智能去重过滤，支持多种去重策略（内存、Redis、Bloom Filter）。

## 📦 示例项目

- [API数据采集](examples/api_data_collection/) - 简单的API数据采集示例
- [电信设备许可证](examples/telecom_licenses_distributed/) - 分布式爬取示例

## 📚 文档

完整的文档请访问 [Crawlo Documentation](https://crawlo.readthedocs.io/)

- [快速开始指南](docs/modules/index.md)
- [模块化文档](docs/modules/index.md)
- [API参考](docs/api_reference.md)
- [配置最佳实践](docs/configuration_best_practices.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进 Crawlo！

## 📄 许可证

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE) 文件。
