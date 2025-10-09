# CLI 工具

Crawlo 提供了丰富的命令行工具，帮助用户快速创建项目、生成爬虫、运行爬虫和管理爬虫任务。

## 工具概述

CLI 工具采用模块化设计，每个命令都有特定的功能，用户可以通过简单的命令行操作完成复杂的爬虫管理任务。

### 核心命令

1. [startproject](startproject.md) - 创建新的爬虫项目
2. [genspider](genspider.md) - 生成新的爬虫模板
3. [run](run.md) - 运行爬虫
4. [list](list.md) - 列出可用的爬虫
5. [check](check.md) - 检查项目配置
6. [stats](stats.md) - 查看爬虫统计信息

## 安装和使用

### 安装

CLI 工具随 Crawlo 框架一起安装：

```bash
pip install crawlo
```

### 基本使用

安装后，可以通过 `crawlo` 命令访问所有 CLI 工具：

```bash
# 查看帮助信息
crawlo --help

# 查看特定命令的帮助信息
crawlo <command> --help
```

## 命令详解

### startproject

创建一个新的爬虫项目。

```bash
# 创建项目
crawlo startproject myproject

# 创建项目到指定目录
crawlo startproject myproject /path/to/projects
```

### genspider

生成一个新的爬虫模板。

```bash
# 生成爬虫
crawlo genspider myspider example.com

# 生成爬虫到指定模块
crawlo genspider myspider example.com --module mymodule
```

### run

运行爬虫。

```bash
# 运行爬虫
crawlo run myspider

# 运行爬虫并指定配置文件
crawlo run myspider --config settings.py

# 运行爬虫并设置日志级别
crawlo run myspider --log-level DEBUG
```

### list

列出项目中所有可用的爬虫。

```bash
# 列出所有爬虫
crawlo list

# 以 JSON 格式列出爬虫
crawlo list --format json
```

### check

检查项目配置和爬虫实现。

```bash
# 检查项目
crawlo check

# 检查特定爬虫
crawlo check myspider
```

### stats

查看爬虫运行统计信息。

```bash
# 查看统计信息
crawlo stats

# 查看特定爬虫的统计信息
crawlo stats myspider
```

## 全局选项

所有 CLI 命令都支持以下全局选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --help | flag | - | 显示帮助信息 |
| --version | flag | - | 显示版本信息 |
| --config | string | 'settings.py' | 指定配置文件路径 |
| --log-level | string | 'INFO' | 设置日志级别 (DEBUG, INFO, WARNING, ERROR) |
| --project-dir | string | 当前目录 | 指定项目目录 |

## 使用示例

### 创建和运行爬虫项目

```bash
# 1. 创建新项目
crawlo startproject myproject
cd myproject

# 2. 生成爬虫
crawlo genspider myspider example.com

# 3. 编辑爬虫文件
# 编辑 myproject/spiders/myspider.py

# 4. 运行爬虫
crawlo run myspider

# 5. 查看统计信息
crawlo stats
```

### 配置管理

```bash
# 使用不同的配置文件
crawlo run myspider --config production_settings.py

# 设置调试模式
crawlo run myspider --log-level DEBUG

# 指定项目目录
crawlo list --project-dir /path/to/myproject
```

## 环境变量

CLI 工具支持以下环境变量：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| CRAWLO_PROJECT_DIR | 当前目录 | 项目目录路径 |
| CRAWLO_CONFIG | 'settings.py' | 配置文件路径 |
| CRAWLO_LOG_LEVEL | 'INFO' | 日志级别 |
| CRAWLO_CONCURRENCY | 16 | 并发请求数 |
| CRAWLO_DOWNLOAD_DELAY | 0.5 | 下载延迟 |

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

## 最佳实践

### 项目结构管理

```bash
# 推荐的项目结构
myproject/
├── settings.py          # 主配置文件
├── spiders/             # 爬虫目录
│   ├── __init__.py
│   └── myspider.py
├── pipelines/           # 管道目录
│   ├── __init__.py
│   └── custom_pipeline.py
├── middlewares/         # 中间件目录
│   ├── __init__.py
│   └── custom_middleware.py
└── items/               # 数据项定义
    ├── __init__.py
    └── myitem.py
```

### 配置文件管理

```bash
# 开发环境配置
crawlo run myspider --config settings_dev.py

# 测试环境配置
crawlo run myspider --config settings_test.py

# 生产环境配置
crawlo run myspider --config settings_prod.py
```

### 日志管理

```bash
# 设置日志级别
crawlo run myspider --log-level INFO

# 输出到文件
crawlo run myspider --log-file crawler.log

# 设置日志轮转
crawlo run myspider --log-max-bytes 10485760 --log-backup-count 5
```

### 性能调优

```bash
# 调整并发数
crawlo run myspider --concurrency 32

# 设置下载延迟
crawlo run myspider --download-delay 1.0

# 设置超时时间
crawlo run myspider --download-timeout 60
```