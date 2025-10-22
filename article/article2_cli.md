# Crawlo CLI工具完全使用指南

## 引言

命令行界面（CLI）是Crawlo框架的重要组成部分，它为用户提供了一套完整的工具来管理网络爬虫项目。通过CLI工具，用户可以快速创建项目、生成爬虫、运行爬虫和管理爬虫任务，大大简化了爬虫开发和管理流程。

本文将详细介绍Crawlo CLI工具的各项功能和使用方法，帮助用户高效地使用这些工具。

## 工具概述

Crawlo CLI工具采用模块化设计，每个命令都有特定的功能，用户可以通过简单的命令行操作完成复杂的爬虫管理任务。

### 核心命令

1. **startproject** - 创建新的爬虫项目
2. **genspider** - 生成新的爬虫模板
3. **run** - 运行爬虫
4. **list** - 列出可用的爬虫
5. **check** - 检查项目配置
6. **stats** - 查看爬虫统计信息

## 安装和基本使用

### 安装

CLI工具随Crawlo框架一起安装：

```bash
pip install crawlo
```

### 基本使用

安装后，可以通过`crawlo`命令访问所有CLI工具：

```bash
# 查看帮助信息
crawlo --help

# 查看特定命令的帮助信息
crawlo <command> --help
```

## 核心命令详解

### startproject命令

`startproject`命令用于创建新的爬虫项目，提供标准的项目结构和基础配置。

#### 命令语法

```bash
crawlo startproject <project_name> [project_dir]
```

#### 参数说明

- `project_name` - 项目名称（必需）
- `project_dir` - 项目目录路径（可选，默认为当前目录）

#### 使用示例

```bash
# 在当前目录创建项目
crawlo startproject myproject

# 使用特定模板创建项目（settings模版）
crawlo startproject myproject distributed

# 创建项目并选择模块组件
crawlo startproject myproject --modules mysql,redis

# 使用特定模板并选择模块组件
crawlo startproject myproject high-performance --modules mysql,proxy,monitoring
```

#### 项目结构

创建的项目包含以下标准结构：

```
myproject/
├── crawlo.cfg                 # 项目配置文件
├── run.py                     # 项目启动脚本
├── logs/                      # 日志目录
├── output/                    # 数据输出目录
└── myproject/                 # 项目根目录
    ├── settings.py            # 项目配置文件
    ├── items.py              # 数据项定义
    ├── pipelines.py          # 数据管道
    ├── middlewares.py        # 中间件
    ├── extensions.py         # 扩展
    ├── spiders/              # 爬虫目录
    │   ├── __init__.py
    │   └── example.py        # 示例爬虫
    ├── utils/                # 工具模块
    │   └── __init__.py
    ├── tests/                # 测试目录
    │   └── __init__.py
    ├── requirements.txt      # 依赖列表
    └── README.md             # 项目说明
```

#### 配置选项

`startproject`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --list-templates | flag | - | 列出所有可用模板 |
| --force | flag | - | 强制覆盖已存在的项目 |
| --verbose | flag | - | 显示详细输出 |
| --modules | string | - | 选择要包含的模块组件，多个模块用逗号分隔 |

#### 模板类型

`startproject`命令支持以下模板类型：

| 模板类型 | 描述 |
|---------|------|
| default | 默认模板 - 通用配置，适合大多数项目 |
| simple | 简化模板 - 最小配置，适合快速开始 |
| distributed | 分布式模板 - 针对分布式爬取优化 |
| high-performance | 高性能模板 - 针对大规模高并发优化 |
| gentle | 温和模板 - 低负载配置，对目标网站友好 |

#### 使用示例

```bash
# 在当前目录创建项目
crawlo startproject myproject

# 使用特定模板创建项目（settings模版）
crawlo startproject myproject distributed

# 创建项目并选择模块组件
crawlo startproject myproject --modules mysql,redis

# 使用特定模板并选择模块组件
crawlo startproject myproject high-performance --modules mysql,proxy,monitoring
```

### genspider命令

`genspider`命令用于生成新的爬虫模板，快速创建爬虫类的基础结构。

#### 命令语法

```bash
crawlo genspider <spider_name> <domain> [options]
```

#### 参数说明

- `spider_name` - 爬虫名称（必需）
- `domain` - 目标域名（必需）
- `options` - 可选参数

#### 使用示例

```
# 生成基本爬虫
crawlo genspider myspider example.com

# 指定模块目录
crawlo genspider myspider example.com --module mymodule

# 生成爬虫到指定文件
crawlo genspider myspider example.com --output myspider.py
```

#### 配置选项

`genspider`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --module | string | 'spiders' | 爬虫模块目录 |
| --output | string | - | 输出文件路径 |

### run命令

`run`命令用于运行指定的爬虫，是执行爬虫任务的主要命令。

#### 命令语法

```bash
crawlo run <spider_name> [options]
```

#### 参数说明

- `spider_name` - 要运行的爬虫名称（必需）
- `options` - 可选参数

#### 使用示例

```
# 运行爬虫
crawlo run myspider

# 设置日志级别
crawlo run myspider --log-level DEBUG

# 设置并发数
crawlo run myspider --concurrency 32
```

#### 配置选项

`run`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --json | flag | - | 以JSON格式输出结果 |
| --no-stats | flag | - | 不记录统计信息 |
| --log-level | string | 'INFO' | 日志级别 (DEBUG, INFO, WARNING, ERROR) |
| --concurrency | int | 16 | 并发请求数 |

### list命令

`list`命令用于列出项目中所有可用的爬虫，帮助用户了解项目结构和可用的爬虫。

#### 命令语法

```bash
crawlo list [options]
```

#### 参数说明

- `options` - 可选参数

#### 使用示例

