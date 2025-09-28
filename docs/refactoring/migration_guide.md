# Crawlo框架重构迁移指南

## 🎯 重构概述

Crawlo框架经过重大重构，主要改进包括：

1. **统一初始化系统** - 解决初始化混乱和死锁问题
2. **简化日志系统** - 移除过度设计，提升性能
3. **模块化架构** - 清晰的组件边界和依赖关系
4. **组件工厂** - 支持依赖注入和测试

## 🔄 API变更

### 1. 日志系统迁移

**旧写法：**
```python
from crawlo.utils.log import get_logger, LoggerManager

# 复杂的延迟初始化
logger = None
def get_module_logger():
    global logger
    if logger is None:
        logger = get_logger(__name__)
    return logger

# 复杂的配置
LoggerManager.configure(settings)
```

**新写法：**
```python
from crawlo.logging import get_logger, configure_logging

# 简单直接
logger = get_logger(__name__)

# 简化的配置
configure_logging(LOG_LEVEL='INFO', LOG_FILE='logs/app.log')
```

### 2. 框架初始化迁移

**旧写法：**
```python
from crawlo.crawler import CrawlerProcess
from crawlo.core.framework_initializer import get_framework_initializer

# 复杂的初始化检查
init_manager = get_framework_initializer()
if not init_manager.is_ready:
    init_manager.ensure_framework_initialized()

process = CrawlerProcess(settings)
```

**新写法：**
```python
from crawlo.framework import get_framework

# 自动初始化
framework = get_framework(settings)
```

### 3. 爬虫运行迁移

**旧写法：**
```python
from crawlo.crawler import CrawlerProcess
import asyncio

async def run_spider():
    process = CrawlerProcess()
    await process.crawl(MySpider)

asyncio.run(run_spider())
```

**新写法：**
```python
from crawlo.framework import run_spider
import asyncio

# 方式1：使用便捷函数
async def main():
    await run_spider(MySpider)

asyncio.run(main())

# 方式2：使用框架实例
from crawlo.framework import get_framework

async def main():
    framework = get_framework()
    await framework.run(MySpider)

asyncio.run(main())
```

## 🏗️ 新架构特性

### 1. 组件工厂系统

```python
from crawlo.factories import get_component_registry, ComponentSpec

# 注册自定义组件
def create_my_component(crawler, **kwargs):
    return MyComponent(crawler)

registry = get_component_registry()
registry.register(ComponentSpec(
    name='my_component',
    component_type=MyComponent,
    factory_func=create_my_component
))

# 使用组件
component = registry.create('my_component', crawler=crawler)
```

### 2. 现代化Crawler

```python
from crawlo.new_crawler import ModernCrawler
import asyncio

async def main():
    crawler = ModernCrawler(MySpider, settings)
    await crawler.crawl()
    
    # 获取指标
    metrics = crawler.metrics
    print(f"Success rate: {metrics.get_success_rate()}%")

asyncio.run(main())
```

### 3. 统一框架入口

```python
from crawlo.framework import CrawloFramework

# 创建框架实例
framework = CrawloFramework({
    'LOG_LEVEL': 'DEBUG',
    'CONCURRENCY': 16,
    'LOG_FILE': 'logs/crawler.log'
})

# 运行爬虫
await framework.run(MySpider)

# 运行多个爬虫
await framework.run_multiple([Spider1, Spider2, Spider3])
```

## 📦 向后兼容性

### 保持兼容的API

以下API保持向后兼容：

```python
# 这些仍然可用
from crawlo.utils.log import get_logger  # 自动重定向到新系统
from crawlo.crawler import Crawler, CrawlerProcess  # 保持原有接口
```

### 逐步迁移策略

1. **阶段1：更新日志系统**
   ```python
   # 替换复杂的延迟初始化
   from crawlo.logging import get_logger
   logger = get_logger(__name__)
   ```

2. **阶段2：使用新的框架入口**
   ```python
   # 替换复杂的初始化逻辑
   from crawlo.framework import get_framework
   framework = get_framework(settings)
   ```

3. **阶段3：迁移到现代Crawler**
   ```python
   # 使用新的Crawler实现
   from crawlo.new_crawler import ModernCrawler
   crawler = ModernCrawler(spider_cls, settings)
   ```

## 🎯 最佳实践

### 1. 简单的项目结构

```python
# main.py
import asyncio
from crawlo.framework import run_spider
from spiders.my_spider import MySpider

async def main():
    await run_spider(MySpider, {
        'LOG_LEVEL': 'INFO',
        'CONCURRENCY': 8
    })

if __name__ == '__main__':
    asyncio.run(main())
```

### 2. 配置管理

```python
# config.py
CRAWLO_SETTINGS = {
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': 'logs/crawler.log',
    'CONCURRENCY': 16,
    'DOWNLOAD_DELAY': 1.0
}

# main.py
from config import CRAWLO_SETTINGS
from crawlo.framework import get_framework

framework = get_framework(CRAWLO_SETTINGS)
```

### 3. 测试

```python
import pytest
from crawlo.framework import reset_framework, create_crawler
from crawlo.factories import get_component_registry

@pytest.fixture
def clean_framework():
    reset_framework()
    get_component_registry().clear()
    yield
    reset_framework()

def test_spider(clean_framework):
    crawler = create_crawler(TestSpider, {'LOG_LEVEL': 'DEBUG'})
    # 测试逻辑...
```

## ⚡ 性能改进

### 1. 日志系统优化

- 移除复杂的锁竞争
- 使用弱引用避免内存泄漏
- LRU缓存减少重复计算

### 2. 初始化优化

- 清晰的阶段化初始化
- 避免循环依赖
- 更快的启动时间

### 3. 内存优化

- 组件工厂减少重复创建
- 更好的资源管理
- 降级策略避免崩溃

## 🔧 故障排除

### 常见问题

1. **导入错误**
   ```python
   # 确保按顺序导入
   from crawlo.logging import get_logger  # 先导入日志
   from crawlo.framework import get_framework  # 再导入框架
   ```

2. **配置问题**
   ```python
   # 使用新的配置方式
   from crawlo.logging import configure_logging
   configure_logging(LOG_LEVEL='DEBUG')
   ```

3. **初始化失败**
   ```python
   # 检查框架状态
   from crawlo.initialization import is_framework_ready
   if not is_framework_ready():
       # 手动初始化
       from crawlo.initialization import initialize_framework
       initialize_framework()
   ```

## 📚 更多资源

- [新架构设计文档](./architecture.md)
- [组件工厂指南](./component_factory.md)
- [性能优化指南](./performance.md)
- [API参考文档](./api_reference.md)