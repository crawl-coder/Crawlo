# 内存监控扩展 (MemoryMonitorExtension)

## 概述

MemoryMonitorExtension是一个用于监控爬虫进程内存使用情况的扩展组件。它定期检查进程的内存使用率，并在超过预设阈值时发出警告或严重警告，帮助开发者及时发现内存泄漏或内存使用过高的问题。

## 功能特性

1. **实时监控**：定期监控爬虫进程的内存使用情况
2. **阈值告警**：支持设置警告和严重阈值
3. **详细日志**：提供详细的内存使用信息
4. **灵活配置**：支持多种配置选项
5. **异常处理**：具备良好的异常处理机制

## 配置选项

```python
# 是否启用内存监控扩展
MEMORY_MONITOR_ENABLED = False  # 默认不启用

# 内存监控检查间隔（秒）
MEMORY_MONITOR_INTERVAL = 60  # 默认60秒检查一次

# 内存使用率警告阈值（百分比）
MEMORY_WARNING_THRESHOLD = 80.0  # 默认80%警告阈值

# 内存使用率严重阈值（百分比）
MEMORY_CRITICAL_THRESHOLD = 90.0  # 默认90%严重阈值
```

## 使用方法

### 1. 启用扩展

在项目的[settings.py](https://github.com/crawl-coder/Crawlo/blob/master/examples/api_data_collection/api_data_collection/settings.py)中启用内存监控扩展：

```python
# settings.py
EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    # ... 其他扩展
]

# 启用内存监控
MEMORY_MONITOR_ENABLED = True

# 可选：自定义配置
MEMORY_MONITOR_INTERVAL = 30  # 每30秒检查一次
MEMORY_WARNING_THRESHOLD = 75.0  # 75%警告阈值
MEMORY_CRITICAL_THRESHOLD = 85.0  # 85%严重阈值
```

### 2. 运行爬虫

启用扩展后，爬虫启动时会自动开始内存监控：

```bash
python run.py
```

### 3. 查看日志

内存监控扩展会输出不同级别的日志信息：

```log
[INFO] Memory monitor started. Interval: 60s, Warning threshold: 80.0%, Critical threshold: 90.0%
[DEBUG] Memory usage: 45.20% (RSS: 78.34 MB, VMS: 456.12 MB)
[WARNING] Memory usage high: 82.50% (RSS: 142.67 MB)
[CRITICAL] Memory usage critical: 92.30% (RSS: 159.82 MB)
[INFO] Memory monitor stopped.
```

## 日志级别说明

1. **INFO**：扩展启动和停止信息
2. **DEBUG**：详细的内存使用情况（定期输出）
3. **WARNING**：内存使用率超过警告阈值
4. **CRITICAL**：内存使用率超过严重阈值

## 监控指标

内存监控扩展会监控以下指标：

- **RSS (Resident Set Size)**：物理内存使用量
- **VMS (Virtual Memory Size)**：虚拟内存使用量
- **内存使用率**：进程内存占系统总内存的百分比

## 最佳实践

### 1. 合理设置阈值

根据项目的实际需求和运行环境合理设置阈值：

```python
# 开发环境：宽松的阈值
MEMORY_WARNING_THRESHOLD = 85.0
MEMORY_CRITICAL_THRESHOLD = 95.0

# 生产环境：严格的阈值
MEMORY_WARNING_THRESHOLD = 70.0
MEMORY_CRITICAL_THRESHOLD = 80.0
```

### 2. 调整监控频率

根据项目的特点调整监控频率：

```python
# 高频爬虫：更频繁的监控
MEMORY_MONITOR_INTERVAL = 10

# 低频爬虫：较低频率的监控
MEMORY_MONITOR_INTERVAL = 120
```

### 3. 结合其他监控工具

内存监控扩展可以与其他监控工具结合使用：

```python
EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
    'crawlo.extension.performance_profiler.PerformanceProfilerExtension',
    # ... 其他扩展
]
```

## 故障排除

### 1. 扩展未启动

检查是否正确启用了扩展：

```python
# 确保在EXTENSIONS中添加了扩展
EXTENSIONS = [
    'crawlo.extension.memory_monitor.MemoryMonitorExtension',
]

# 确保启用了扩展
MEMORY_MONITOR_ENABLED = True
```

### 2. 没有日志输出

检查日志级别设置：

```python
# 确保日志级别设置为DEBUG或更低
LOG_LEVEL = 'DEBUG'
```

### 3. 监控频率不正确

检查配置项是否正确：

```python
# 确保配置项名称正确
MEMORY_MONITOR_INTERVAL = 30  # 而不是 MEMORY_MONITOR_INTERVAL_SECONDS
```

## 性能影响

内存监控扩展对性能的影响非常小：

- **CPU占用**：几乎可以忽略不计
- **内存占用**：监控本身占用的内存很少
- **I/O操作**：无磁盘I/O操作

## 适用场景

1. **长时间运行的爬虫**：监控内存泄漏
2. **高并发爬虫**：监控内存使用峰值
3. **生产环境部署**：实时监控系统健康状况
4. **调试和优化**：分析内存使用模式

## 注意事项

1. 内存监控扩展依赖[psutil](https://github.com/giampaolo/psutil)库，请确保已安装
2. 在容器化环境中，监控的是容器的内存使用情况
3. 扩展只监控当前进程的内存使用，不包括子进程
4. 阈值设置应考虑系统的整体内存情况