# startproject 命令

`startproject` 命令用于创建新的 Crawlo 爬虫项目，提供标准的项目结构和基础配置。

## 命令语法

```bash
crawlo startproject <project_name> [project_dir]
```

### 参数说明

- `project_name` - 项目名称（必需）
- `project_dir` - 项目目录路径（可选，默认为当前目录）

## 使用示例

### 创建项目

```bash
# 在当前目录创建项目
crawlo startproject myproject

# 在指定目录创建项目
crawlo startproject myproject /path/to/projects

# 创建项目并进入目录
crawlo startproject myproject
cd myproject
```

## 项目结构

创建的项目包含以下标准结构：

```bash
myproject/
├── settings.py          # 项目配置文件
├── items.py            # 数据项定义
├── pipelines.py        # 数据管道
├── middlewares.py      # 中间件
├── extensions.py       # 扩展
├── spiders/            # 爬虫目录
│   ├── __init__.py
│   └── example.py      # 示例爬虫
├── utils/              # 工具模块
│   └── __init__.py
├── tests/              # 测试目录
│   └── __init__.py
├── requirements.txt    # 依赖列表
└── README.md           # 项目说明
```

## 配置文件

### settings.py

```python
# 项目配置
PROJECT_NAME = 'myproject'
VERSION = '1.0.0'

# 并发配置
CONCURRENCY = 16
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 30

# 队列配置
SCHEDULER_MAX_QUEUE_SIZE = 10000

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = None

# 下载器配置
DOWNLOADER_TYPE = 'aiohttp'

# 管道配置
PIPELINES = []

# 中间件配置
MIDDLEWARES = []

# 扩展配置
EXTENSIONS = []
```

## 自定义模板

### 使用自定义模板

```bash
# 使用自定义模板创建项目
crawlo startproject myproject --template mytemplate

# 列出可用模板
crawlo startproject --list-templates
```

### 模板结构

```bash
templates/
├── default/            # 默认模板
├── distributed/        # 分布式模板
├── api/                # API 爬虫模板
└── custom/             # 自定义模板
    ├── template.py
    └── structure.json
```

## 配置选项

`startproject` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --template | string | 'default' | 使用的模板名称 |
| --list-templates | flag | - | 列出所有可用模板 |
| --force | flag | - | 强制覆盖已存在的项目 |
| --verbose | flag | - | 显示详细输出 |

## 最佳实践

### 1. 项目命名

```bash
# 使用有意义的项目名称
crawlo startproject ecommerce_scraper
crawlo startproject news_collector
crawlo startproject social_media_monitor
```

### 2. 目录组织

```bash
# 按功能组织项目
projects/
├── ecommerce/
│   ├── amazon_scraper/
│   ├── ebay_scraper/
│   └── aliexpress_scraper/
├── news/
│   ├── cnn_crawler/
│   └── bbc_crawler/
└── social/
    ├── twitter_monitor/
    └── facebook_scraper/
```

### 3. 版本控制

```bash
# 创建项目后初始化 Git 仓库
crawlo startproject myproject
cd myproject
git init
git add .
git commit -m "Initial commit: Create Crawlo project"
```

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   # 错误: Permission denied
   # 解决: 使用 sudo 或更改目录权限
   sudo crawlo startproject myproject
   ```

2. **目录已存在**
   ```bash
   # 错误: Directory already exists
   # 解决: 使用 --force 选项或选择其他目录
   crawlo startproject myproject --force
   ```

3. **模板不存在**
   ```bash
   # 错误: Template not found
   # 解决: 检查模板名称或使用默认模板
   crawlo startproject myproject --template default
   ```

### 调试技巧

```bash
# 使用详细模式查看创建过程
crawlo startproject myproject --verbose

# 检查模板列表
crawlo startproject --list-templates
```