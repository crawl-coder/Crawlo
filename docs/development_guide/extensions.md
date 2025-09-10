# 扩展组件

扩展组件为 Crawlo 框架提供了额外的功能，可以在不修改核心代码的情况下增强爬虫的能力。

## 扩展管理器

[ExtensionManager](file:///d%3A/dowell/projects/Crawlo/crawlo/extension/__init__.py#L10-L35) 负责管理所有扩展组件，并协调它们的执行。

### 类: ExtensionManager

```python
class ExtensionManager(object):
    def __init__(self, crawler):
        # Initialize the extension manager
        pass
    
    def add_extension(self, extension_class):
        # Add an extension to the manager
        pass
    
    async def fire_event(self, event_name, *args, **kwargs):
        # Fire an event to all registered extensions
        pass
```

#### 参数

- `crawler` (Crawler): 与扩展管理器关联的爬虫实例

#### 方法

##### `__init__(self, crawler)`

使用爬虫初始化扩展管理器。

**参数:**
- `crawler` (Crawler): 与扩展管理器关联的爬虫实例

##### `add_extension(self, extension_class)`

向管理器添加扩展。

**参数:**
- `extension_class` (class): 要添加的扩展类

##### `fire_event(self, event_name, *args, **kwargs)`

向所有已注册的扩展触发事件。

**参数:**
- `event_name` (str): 要触发的事件名称
- `*args`: 传递给事件处理程序的位置参数
- `**kwargs`: 传递给事件处理程序的关键字参数

**返回:**
- `Coroutine`: 当所有事件处理程序执行完成时解析的协程

## 基础扩展类

所有扩展都应该遵循一定的接口规范。

### 类: BaseExtension

扩展的基类。

```python
class BaseExtension(object):
    def __init__(self, crawler):
        # Initialize the extension
        pass
    
    @classmethod
    def create_instance(cls, crawler):
        # Create an instance of the extension
        pass
```

#### 方法

##### `__init__(self, crawler)`

使用爬虫实例初始化扩展。

**参数:**
- `crawler` (Crawler): 与扩展关联的爬虫实例

##### `create_instance(cls, crawler)`

创建扩展实例的类方法。

**参数:**
- `crawler` (Crawler): 与扩展关联的爬虫实例

**返回:**
- `BaseExtension`: 扩展实例

## 内置扩展

Crawlo 提供了多种内置扩展：

### 1. LogIntervalExtension (定时日志扩展)

定期输出爬虫的运行统计信息。

**配置参数:**
```python
INTERVAL = 60  # 日志输出间隔（秒）
```

### 2. LogStats (统计信息扩展)

收集和记录爬虫运行过程中的各种统计数据。

### 3. CustomLoggerExtension (自定义日志扩展)

初始化和配置日志系统。

**配置参数:**
```python
LOG_FILE = 'logs/spider.log'  # 日志文件路径
LOG_LEVEL = 'INFO'  # 日志级别
LOG_ENABLE_CUSTOM = False  # 是否启用自定义日志配置
```

### 4. MemoryMonitorExtension (内存监控扩展)

监控爬虫进程的内存使用情况，在内存使用过高时发出警告。

**启用方式:**
```python
EXTENSIONS = [
    # ... 其他扩展
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]

# 配置参数
MEMORY_MONITOR_ENABLED = True  # 是否启用内存监控
MEMORY_MONITOR_INTERVAL = 60  # 内存检查间隔（秒）
MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用警告阈值（百分比）
MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用严重阈值（百分比）
```

### 5. RequestRecorderExtension (请求记录扩展)

记录所有发送的请求和接收到的响应信息，便于调试和分析。

**启用方式:**
```python
EXTENSIONS = [
    # ... 其他扩展
    'crawlo.extension.request_recorder.RequestRecorderExtension',
]

# 配置参数
REQUEST_RECORDER_ENABLED = True  # 是否启用请求记录
REQUEST_RECORDER_OUTPUT_DIR = 'requests_log'  # 请求记录输出目录
REQUEST_RECORDER_MAX_FILE_SIZE = 10 * 1024 * 1024  # 单个记录文件最大大小（字节）
```

### 6. PerformanceProfilerExtension (性能分析扩展)

在爬虫运行期间进行性能分析，帮助优化爬虫性能。

**启用方式:**
```python
EXTENSIONS = [
    # ... 其他扩展
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
]

# 配置参数
PERFORMANCE_PROFILER_ENABLED = True  # 是否启用性能分析
PERFORMANCE_PROFILER_OUTPUT_DIR = 'profiling'  # 性能分析输出目录
PERFORMANCE_PROFILER_INTERVAL = 300  # 定期保存分析结果间隔（秒）
```

### 7. HealthCheckExtension (健康检查扩展)

监控爬虫的健康状态，包括响应时间、错误率等指标。

**启用方式:**
```python
EXTENSIONS = [
    # ... 其他扩展
    'crawlo.extension.health_check.HealthCheckExtension',
]

# 配置参数
HEALTH_CHECK_ENABLED = True  # 是否启用健康检查
HEALTH_CHECK_INTERVAL = 60  # 健康检查间隔（秒）
```

## 开发自定义扩展

要开发自定义扩展，需要遵循以下规范：

1. 创建一个类实现扩展功能
2. 实现 `create_instance` 类方法
3. 根据需要订阅相应的事件

### 示例：自定义扩展

```python
from crawlo.utils.log import get_logger
from crawlo.event import spider_opened, spider_closed

class CustomExtension:
    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
    
    @classmethod
    def create_instance(cls, crawler):
        o = cls(crawler)
        crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
        crawler.subscriber.subscribe(o.spider_closed, event=spider_closed)
        return o
    
    async def spider_opened(self):
        self.logger.info("Spider opened!")
    
    async def spider_closed(self):
        self.logger.info("Spider closed!")
```

然后在 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中启用：
```python
EXTENSIONS = [
    # ... 其他扩展
    'your_project.extensions.CustomExtension',
]
```

### 事件系统

Crawlo 提供了以下内置事件：

- `spider_opened`: 爬虫启动时触发
- `spider_closed`: 爬虫关闭时触发
- `request_scheduled`: 请求被调度时触发
- `response_received`: 响应被接收时触发
- `item_successful`: 数据项处理成功时触发
- `item_discard`: 数据项被丢弃时触发
- `ignore_request`: 请求被忽略时触发

### 扩展生命周期

扩展的生命周期与爬虫的生命周期紧密相关：

1. **初始化**: 当爬虫启动时，扩展管理器会加载所有配置的扩展
2. **事件订阅**: 扩展在 `create_instance` 方法中订阅感兴趣的事件
3. **事件处理**: 当事件发生时，扩展的相应方法会被调用
4. **清理**: 当爬虫关闭时，扩展有机会进行清理工作

## 配置扩展

在 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中配置扩展：

```python
EXTENSIONS = [
    # 内置扩展
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    
    # 自定义扩展
    'myproject.extensions.CustomExtension',
]
```

## 最佳实践

1. **明确扩展职责**：每个扩展应该有明确的单一职责
2. **正确处理异步操作**：扩展中的异步方法应该正确处理
3. **异常处理**：在扩展中妥善处理异常，避免影响整个爬虫
4. **资源管理**：正确管理文件、网络连接等资源
5. **性能考虑**：避免在扩展中执行耗时操作
6. **日志记录**：适当记录扩展的操作日志
7. **配置管理**：通过设置文件配置扩展行为
8. **测试**：为扩展编写单元测试