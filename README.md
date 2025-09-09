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

```
┌─────────────────┐    ┌──────────────┐    ┌──────────────┐
│   Scheduler     │◄──►│   Engine     │◄──►│  Downloader  │
└─────────────────┘    └──────────────┘    └──────────────┘
       │                       │                    │
       ▼                       ▼                    ▼
┌─────────────────┐    ┌──────────────┐    ┌──────────────┐
│     Queue       │    │ Middlewares  │    │   Network    │
└─────────────────┘    └──────────────┘    └──────────────┘
       │                       │
       ▼                       ▼
┌─────────────────┐    ┌──────────────┐
│    Filter       │    │  Pipelines   │
└─────────────────┘    └──────────────┘
                               │
                               ▼
                      ┌──────────────┐
                      │    Items     │
                      └──────────────┘
```

## 🎛️ 配置系统

### 传统配置方式

```python
# settings.py
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
QUEUE_TYPE = 'memory'  # 单机模式
# QUEUE_TYPE = 'redis'   # 分布式模式
```

### 命令行配置

```bash
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

- [快速开始指南](docs/quick_start.md)
- [框架文档](docs/crawlo_framework_documentation.md)
- [API参考](docs/api_reference.md)
- [分布式爬取教程](docs/distributed_crawling_tutorial.md)
- [配置最佳实践](docs/configuration_best_practices.md)
- [扩展组件](docs/extensions.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进 Crawlo！

## 📄 许可证

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE) 文件。
