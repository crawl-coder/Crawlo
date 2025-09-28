# Crawlo 框架日志系统使用指南

## 概述

Crawlo 框架提供了一个统一的日志系统，确保框架组件和用户代码都能正确输出日志信息。本指南将帮助您正确配置和使用日志系统。

## 配置日志系统

### 1. 在项目配置中设置日志级别

在您的项目 `settings.py` 文件中设置日志配置：

```python
# 基本日志配置
LOG_LEVEL = 'INFO'  # DEBUG/INFO/WARNING/ERROR
LOG_FILE = 'logs/my_project.log'
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
LOG_ENCODING = 'utf-8'

# 特定模块的日志级别（可选）
LOG_LEVELS = {
    'crawlo.framework': 'INFO',
    'crawlo.crawler': 'DEBUG',
    'my_project.spiders': 'DEBUG',
    'my_project.pipelines': 'INFO',
}
```

### 2. 使用 conda 虚拟环境

建议使用 conda 虚拟环境来管理 Crawlo 项目：

```bash
# 激活虚拟环境
conda activate crawlo

# 运行项目
python run.py
```

## 在组件中使用日志系统

### 1. 推荐方式：使用统一的组件 logger 创建函数

```python
from crawlo.utils.log import get_component_logger

class MyMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler
        # 推荐：使用统一的组件logger创建函数
        self.logger = get_component_logger(self.__class__, crawler.settings)
    
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)
```

### 2. 传统方式（仍然支持，但不推荐）

```python
from crawlo.utils.log import get_logger

class MyPipeline:
    def __init__(self, settings):
        self.settings = settings
        # 传统方式：手动传递LOG_LEVEL
        self.logger = get_logger(self.__class__.__name__, settings.get('LOG_LEVEL'))
```

### 3. 简单方式（适用于不需要特定配置的场景）

```python
from crawlo.utils.log import get_component_logger

class MyExtension:
    def __init__(self):
        # 简单方式：只传递类
        self.logger = get_component_logger(self.__class__)
```

## 框架初始化和日志时序

### 框架已解决的问题

1. **日志时序问题**：框架确保日志系统在所有其他组件之前初始化
2. **配置一致性**：所有组件使用相同的日志配置
3. **文件日志输出**：框架启动信息现在会正确输出到日志文件中

### 框架初始化流程

```python
from crawlo.core.framework_initializer import initialize_framework

# 手动初始化框架（通常不需要，框架会自动处理）
settings = initialize_framework()
```

## 最佳实践

### 1. 组件开发最佳实践

```python
from crawlo.utils.log import get_component_logger

class MySpider(Spider):
    name = 'my_spider'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 在Spider中，可以直接使用类名
        self.logger = get_component_logger(self.__class__)
    
    def parse(self, response):
        self.logger.info(f"正在处理页面: {response.url}")
        # 处理逻辑...
```

### 2. 中间件开发最佳实践

```python
from crawlo.utils.log import get_component_logger

class MyMiddleware:
    def __init__(self, crawler):
        self.crawler = crawler
        # 传递crawler.settings确保使用正确的日志配置
        self.logger = get_component_logger(self.__class__, crawler.settings)
    
    def process_request(self, request, spider):
        self.logger.debug(f"处理请求: {request.url}")
        return None
```

### 3. 管道开发最佳实践

```python
from crawlo.utils.log import get_component_logger

class MyPipeline:
    def __init__(self, settings):
        self.settings = settings
        # 传递settings和可选的日志级别
        self.logger = get_component_logger(self.__class__, settings, 'INFO')
    
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler.settings)
    
    def process_item(self, item, spider):
        self.logger.info(f"处理数据项: {item}")
        return item
```

## 日志输出示例

正确配置后，您的日志文件将包含完整的框架启动信息：

```
2025-09-24 00:51:17,916 - [crawlo.framework] - INFO: Crawlo框架初始化完成
2025-09-24 00:51:17,918 - [crawlo.framework] - INFO: Crawlo Framework Started 1.3.3
2025-09-24 00:51:17,918 - [crawlo.framework] - INFO: 使用单机模式 - 简单快速，适合开发和中小规模爬取
2025-09-24 00:51:17,918 - [crawlo.framework] - INFO: Run Mode: standalone
2025-09-24 00:51:17,924 - [crawlo.framework] - INFO: Starting running my_spider
2025-09-24 00:51:17,925 - [QueueManager] - INFO: Queue initialized successfully Type: memory
2025-09-24 00:51:17,925 - [Scheduler] - INFO: enabled filters: crawlo.filters.memory_filter.MemoryFilter
```

## 配置文件合并机制

框架支持多层配置合并：

1. **默认配置**：`crawlo/settings/default_settings.py` 中的 `LOG_LEVEL = None`
2. **项目配置**：您项目中的 `settings.py` 中的 `LOG_LEVEL` 设置
3. **运行时配置**：程序运行时传递的配置参数

项目配置会覆盖默认配置，运行时配置会覆盖项目配置。

## 常见问题

### Q: 为什么我的日志文件中缺少框架启动信息？
A: 这个问题已经在最新版本中修复。框架现在使用专门的 framework logger 来输出启动信息，确保这些信息能正确写入日志文件。

### Q: 如何为不同的组件设置不同的日志级别？
A: 使用 `LOG_LEVELS` 配置：

```python
LOG_LEVELS = {
    'crawlo.framework': 'INFO',
    'my_spider': 'DEBUG',
    'MyPipeline': 'WARNING',
}
```

### Q: 我的组件日志输出不一致怎么办？
A: 建议所有组件都使用 `get_component_logger()` 函数创建 logger，这样可以确保一致的日志配置。

## 迁移指南

如果您有现有的组件使用旧的日志创建方式，可以按以下步骤迁移：

### 旧方式
```python
from crawlo.utils.log import get_logger

class MyComponent:
    def __init__(self, crawler):
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
```

### 新方式
```python
from crawlo.utils.log import get_component_logger

class MyComponent:
    def __init__(self, crawler):
        self.logger = get_component_logger(self.__class__, crawler.settings)
```

这样的迁移能确保您的组件使用统一的日志配置，并且能够正确响应框架的日志设置。