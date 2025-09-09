# Extensions 扩展组件

扩展组件为 Crawlo 框架提供了额外的功能，可以在不修改核心代码的情况下增强爬虫的能力。

## 内置扩展

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

## 可选扩展

### 1. MemoryMonitorExtension (内存监控扩展)
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

### 2. RequestRecorderExtension (请求记录扩展)
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

### 3. PerformanceProfilerExtension (性能分析扩展)
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

### 4. HealthCheckExtension (健康检查扩展)
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

示例：
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

然后在 settings.py 中启用：
```python
EXTENSIONS = [
    # ... 其他扩展
    'your_project.extensions.CustomExtension',
]
```