# 内置扩展

Crawlo提供了几个内置扩展组件，为爬取过程添加额外功能。这些扩展组件可以通过配置启用或禁用。

## 概述

内置扩展为网页爬取提供辅助功能：

- 日志记录和监控
- 性能分析
- 健康检查
- 统计信息收集
- 调试辅助

## LogIntervalExtension

定期记录爬取进度以监控正在进行的操作。

### 特性

- 可配置的日志记录间隔
- 进度报告
- 性能指标
- 实时监控

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.log_interval.LogIntervalExtension',
]

# 日志间隔设置
LOG_INTERVAL = 60  # 每60秒记录一次
```

## LogStats

爬取完成时记录最终统计信息以提供操作摘要。

### 特性

- 全面的统计信息收集
- 最终摘要报告
- 性能指标
- 资源使用跟踪

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.log_stats.LogStats',
]

# 日志统计设置
STATS_DUMP = True
```

## CustomLoggerExtension

为特殊日志记录需求提供自定义日志功能。

### 特性

- 自定义日志格式
- 多日志输出
- 可配置的日志级别
- 结构化日志

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.logging_extension.CustomLoggerExtension',
]

# 自定义日志设置
CUSTOM_LOGGER_ENABLED = True
CUSTOM_LOGGER_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

## MemoryMonitorExtension

在爬取过程中监控内存使用以检测内存泄漏或过度使用。

### 特性

- 实时内存监控
- 内存使用警报
- 定期报告
- 基于阈值的警告

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]

# 内存监控设置
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL = 60  # 每60秒检查一次
MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用率达到80%时警告
MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用率达到90%时严重警告
```

## RequestRecorderExtension

记录所有请求用于调试和分析目的。

### 特性

- 请求日志记录
- 响应元数据记录
- 基于文件的存储
- 可配置的记录选项

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.request_recorder.RequestRecorderExtension',
]

# 请求记录器设置
REQUEST_RECORDER_ENABLED = True
REQUEST_RECORDER_OUTPUT_DIR = 'requests_log'
REQUEST_RECORDER_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## PerformanceProfilerExtension

分析爬取过程的性能以识别瓶颈和优化机会。

### 特性

- 性能分析
- 函数计时
- 资源使用跟踪
- 定期分析报告

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
]

# 性能分析器设置
PERFORMANCE_PROFILER_ENABLED = True
PERFORMANCE_PROFILER_OUTPUT_DIR = 'profiling'
PERFORMANCE_PROFILER_INTERVAL = 300  # 每5分钟分析一次
```

## HealthCheckExtension

监控爬取过程的健康状况以确保正常运行。

### 特性

- 健康状态监控
- 组件健康检查
- 警报机制
- 恢复操作

### 配置

```python
# 在settings.py中
EXTENSIONS = [
    'crawlo.extension.health_check.HealthCheckExtension',
]

# 健康检查设置
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_INTERVAL = 60  # 每60秒检查一次
```

## 使用示例

要启用多个内置扩展：

```python
# 在settings.py中
EXTENSIONS = [
    # 日志扩展
    'crawlo.extension.log_interval.LogIntervalExtension',
    'crawlo.extension.log_stats.LogStats',
    'crawlo.extension.logging_extension.CustomLoggerExtension',
    
    # 监控扩展
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
    
    # 实用扩展
    'crawlo.extension.request_recorder.RequestRecorderExtension',
    'crawlo.extension.health_check.HealthCheckExtension',
]
```

## 性能考虑

- 仅启用必要的扩展以最小化开销
- 为周期性扩展配置适当的间隔
- 监控扩展资源使用
- 在生产环境中禁用调试扩展
- 为高频事件使用轻量级实现

## 扩展集成

内置扩展通过事件钩子与爬虫集成：

```python
class ExampleExtension:
    def __init__(self, crawler):
        # 初始化扩展
        pass
        
    def spider_opened(self, spider):
        # 处理爬虫打开事件
        pass
        
    def response_received(self, response, spider):
        # 处理响应接收事件
        pass
        
    def item_successful(self, item, spider):
        # 处理数据项处理事件
        pass
        
    def spider_closed(self, spider, reason):
        # 处理爬虫关闭事件
        pass
```

## 最佳实践

1. **选择性启用**：仅启用您需要的扩展
2. **性能监控**：监控扩展对爬取性能的影响
3. **配置**：为您的用例正确配置扩展设置
4. **生产环境vs开发环境**：为不同环境使用不同的扩展集
5. **错误处理**：扩展应优雅地处理错误而不影响爬取