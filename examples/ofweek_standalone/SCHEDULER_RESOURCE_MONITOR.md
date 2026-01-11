# 定时任务调度器 - 资源监控功能说明

## 📋 功能概述

定时任务调度器新增了资源监控功能，可以检测资源使用情况和潜在的资源泄露，确保长时间运行时资源使用正常。

## 🔍 监控功能

### 1. 资源统计
- 显示活跃资源数量
- 按类型统计资源分布（downloader、pipeline、session 等）

### 2. 资源泄露检测
- 检测超过阈值的未清理资源
- 自动标记潜在的资源泄露
- 输出资源名称和生命周期

### 3. 系统资源监控
- 显示内存使用情况（MB）
- 显示 CPU 使用情况（%）
- 使用 `psutil` 库获取系统资源信息

### 4. 垃圾回收
- 定期执行 Python 垃圾回收
- 显示回收的对象数量

## ⚙️ 配置参数

在 `settings.py` 中添加了以下配置参数：

```python
# 资源监控配置（可选）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True   # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300   # 资源检查间隔（秒），默认5分钟
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600  # 资源泄露检测阈值（秒），默认1小时
```

### 配置说明

| 参数 | 默认值 | 说明 |
|------|---------|------|
| `SCHEDULER_RESOURCE_MONITOR_ENABLED` | True | 是否启用资源监控 |
| `SCHEDULER_RESOURCE_CHECK_INTERVAL` | 300 | 资源检查间隔（秒），默认5分钟 |
| `SCHEDULER_RESOURCE_LEAK_THRESHOLD` | 3600 | 资源泄露检测阈值（秒），默认1小时 |

## 📊 监控日志

### 正常监控日志

```
2026-01-11 20:10:00,000 - [SchedulerDaemon] - INFO: 资源监控 - 活跃资源: 5, 内存: 125.50MB, CPU: 2.3%
2026-01-11 20:10:00,001 - [SchedulerDaemon] - INFO: 资源类型分布 - downloader: 2, pipeline: 1, session: 2
2026-01-11 20:10:00,002 - [SchedulerDaemon] - INFO: 垃圾回收完成 - 回收对象数: 0
```

### 资源泄露检测日志

```
2026-01-11 20:10:00,003 - [SchedulerDaemon] - WARNING: 检测到 2 个潜在资源泄露
2026-01-11 20:10:00,004 - [SchedulerDaemon] - WARNING:   - downloader_12345 (生命周期: 3605.23s)
2026-01-11 20:10:00,005 - [SchedulerDaemon] - WARNING:   - session_67890 (生命周期: 3610.45s)
```

## 🚀 使用方法

### 1. 启用资源监控

在 `settings.py` 中设置：

```python
SCHEDULER_RESOURCE_MONITOR_ENABLED = True
```

### 2. 禁用资源监控

在 `settings.py` 中设置：

```python
SCHEDULER_RESOURCE_MONITOR_ENABLED = False
```

### 3. 调整监控间隔

在 `settings.py` 中设置：

```python
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300  # 5分钟
```

### 4. 调整泄露检测阈值

在 `settings.py` 中设置：

```python
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600  # 1小时
```

## 📦 依赖安装

资源监控功能需要安装 `psutil` 库：

```bash
pip install psutil
```

如果没有安装 `psutil`，资源监控功能会自动禁用，不会影响调度器的正常运行。

## ⚠️ 注意事项

### 1. 性能影响

资源监控会定期执行垃圾回收，可能会对性能产生轻微影响。如果不需要监控，可以禁用。

### 2. 长期运行

建议启用资源监控，以确保长时间运行时资源使用正常。

### 3. psutil 依赖

资源监控功能需要安装 `psutil` 库。如果没有安装，资源监控功能会自动禁用。

### 4. 资源泄露检测

资源泄露检测是基于资源生命周期的，超过阈值的资源会被标记为潜在泄露。需要根据实际情况调整阈值。

## 🔧 故障排除

### Q: 资源监控没有启动？

A: 检查以下几点：
1. 确认 `SCHEDULER_RESOURCE_MONITOR_ENABLED = True`
2. 检查是否安装了 `psutil` 库
3. 查看日志中是否有 "psutil 未安装" 的警告

### Q: 资源监控日志太多？

A: 可以调整 `SCHEDULER_RESOURCE_CHECK_INTERVAL` 参数，增加检查间隔。

### Q: 如何查看资源泄露？

A: 查看日志中的 "检测到 X 个潜在资源泄露" 警告信息。

### Q: 资源泄露检测不准确？

A: 可以调整 `SCHEDULER_RESOURCE_LEAK_THRESHOLD` 参数，根据实际情况设置合适的阈值。

## 📚 相关文档

- [定时任务调度器使用文档](../../docs/scheduler_guide.md)
- [OFweek 爬虫定时任务使用指南](./SCHEDULER_README.md)
- [资源管理器文档](../../crawlo/utils/resource_manager.py)

## 🎯 最佳实践

1. **启用资源监控**：对于长时间运行的调度器，建议启用资源监控
2. **定期检查日志**：定期查看资源监控日志，确保资源使用正常
3. **调整监控间隔**：根据任务执行频率，调整合适的监控间隔
4. **设置合适的阈值**：根据实际情况，设置合适的资源泄露检测阈值
5. **及时处理资源泄露**：如果检测到资源泄露，及时处理

## 📝 配置示例

```python
# settings.py

# 启用定时任务
SCHEDULER_ENABLED = True

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',
        'cron': '*/2 * * * *',
        'enabled': True,
        'args': {},
        'priority': 10
    }
]

# 定时任务高级配置
SCHEDULER_CHECK_INTERVAL = 1
SCHEDULER_MAX_CONCURRENT = 3
SCHEDULER_JOB_TIMEOUT = 3600

# 资源监控配置
SCHEDULER_RESOURCE_MONITOR_ENABLED = True
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600
```
