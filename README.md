# 🕷️ Crawlo - 智能异步爬虫框架

> 一个现代化、高性能的 Python 异步爬虫框架，支持单机和分布式模式，开箱即用。

🚀 **核心特色**：默认单机模式，一键分布式，配置优雅，扩展灵活。

---

## ✨ 核心特性

### 🎯 运行模式
- **单机模式**（默认）：零配置启动，适合开发和中小规模爬取
- **分布式模式**：Redis 队列，多节点协同，适合大规模生产环境
- **自动模式**：智能检测 Redis 可用性，自动选择最佳运行方式

### 🛠️ 开发友好
- ✅ **命令行驱动**：`crawlo startproject`、`crawlo genspider`、`crawlo run`
- ✅ **自动发现爬虫**：无需手动注册，自动加载 `spiders/` 模块
- ✅ **智能配置系统**：配置工厂 + 链式调用 + 预设配置
- ✅ **灵活运行参数**：`--env`、`--concurrency`、`--debug`、`--distributed`

### ⚡ 高性能架构
- ✅ **异步核心**：基于 `asyncio` 实现高并发抓取
- ✅ **多下载器支持**：aiohttp、httpx、curl-cffi（浏览器指纹）
- ✅ **智能中间件**：请求去重、延迟控制、重试机制、代理支持
- ✅ **分布式去重**：Redis 分布式去重，避免重复爬取

### 📊 监控与管理
- ✅ **实时统计**：爬取进度、成功率、错误统计
- ✅ **日志系统**：结构化日志输出，支持文件和控制台
- ✅ **健康检查**：`crawlo check` 验证爬虫定义是否合规
- ✅ **性能分析**：`crawlo stats` 查看历史运行指标

---

## 🌐 语言选择 / Language

