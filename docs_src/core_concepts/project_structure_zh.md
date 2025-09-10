# 项目结构

典型的 Crawlo 项目遵循组织良好的结构，以促进可维护性和可扩展性。

## 默认项目结构

当您使用 `crawlo startproject` 创建新项目时，会生成以下结构：

```
project_name/
├── crawlo.cfg              # 项目配置文件
├── run.py                  # 主执行脚本
├── logs/                   # 日志目录
├── project_name/           # 主 Python 包
│   ├── __init__.py         # 包初始化器
│   ├── settings.py         # 配置设置
│   ├── items.py            # 数据项定义
│   ├── middlewares.py      # 自定义中间件
│   ├── pipelines.py        # 数据处理管道
│   └── spiders/            # 爬虫实现
│       ├── __init__.py     # 爬虫包初始化器
│       └── *.py            # 单个爬虫文件
```

## 关键文件和目录

### 1. crawlo.cfg

此文件标识项目根目录。对于 Crawlo 定位项目文件和配置至关重要。

### 2. run.py

处理命令行参数并启动爬取过程的主执行脚本。

### 3. logs/

存储日志文件的目录。日志文件的结构和命名可以在 `settings.py` 中配置。

### 4. project_name/

包含所有项目特定代码的主 Python 包。

#### __init__.py

使目录成为 Python 包的包初始化器。

#### settings.py

项目配置文件，您可以在其中定义以下设置：
- 并发级别
- 下载延迟
- 管道配置
- 中间件配置
- Redis 设置（分布式模式）

#### items.py

指定您想要提取的数据结构的数据项定义。

#### middlewares.py

用于请求/响应处理的自定义中间件实现。

#### pipelines.py

用于数据处理和存储的自定义管道实现。

#### spiders/

包含爬虫实现的目录。

##### __init__.py

爬虫包初始化器。

##### *.py

包含一个或多个爬虫类的单个爬虫文件。

## 自定义项目结构

虽然推荐使用默认结构，但您可以根据需要自定义它：

### 1. 多个爬虫文件

您可以根据功能将爬虫组织到多个文件中：

```
spiders/
├── __init__.py
├── news_spiders.py
├── product_spiders.py
└── forum_spiders.py
```

### 2. 复杂项目的子目录

对于大型项目，您可以创建子目录：

```
project_name/
├── __init__.py
├── settings.py
├── items/
│   ├── __init__.py
│   ├── news_items.py
│   └── product_items.py
├── spiders/
│   ├── __init__.py
│   ├── news/
│   │   ├── __init__.py
│   │   ├── local_news.py
│   │   └── international_news.py
│   └── products/
│       ├── __init__.py
│       ├── electronics.py
│       └── clothing.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

## 最佳实践

1. **保持组织性**：使用一致的命名约定和目录结构
2. **分离关注点**：将项目、爬虫和管道保存在各自的目录中
3. **使用有意义的名称**：为文件和类选择描述性名称
4. **记录您的结构**：添加注释以解释复杂结构
5. **版本控制**：使用 Git 等版本控制系统跟踪更改