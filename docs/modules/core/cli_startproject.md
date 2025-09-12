# startproject 命令

`startproject` 命令用于初始化一个新的 Crawlo 爬虫项目，创建项目的基本目录结构和配置文件。

## 使用方法

```bash
crawlo startproject <project_name> [template_type] [--modules module1,module2]
```

### 参数说明

- `project_name`：项目名称，必须是有效的 Python 标识符
- `template_type`：可选，模板类型（默认：default）
- `--modules`：可选，选择要包含的模块组件

## 模板类型

Crawlo 提供多种预定义模板来满足不同场景的需求：

### default（默认模板）
通用配置，适合大多数项目。包含完整的配置选项和最佳实践设置。

### simple（简化模板）
最小配置，适合快速开始。只包含最基本的配置项，便于快速上手。

### distributed（分布式模板）
针对分布式爬取优化。预配置 Redis 队列和去重过滤器，适合大规模数据采集。

### high-performance（高性能模板）
针对大规模高并发优化。使用高性能下载器和优化的并发设置。

### gentle（温和模板）
低负载配置，对目标网站友好。使用较低的并发数和较长的请求延迟。

## 模块组件

使用 `--modules` 参数可以选择性地包含特定功能模块：

- `mysql`：MySQL 数据库支持
- `mongodb`：MongoDB 数据库支持
- `redis`：Redis 支持（分布式队列和去重）
- `proxy`：代理支持
- `monitoring`：监控和性能分析
- `dedup`：去重功能
- `httpx`：HttpX 下载器
- `aiohttp`：AioHttp 下载器
- `curl`：CurlCffi 下载器

## 使用示例

### 创建默认项目
```bash
crawlo startproject my_spider_project
```

### 创建分布式项目
```bash
crawlo startproject news_crawler distributed
```

### 创建高性能项目并包含 MySQL 和代理支持
```bash
crawlo startproject ecommerce_spider high-performance --modules mysql,proxy
```

### 创建简化项目并包含 MongoDB 支持
```bash
crawlo startproject simple_spider simple --modules mongodb
```

## 项目结构

使用 `startproject` 命令创建的项目具有以下标准结构：

```
project_name/
├── crawlo.cfg                 # 项目配置文件
├── run.py                     # 项目启动脚本
├── logs/                      # 日志目录
├── output/                    # 数据输出目录
└── project_name/              # 项目包
    ├── __init__.py            # 包初始化文件
    ├── settings.py            # 项目配置（根据模板类型生成）
    ├── items.py               # 数据结构定义
    ├── middlewares.py         # 中间件
    ├── pipelines.py           # 数据管道
    └── spiders/               # 爬虫目录
        └── __init__.py        # 爬虫包初始化文件
```

## run.py 启动脚本说明

项目根目录下的 `run.py` 文件是一个简化版的爬虫启动脚本，用户可以直接运行：

```bash
python run.py
```

该脚本具有以下特点：

1. **自动配置加载**：脚本会自动查找并加载项目的配置文件
2. **固定爬虫运行**：默认运行名为 `your_spider_name` 的爬虫
3. **简化设计**：代码简洁，易于理解和修改

使用方法：
1. 打开 `run.py` 文件
2. 将 `'your_spider_name'` 替换为实际要运行的爬虫名称
3. 运行命令 `python run.py`

注意：如果需要更复杂的运行选项（如运行多个爬虫、自定义配置等），建议使用命令行工具：
```bash
crawlo run spider_name
```

## 配置文件说明

无论选择哪种模板类型，生成的配置文件都统一命名为 `settings.py`，但内容会根据模板类型进行相应调整：

- **default 模板**：包含完整的配置选项和详细注释
- **simple 模板**：只包含最基本的配置项
- **distributed 模板**：预配置分布式爬取所需的 Redis 设置
- **high-performance 模板**：优化的高性能配置
- **gentle 模板**：低负载、对目标网站友好的配置

## 最佳实践

1. **选择合适的模板**：根据项目需求选择最合适的模板类型
2. **模块化构建**：使用 `--modules` 参数只包含需要的功能组件
3. **配置调整**：创建项目后根据具体需求调整 `settings.py` 配置
4. **版本控制**：将项目纳入版本控制系统进行管理

## 故障排除

### 项目名称验证
项目名称必须满足以下要求：
- 以小写字母开头
- 只包含小写字母、数字和下划线
- 是有效的 Python 标识符
- 不是 Python 关键字

### 模板类型错误
如果指定的模板类型不支持，命令会显示可用的模板类型列表。

### 目录已存在
如果目标目录已存在，命令会提示选择其他项目名称或删除现有目录。