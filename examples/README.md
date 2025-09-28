# Crawlo 框架示例

Crawlo 是一个功能强大的异步爬虫框架，支持单机和分布式模式。本目录包含多个示例项目，展示框架的各种功能和使用方法。

## 示例项目

### 1. 基础示例

- [ofweek_standalone](ofweek_standalone/) - 单机模式基础示例
- [ofweek_distributed](ofweek_distributed/) - 分布式模式基础示例

### 2. 高级功能示例

- [playwright_selenium_example](playwright_selenium_example/) - Playwright 和 Selenium 下载器示例
- [refactored_example](refactored_example/) - 重构后的示例项目
- [advanced_tools_example](advanced_tools_example/) - 高级工具使用示例（工厂模式、批处理工具、受控爬虫混入类、大规模配置工具、大规模爬虫辅助工具）

## 使用说明

每个示例项目都包含完整的项目结构和运行脚本。进入相应的目录并运行 `python run.py` 即可启动示例。

## 示例说明

### ofweek_standalone

展示如何使用 Crawlo 框架的单机模式进行网页爬取。包含完整的项目结构、配置文件和爬虫实现。

### ofweek_distributed

展示如何使用 Crawlo 框架的分布式模式进行网页爬取。需要 Redis 服务器支持。

### playwright_selenium_example

展示如何使用 Playwright 和 Selenium 下载器处理 JavaScript 渲染的页面。

### refactored_example

展示重构后的项目结构，使用更简洁的配置方式。

### advanced_tools_example

展示 Crawlo 框架的高级工具使用方法：

1. **工厂模式相关模块** - 组件创建和依赖注入
2. **批处理工具** - 大规模数据处理
3. **受控爬虫混入类** - 大量请求的并发控制
4. **大规模配置工具** - 针对大规模爬取的优化配置
5. **大规模爬虫辅助工具** - 处理大规模爬取的辅助功能

运行示例：
```bash
cd advanced_tools_example
python run.py help             # 查看帮助信息
python run.py factory          # 工厂模式示例
python run.py batch            # 批处理工具示例
python run.py controlled       # 受控爬虫混入类示例
python run.py large_scale_config  # 大规模配置工具示例
python run.py large_scale_helper  # 大规模爬虫辅助工具示例

# 或者使用独立演示脚本
python demo_tools.py           # 演示所有工具
python demo_tools.py factory   # 演示工厂模式工具
```

## 📁 项目结构

```
examples/
├── ofweek_standalone/              # Ofweek 网站爬虫（独立单机版）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本
│   ├── logs/                        # 日志目录
│   └── ofweek_standalone/
│       ├── __init__.py
│       ├── settings.py              # 单机模式配置
│       ├── items.py                 # 数据结构定义
│       └── spiders/
│           ├── __init__.py
│           └── OfweekSpider.py      # Ofweek 网站爬虫
│
├── ofweek_distributed/             # Ofweek 网站爬虫（独立分布式版）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本
│   ├── logs/                        # 日志目录
│   └── ofweek_distributed/
│       ├── __init__.py
│       ├── settings.py              # 分布式模式配置
│       ├── items.py                 # 数据结构定义
│       └── spiders/
│           ├── __init__.py
│           └── OfweekSpider.py      # Ofweek 网站爬虫
│
├── ofweek_spider/                  # Ofweek 网站爬虫（混合版，支持模式切换）
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 启动脚本（支持模式切换）
│   ├── logs/                        # 日志目录
│   └── ofweek_spider/
│       ├── __init__.py
│       ├── settings.py              # 混合模式配置
│       ├── items.py                 # 数据结构定义
│       └── spiders/
│           ├── __init__.py
│           └── OfweekSpider.py      # Ofweek 网站爬虫
│
├── simple_proxy_example/           # 简化版代理中间件使用示例
│   ├── run.py                       # 启动脚本
│   └── simple_proxy_example/
│       ├── __init__.py
│       ├── settings.py              # 简化版代理配置
│       └── spiders/
│           ├── __init__.py
│           └── example_spider.py    # 示例爬虫
│
├── advanced_tools_example/         # 高级工具使用示例
│   ├── crawlo.cfg                   # 项目配置文件
│   ├── run.py                       # 爬虫运行脚本
│   ├── demo_tools.py                # 独立工具演示脚本
│   ├── README.md                    # 项目说明文档
│   ├── logs/                        # 日志目录
│   ├── output/                      # 输出目录
│   └── advanced_tools_example/
│       ├── __init__.py
│       ├── settings.py              # 配置文件
│       ├── items.py                 # 数据项定义
│       ├── middlewares.py           # 中间件
│       ├── pipelines.py             # 管道
│       └── spiders/                 # 爬虫模块
│           ├── __init__.py
│           ├── factory_example.py          # 工厂模式示例
│           ├── batch_example.py            # 批处理工具示例
│           ├── controlled_example.py       # 受控爬虫混入类示例
│           ├── large_scale_config_example.py    # 大规模配置工具示例
│           └── large_scale_helper_example.py    # 大规模爬虫辅助工具示例
│
└── README.md                        # 本文档
```

