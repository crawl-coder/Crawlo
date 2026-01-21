# Crawlo 框架资源监控功能指南

## 概述

Crawlo 框架提供了全面的资源监控功能，包括内存、MySQL、Redis 和系统性能监控。本文档介绍了如何启用和配置这些监控功能。

## 监控功能

### 1. 内存监控

监控爬虫进程的内存使用情况。

**配置项：**
- MEMORY_MONITOR_ENABLED - 是否启用内存监控（默认：False）
- MEMORY_MONITOR_INTERVAL - 监控检查间隔（秒，默认：60）
- MEMORY_WARNING_THRESHOLD - 内存使用警告阈值（百分比，默认：80.0）
- MEMORY_CRITICAL_THRESHOLD - 内存使用严重阈值（百分比，默认：90.0）

**扩展：** crawlo.extension.memory_monitor.MemoryMonitorExtension

### 2. MySQL监控

监控MySQL连接池状态和SQL执行性能。

**配置项：**
- MYSQL_MONITOR_ENABLED - 是否启用MySQL监控（默认：False）
- MYSQL_MONITOR_INTERVAL - 监控检查间隔（秒，默认：120）

**扩展：** crawlo.extension.mysql_monitor.MySQLMonitorExtension

### 3. Redis监控

监控Redis连接池状态和性能。

**配置项：**
- REDIS_MONITOR_ENABLED - 是否启用Redis监控（默认：False）
- REDIS_MONITOR_INTERVAL - 监控检查间隔（秒，默认：120）

**扩展：** crawlo.extension.redis_monitor.RedisMonitorExtension

### 4. 系统性能监控

监控系统CPU、内存、网络和磁盘使用情况。

**工具：** crawlo.utils.performance_monitor.PerformanceMonitor

## 配置示例

### 基础监控配置

`python
# 启用内存监控
MEMORY_MONITOR_ENABLED = True
MEMORY_MONITOR_INTERVAL = 60

# 启用MySQL监控
MYSQL_MONITOR_ENABLED = True
MYSQL_MONITOR_INTERVAL = 120

# 启用Redis监控
REDIS_MONITOR_ENABLED = True
REDIS_MONITOR_INTERVAL = 120
`

### 定时任务监控配置

`python
# 定时任务配置
SCHEDULER_ENABLED = True
SCHEDULER_JOBS = [
    {
        'spider': 'my_spider',
        'cron': '*/5 * * * *',  # 每5分钟执行一次
        'enabled': True,
    }
]

# 定时任务资源监控
SCHEDULER_RESOURCE_MONITOR_ENABLED = True
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300  # 5分钟检查一次
`

## 监控扩展使用

### 启用监控扩展

监控扩展会在爬虫启动时自动初始化并开始监控。只有在相应配置项启用时才会创建监控实例。

### 监控数据

监控扩展会定期输出以下信息：

- **内存监控：** 进程内存使用率、RSS/VMS值、警告/严重阈值状态
- **MySQL监控：** 连接池使用率、SQL执行时间、插入成功率/失败率
- **Redis监控：** 请求次数、错误次数、命中率等

## 性能影响

监控功能对性能的影响非常小，但在生产环境中建议根据实际需要启用监控功能。

## 故障排除

如果监控功能出现异常，请检查：

1. 相应服务（MySQL/Redis）是否可访问
2. 配置项是否正确设置
3. 监控扩展是否在EXTENSIONS列表中

## 默认配置

所有监控功能的默认配置均在 crawlo/settings/default_settings.py 中定义，用户可以在项目配置中覆盖这些默认值。

## 使用示例

参见 examples/monitoring_example_settings.py 文件，其中包含了完整的监控配置示例。

## 扩展开发

如果需要自定义监控功能，可以参考以下扩展的实现：

- crawlo/extension/mysql_monitor.py
- crawlo/extension/redis_monitor.py

这些扩展遵循相同的模式，可以作为开发自定义监控扩展的模板。
