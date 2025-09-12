# Crawlo 框架示例项目

本目录包含 Crawlo 框架的各种使用示例，帮助开发者快速上手和理解框架功能。

## 示例项目列表

1. [ofweek_spider](ofweek_spider/) - Ofweek 网站爬虫示例（混合版）
2. [ofweek_standalone](ofweek_standalone/) - Ofweek 网站爬虫示例（独立单机版）
3. [ofweek_distributed](ofweek_distributed/) - Ofweek 网站爬虫示例（独立分布式版）

## 使用说明

每个示例项目都包含完整的项目结构和运行说明，可以直接使用 Crawlo 命令运行。

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

## 📚 相关文档

- [Crawlo 框架文档](https://crawlo.readthedocs.io/)
- [框架命令参考](../crawlo/commands/)
- [默认配置说明](../crawlo/settings/default_settings.py)
- [项目模板](../crawlo/templates/)

---

**注意**: 本示例严格按照Crawlo框架标准流程创建，展示了从零开始使用框架命令构建完整爬虫项目的最佳实践.