## 🎯 项目特点

### 按框架标准创建
- 使用 `crawlo startproject` 命令创建项目结构
- 严格遵循框架默认配置和目录规范
- 基于框架模板进行业务逻辑定制

## Ofweek 爬虫示例

### 项目概述
Ofweek 爬虫示例演示了如何使用 Crawlo 框架创建一个完整的新闻网站爬虫，支持从单机模式到分布式模式的平滑演进。

### 功能特点
- 抓取 [OFweek 电子工程网](https://ee.ofweek.com/) 的新闻文章
- 支持单机模式和分布式模式切换
- 包含完整的数据提取和清洗逻辑
- 提供详细的演进文档和配置示例

### 项目结构

#### 1. [ofweek_standalone](ofweek_standalone/) - 独立单机版
专为单机运行优化的版本，配置简单，无需额外依赖。

#### 2. [ofweek_distributed](ofweek_distributed/) - 独立分布式版
专为分布式部署优化的版本，需要 Redis 环境支持。

#### 3. [ofweek_spider](ofweek_spider/) - 混合版（支持模式切换）
通过环境变量支持单机和分布式模式的无缝切换，便于对比学习。

### 运行方式

#### 独立单机版 (ofweek_standalone)
```bash
cd examples/ofweek_standalone
python run.py
```

#### 独立分布式版 (ofweek_distributed)
```bash
cd examples/ofweek_distributed
# 确保 Redis 服务已启动
python run.py
```

#### 混合版 (ofweek_spider)
```bash
cd examples/ofweek_spider

# 运行单机模式（默认）
python run.py

# 运行分布式模式
export CRAWLO_MODE=distributed
python run.py
```

## 高级工具示例

### 项目概述
[advanced_tools_example](advanced_tools_example/) 演示了 Crawlo 框架中各种高级工具的使用方法，包括工厂模式、批处理工具、受控爬虫混入类、大规模配置工具和大规模爬虫辅助工具。

### 功能特点
- 展示工厂模式在组件创建和依赖注入中的应用
- 演示批处理工具在大规模数据处理中的使用
- 展示受控爬虫混入类在处理大量请求时的并发控制
- 演示大规模配置工具针对不同场景的优化配置
- 展示大规模爬虫辅助工具在处理大规模任务时的支持功能

### 运行方式
```bash
cd examples/advanced_tools_example

# 查看帮助信息
python run.py help

# 运行特定示例
python run.py factory          # 工厂模式示例
python run.py batch            # 批处理工具示例
python run.py controlled       # 受控爬虫混入类示例
python run.py large_scale_config  # 大规模配置工具示例
python run.py large_scale_helper  # 大规模爬虫辅助工具示例

# 或者使用独立演示脚本
python demo_tools.py           # 演示所有工具
python demo_tools.py factory   # 演示特定工具
```

## 简化版代理中间件示例

### 项目概述
[simple_proxy_example](simple_proxy_example/) 演示了如何使用 Crawlo 框架的简化版代理中间件，对比复杂版代理中间件的优势。

### 功能特点
- 使用简单的代理列表配置
- 轻量级实现，代码简洁
- 易于配置和使用
- 适用于只需要基本代理功能的场景

### 运行方式
```bash
cd examples/simple_proxy_example
# 修改 settings.py 中的 PROXY_LIST 配置
python run.py
```

## 📚 相关文档

- [Crawlo 框架文档](https://crawlo.readthedocs.io/)
- [框架命令参考](../crawlo/commands/)
- [默认配置说明](../crawlo/settings/default_settings.py)
- [项目模板](../crawlo/templates/)

---

**注意**: 本示例严格按照Crawlo框架标准流程创建，展示了从零开始使用框架命令构建完整爬虫项目的最佳实践.