```
# 列出所有爬虫
crawlo list

# 指定项目目录
crawlo list --project-dir /path/to/project

# 以JSON格式输出
crawlo list --format json
```

#### 配置选项

`list`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --json | flag | - | 以JSON格式输出结果 |

### check命令

`check`命令用于检查项目配置和爬虫实现，帮助发现潜在问题和错误。

#### 命令语法

```bash
crawlo check [spider_name] [options]
```

#### 参数说明

- `spider_name` - 要检查的爬虫名称（可选，不指定则检查整个项目）
- `options` - 可选参数

#### 使用示例

```
# 检查整个项目
crawlo check

# 检查特定爬虫
crawlo check myspider

# 指定项目目录
crawlo check --project-dir /path/to/project
```

#### 配置选项

`check`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --fix | flag | - | 自动修复发现的问题 |
| --ci | flag | - | CI模式，适合在持续集成环境中使用 |
| --json | flag | - | 以JSON格式输出结果 |
| --watch | flag | - | 监听模式，监听爬虫文件变更并自动检查 |

### stats命令

`stats`命令用于查看爬虫运行统计信息，帮助监控爬虫性能和状态。

#### 命令语法

```bash
crawlo stats [spider_name] [options]
```

#### 参数说明

- `spider_name` - 要查看统计信息的爬虫名称（可选，不指定则显示所有爬虫）
- `options` - 可选参数

#### 使用示例

```
# 查看所有爬虫统计信息
crawlo stats

# 查看特定爬虫统计信息
crawlo stats myspider

# 实时监控统计信息
crawlo stats --follow
```

#### 配置选项

`stats`命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --all | flag | - | 显示指定爬虫的所有历史记录 |

## 全局选项

所有CLI命令都支持以下全局选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --help | flag | - | 显示帮助信息 |
| --version | flag | - | 显示版本信息 |

## 环境变量

CLI工具支持以下环境变量：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| CRAWLO_MODE | 'standalone' | 运行模式 (standalone/distributed/auto) |
| REDIS_HOST | '127.0.0.1' | Redis服务器地址 |
| REDIS_PORT | 6379 | Redis端口 |
| REDIS_PASSWORD | None | Redis密码 |
| REDIS_DB | 0 | Redis数据库编号 |
| PROJECT_NAME | 'crawlo' | 项目名称 |
| CONCURRENCY | 8/16 | 并发请求数（根据模式不同） |

## 使用示例

### 创建和运行爬虫项目

```
# 1. 创建新项目
crawlo startproject myproject
cd myproject

# 2. 生成爬虫
crawlo genspider myspider example.com

# 3. 编辑爬虫文件
# 编辑 myproject/myproject/spiders/myspider.py

# 4. 运行爬虫
crawlo run myspider

# 5. 查看统计信息
crawlo stats
```

### 配置管理

```
# 使用不同的配置文件
crawlo run myspider --config production_settings.py

# 设置调试模式
crawlo run myspider --log-level DEBUG

# 指定项目目录
crawlo list --project-dir /path/to/myproject
```

## 最佳实践

### 项目结构规范

创建的项目包含以下标准结构：

```
myproject/
├── crawlo.cfg                 # 项目配置文件
├── run.py                     # 项目启动脚本
├── logs/                      # 日志目录
├── output/                    # 数据输出目录
└── myproject/                 # 项目根目录
    ├── settings.py            # 项目配置文件
    ├── items.py              # 数据项定义
    ├── pipelines.py          # 数据管道
    ├── middlewares.py        # 中间件
    ├── extensions.py         # 扩展
    ├── spiders/              # 爬虫目录
    │   ├── __init__.py
    │   └── example.py        # 示例爬虫
    ├── utils/                # 工具模块
    │   └── __init__.py
    ├── tests/                # 测试目录
    │   └── __init__.py
    ├── requirements.txt      # 依赖列表
    └── README.md             # 项目说明
```

### 配置文件管理

```
# 开发环境配置
crawlo run myspider --config settings_dev.py

# 测试环境配置
crawlo run myspider --config settings_test.py

# 生产环境配置
crawlo run myspider --config settings_prod.py
```

### 日志管理

```
# 设置日志级别
crawlo run myspider --log-level INFO

# 输出到文件
crawlo run myspider --log-file crawler.log

# 设置日志轮转
crawlo run myspider --log-max-bytes 10485760 --log-backup-count 5
```

### 性能调优

```
# 调整并发数
crawlo run myspider --concurrency 32

# 设置日志级别为DEBUG以获取更多调试信息
crawlo run myspider --log-level DEBUG
```

## 错误处理

### 常见错误

1. **找不到爬虫**
   ```bash
   crawlo run nonexistentspider
   # 错误: 找不到爬虫 'nonexistentspider'
   ```

2. **配置文件错误**
   ```bash
   crawlo run myspider --config bad_settings.py
   # 错误: 配置文件 'bad_settings.py' 格式错误
   ```

3. **权限错误**
   ```bash
   crawlo startproject myproject /root/projects
   # 错误: 没有权限创建目录
   ```

### 调试技巧

```bash
# 启用详细日志
crawlo run myspider --log-level DEBUG

# 检查配置
crawlo check

# 查看可用爬虫
crawlo list
```

## 总结

Crawlo CLI工具为用户提供了一套完整的命令行接口，涵盖了爬虫开发的整个生命周期。通过这些工具，用户可以快速创建项目、生成爬虫、运行爬虫、检查配置和监控统计信息。

## 项目源码

如需获取Crawlo框架的最新源代码和更多技术文档，欢迎访问我们的GitHub仓库：[https://github.com/crawl-coder/Crawlo.git](https://github.com/crawl-coder/Crawlo.git)。您可以在那里找到完整的项目代码、示例以及参与社区讨论。