- [中文文档 (默认)](#中文文档)
- [English Documentation](#english-documentation)

---

## 📚 中文文档

详细的框架文档现已可用，提供中英文双语版本，默认使用中文：

### 快速入门
- [快速入门指南](docs/quick_start_guide_zh.md) - 快速上手 Crawlo
- [框架完整文档](docs/crawlo_framework_documentation_zh.md) - 框架所有特性的综合指南
- [API 参考](docs/api_reference_zh.md) - 所有类和方法的详细文档

### 高级主题
- [分布式爬取教程](docs/distributed_crawling_tutorial_zh.md) - 分布式爬取的完整指南
- [配置最佳实践](docs/configuration_best_practices_zh.md) - 配置 Crawlo 项目的指南
- [去重管道指南](docs/deduplication_pipelines_guide.md) - 所有去重管道的详细指南
- [去重配置说明](docs/deduplication_configuration_zh.md) - 如何为不同模式配置去重
- [示例项目](examples/) - 真实项目的完整示例

---

## 📚 English Documentation

Comprehensive framework documentation is now available in both Chinese and English, with Chinese as the default:

### Getting Started
- [Quick Start Guide](docs/quick_start_guide.md) - Get up and running with Crawlo quickly
- [Framework Documentation](docs/crawlo_framework_documentation.md) - Comprehensive guide to all framework features
- [API Reference](docs/api_reference.md) - Detailed documentation of all classes and methods

### Advanced Topics
- [Distributed Crawling Tutorial](docs/distributed_crawling_tutorial.md) - Complete guide to setting up distributed crawling
- [Configuration Best Practices](docs/configuration_best_practices.md) - Guidelines for configuring Crawlo projects
- [Deduplication Pipelines Guide](docs/deduplication_pipelines_guide.md) - Detailed guide to all deduplication pipelines
- [Deduplication Configuration](docs/deduplication_configuration.md) - How to configure deduplication for different modes

---

## 🚀 快速开始

### 1. 安装框架

```bash
# 从源码安装（推荐）
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -e .

# 或直接安装（开发中）
pip install crawlo
```

### 2. 创建项目

```bash
# 创建新项目
crawlo startproject myproject
cd myproject

# 项目结构
# myproject/
# ├── crawlo.cfg          # 项目配置
# ├── myproject/
# │   ├── __init__.py
# │   ├── settings.py     # 设置文件
# │   ├── items.py        # 数据项定义
# │   └── spiders/        # 爬虫目录
# └── run.py              # 运行脚本
```

### 3. 生成爬虫

```bash
# 生成爬虫模板
crawlo genspider example example.com
```

生成的爬虫代码：

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

### 4. 运行爬虫

```bash
# 🏠 单机模式（默认）
python run.py example

# 🌐 分布式模式
python run.py example --distributed

# 🛠️ 开发环境
python run.py example --env development --debug

# ⚡ 自定义并发
python run.py example --concurrency 20 --delay 0.5

# 🔄 使用预设配置
python run.py example --env production
```

---

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

### 🆕 智能配置工厂

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

### 🎯 预设配置

| 配置 | 适用场景 | 特点 |
|------|----------|------|
| `development()` | 开发调试 | 低并发、详细日志、调试友好 |
| `production()` | 生产环境 | 高性能、自动模式、稳定可靠 |
| `large_scale()` | 大规模爬取 | 分布式、内存优化、批处理 |
| `gentle()` | 温和模式 | 低负载、对目标服务器友好 |

---

## 🌐 分布式架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  节点 A     │    │  节点 B     │    │  节点 N     │
│ (爬虫实例)   │    │ (爬虫实例)   │    │ (爬虫实例)   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
              ┌───────────▼────────────┐
              │     Redis 集群        │
              │ ┌─────────────────────┐│
              │ │ 任务队列 (Queue)    ││
              │ │ 去重集合 (Filter)   ││
              │ │ 统计监控 (Stats)    ││
              │ └─────────────────────┘│
              └─────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │    共享数据存储       │
              │   MySQL / MongoDB    │
              └─────────────────────────┘
```

### 分布式特性

- **🔄 自动负载均衡**：节点间自动分配任务
- **🛡️ 分布式去重**：避免重复爬取
- **📈 水平扩展**：动态增减节点
- **🔧 故障恢复**：节点故障不影响整体运行

---

## 🛠️ 命令行工具

| 命令 | 功能 | 示例 |
|------|------|------|
| `startproject` | 创建新项目 | `crawlo startproject myproject` |
| `genspider` | 生成爬虫 | `crawlo genspider news news.com` |
| `list` | 列出所有爬虫 | `crawlo list` |
| `check` | 检查爬虫合规性 | `crawlo check` |
| `run` | 运行爬虫 | `crawlo run news --distributed` |
| `stats` | 查看统计信息 | `crawlo stats news` |

---

## 📖 完整示例

我们提供了基于真实项目的完整示例，帮助您快速上手：

### 🏠 单机版示例

```bash
# 进入单机版示例
cd examples/telecom_licenses_standalone

# 零配置运行（使用默认 httpx 下载器）
python run.py telecom_device

# 开发环境配置
python run.py telecom_device --env development --concurrency 4

# 调试模式（详细日志）
python run.py telecom_device --debug

# 自定义下载器（在项目 settings.py 中配置）
# DOWNLOADER_TYPE = 'aiohttp'    # 高性能下载器
# DOWNLOADER_TYPE = 'curl_cffi'  # 浏览器指纹模拟
```

**特点**：
- ✅ 零配置启动，开箱即用
- ✅ 内存队列，速度快
- ✅ 适合开发调试和中小规模爬取

### 🌐 分布式示例

```bash
# 进入分布式示例
cd examples/telecom_licenses_distributed

# 启动 Redis
redis-server

# 启动分布式爬虫（使用默认 aiohttp 下载器）
python run.py telecom_device --distributed

# 高并发分布式模式
python run.py telecom_device --distributed --concurrency 30

# 多节点部署
# 机器A (Redis服务器)
python run.py telecom_device

# 机器B
python run.py telecom_device --redis-host 192.168.1.100 --concurrency 16

# 机器C
python run.py telecom_device --redis-host 192.168.1.100 --concurrency 24

# 环境变量配置
NODE_ID=node-1 REDIS_HOST=192.168.1.100 python run.py telecom_device --distributed
```

**特点**：
- ✅ 多节点协同，高并发
- ✅ Redis 队列和去重
- ✅ 适合大规模生产环境

### 📚 详细教程

- **[单机版示例说明](examples/telecom_licenses_standalone/)**：从创建到运行的完整流程
- **[分布式版示例说明](examples/telecom_licenses_distributed/)**：分布式架构和部署方案
- **[examples/README.md](examples/README.md)**：完整示例说明

---

## 🎯 使用场景对比

| 特性 | 单机版 | 分布式版 |
|-----|--------|----------|
| **配置复杂度** | 零配置 | 需要 Redis |
| **外部依赖** | 无 | Redis + 数据库 |
| **并发能力** | 中等 | 高 |
| **扩展性** | 有限 | 水平扩展 |
| **适用场景** | 开发测试、中小规模 | 生产环境、大规模 |
| **学习难度** | 简单 | 中等 |

---

## 🔧 高级功能

### 多下载器支持

```python
# 方式1: 使用简化名称（推荐）
DOWNLOADER_TYPE = 'aiohttp'    # 高性能默认选择
DOWNLOADER_TYPE = 'httpx'      # HTTP/2 支持
DOWNLOADER_TYPE = 'curl_cffi'  # 浏览器指纹模拟

# 方式2: 完整类路径（兼容旧版本）
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# 方式3: 在 Spider 中动态选择
class MySpider(Spider):
    custom_settings = {
        'DOWNLOADER_TYPE': 'curl_cffi',  # 需要浏览器指纹时
        'CURL_BROWSER_TYPE': 'chrome136'
    }

# 下载器特定配置
CURL_BROWSER_TYPE = "chrome136"         # curl-cffi 模拟浏览器
HTTPX_HTTP2 = True                      # httpx 启用 HTTP/2
CONNECTION_POOL_LIMIT_PER_HOST = 20     # 连接池优化
```

### 智能中间件

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',   # 请求过滤
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',   # 延迟控制
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',   # 默认请求头
    'crawlo.middleware.proxy.ProxyMiddleware',                    # 代理支持
    'crawlo.middleware.retry.RetryMiddleware',                    # 重试机制
    'crawlo.middleware.response_code.ResponseCodeMiddleware',     # 状态码处理
]
```

### 数据管道

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',          # 控制台输出
    'crawlo.pipelines.json_pipeline.JsonPipeline',               # JSON 文件（逐行）
    'crawlo.pipelines.json_pipeline.JsonLinesPipeline',          # JSON Lines 格式
    'crawlo.pipelines.json_pipeline.JsonArrayPipeline',          # JSON 数组格式
    'crawlo.pipelines.csv_pipeline.CsvPipeline',                 # CSV 文件
    'crawlo.pipelines.csv_pipeline.CsvDictPipeline',             # CSV 字典格式
    'crawlo.pipelines.csv_pipeline.CsvBatchPipeline',            # CSV 批量写入
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',      # MySQL 数据库（推荐）
    'crawlo.pipelines.mysql_pipeline.AiomysqlMySQLPipeline',     # MySQL 数据库（备选）
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',             # MongoDB
    'crawlo.pipelines.mongo_pipeline.MongoPoolPipeline',         # MongoDB 连接池版本
]
```

### 智能去重配置

Crawlo 框架根据运行模式自动选择合适的去重管道：

- **单机模式**：默认使用内存去重管道 ([MemoryDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/memory_dedup_pipeline.py#L25-L115))
- **分布式模式**：默认使用 Redis 去重管道 ([RedisDedupPipeline](file://d:/dowell/projects/Crawlo/crawlo/pipelines/redis_dedup_pipeline.py#L33-L162))

用户也可以手动指定其他去重管道：

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.BloomDedupPipeline': 100,  # 使用Bloom Filter去重
    'crawlo.pipelines.ConsolePipeline': 300,
}
```

更多去重配置信息请参阅：
- [去重管道指南](docs/deduplication_pipelines_guide.md)
- [去重配置说明](docs/deduplication_configuration_zh.md)

---

## 📊 监控与运维

### 实时监控

```bash
# 查看运行统计
crawlo stats

# 查看特定爬虫
crawlo stats my_spider

# Redis 队列监控
redis-cli llen crawlo:requests
redis-cli scard crawlo:fingerprint
```

### 日志系统

```python
# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/crawlo.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
```

### 性能调优

```python
# 并发控制
CONCURRENCY = 16                    # 并发请求数
DOWNLOAD_DELAY = 1.0               # 下载延迟
CONNECTION_POOL_LIMIT = 100        # 全局连接池大小
CONNECTION_POOL_LIMIT_PER_HOST = 30 # 每个主机连接数

# 重试策略
MAX_RETRY_TIMES = 3                # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503] # 重试状态码

# 统计和监控（新增）
DOWNLOADER_STATS = True            # 启用下载器统计
DOWNLOAD_STATS = True              # 记录下载时间和大小
DOWNLOADER_HEALTH_CHECK = True     # 下载器健康检查
REQUEST_STATS_ENABLED = True       # 请求统计
```

---

## 🚀 最佳实践

### 1. 开发阶段
```bash
# 使用开发配置，低并发，详细日志
python run.py my_spider --env development --debug
```

### 2. 测试阶段
```bash
# 干运行模式，验证逻辑
python run.py my_spider --dry-run
```

### 3. 生产环境
```bash
# 使用生产配置或分布式模式
python run.py my_spider --env production
python run.py my_spider --distributed --concurrency 50
```

### 4. 大规模爬取
```bash
# 使用大规模配置，启用分布式
python run.py my_spider --env large-scale
```

### 5. 下载器选择最佳实践
```python
# 开发/测试环境 - 使用 httpx（稳定、兼容性好）
DOWNLOADER_TYPE = 'httpx'

# 生产环境 - 使用 aiohttp（高性能）
DOWNLOADER_TYPE = 'aiohttp'

# 反爬虫场景 - 使用 curl_cffi（浏览器指纹）
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'
```

---

## 💡 核心优势

### 🎯 开箱即用
- **零配置启动**：默认单机模式，无需复杂配置
- **智能检测**：自动发现爬虫，智能选择运行模式
- **预设配置**：内置多种场景的最佳实践配置

### 🔧 灵活配置
- **配置工厂**：链式调用，代码即配置
- **多下载器支持**：简化配置，支持 aiohttp、httpx、curl_cffi
- **环境变量**：支持容器化部署
- **多种模式**：单机、分布式、自动模式

### ⚡ 高性能
- **异步架构**：基于 asyncio 的高并发设计
- **多下载器**：aiohttp、httpx、curl_cffi 灵活选择
- **智能去重**：内存/Redis 分布式去重
- **负载均衡**：多节点自动任务分配
- **性能监控**：实时统计和健康检查

### 🛡️ 生产就绪
- **容错机制**：节点故障自动恢复
- **监控系统**：完善的统计和监控
- **扩展能力**：水平扩展，按需增减节点

---

## 🆚 与其他框架对比

| 特性 | Crawlo | Scrapy | 其他框架 |
|------|--------|--------|---------|
| **学习曲线** | 简单 | 中等 | 复杂 |
| **配置方式** | 智能配置工厂 | 传统配置 | 手动配置 |
| **分布式** | 一键切换 | 需要 Scrapyd | 复杂 |
| **默认模式** | 单机零配置 | 单机 | 各异 |
| **运行方式** | 多种灵活选项 | 命令行 | 各异 |
| **现代化** | 现代 Python | 传统 | 各异 |

---

## 📞 支持与贡献

### 🐛 问题反馈
- **GitHub Issues**：[提交问题](https://github.com/yourname/crawlo/issues)
- **文档**：查看 [examples/README.md](examples/README.md) 获取更多示例

### 🤝 参与贡献
- **Fork 项目**：欢迎提交 Pull Request
- **改进文档**：帮助完善文档和示例
- **分享经验**：分享使用经验和最佳实践

### 📋 开发路线图
- [ ] 图形化管理界面
- [ ] 更多数据存储支持
- [ ] 云原生部署方案
- [ ] 智能反爬虫对抗
- [ ] 可视化监控面板

---

## 📄 许可证

MIT License - 自由使用，商业友好

---

**🎉 立即开始您的爬虫之旅！**

```bash
git clone https://github.com/yourname/crawlo.git
cd crawlo
pip install -e .
crawlo startproject my_first_spider
```