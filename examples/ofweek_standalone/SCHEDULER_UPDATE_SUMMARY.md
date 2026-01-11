# 定时任务调度器 - 功能更新总结

## 📋 更新内容

### 1. 资源监控功能

#### 功能概述
定时任务调度器新增了资源监控功能，可以检测资源使用情况和潜在的资源泄露，确保长时间运行时资源使用正常。

#### 监控功能
- **资源统计**：显示活跃资源数量和按类型分布
- **资源泄露检测**：检测超过阈值的未清理资源
- **系统资源监控**：显示内存和 CPU 使用情况
- **垃圾回收**：定期执行 Python 垃圾回收

#### 配置参数
在 `settings.py` 中添加了以下配置参数：

```python
# 资源监控配置（可选）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True   # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300   # 资源检查间隔（秒），默认5分钟
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600  # 资源泄露检测阈值（秒），默认1小时
```

#### 监控日志示例

```
2026-01-11 20:10:00,000 - [SchedulerDaemon] - INFO: 资源监控 - 活跃资源: 5, 内存: 125.50MB, CPU: 2.3%
2026-01-11 20:10:00,001 - [SchedulerDaemon] - INFO: 资源类型分布 - downloader: 2, pipeline: 1, session: 2
2026-01-11 20:10:00,002 - [SchedulerDaemon] - INFO: 垃圾回收完成 - 回收对象数: 0
```

#### 资源泄露检测

如果检测到资源泄露，会输出警告信息：

```
2026-01-11 20:10:00,003 - [SchedulerDaemon] - WARNING: 检测到 2 个潜在资源泄露
2026-01-11 20:10:00,004 - [SchedulerDaemon] - WARNING:   - downloader_12345 (生命周期: 3605.23s)
2026-01-11 20:10:00,005 - [SchedulerDaemon] - WARNING:   - session_67890 (生命周期: 3610.45s)
```

#### 注意事项
1. **psutil 依赖**：资源监控功能需要安装 `psutil` 库，如果没有安装会自动禁用
2. **性能影响**：资源监控会定期执行垃圾回收，可能会对性能产生轻微影响
3. **长期运行**：建议启用资源监控，以确保长时间运行时资源使用正常

### 2. 日志优化

#### 功能概述
优化了任务执行完成后的日志输出，显示下次运行时间信息。

#### 日志示例

```
2026-01-11 20:14:00,000 - [SchedulerDaemon] - INFO: 执行定时任务: of_week
2026-01-11 20:14:00,001 - [of_week] - INFO: 爬取任务开始
...
2026-01-11 20:14:07,000 - [of_week] - INFO: 爬取任务结束
2026-01-11 20:14:07,001 - [SchedulerDaemon] - INFO: 定时任务完成: of_week
2026-01-11 20:14:07,002 - [SchedulerDaemon] - INFO: 下次运行时间: 2026-01-11 20:16:00 (距离: 1 分钟)
2026-01-11 20:14:07,003 - [SchedulerDaemon] - INFO: 任务执行完成标记: of_week
```

#### 功能说明
- **定时任务完成**：显示任务执行完成信息
- **下次运行时间**：显示下次运行的时间和距离下次运行的时间差
- **时间格式化**：使用易读的时间格式（年-月-日 时:分:秒）
- **时间差格式化**：自动格式化为秒、分钟或小时

## 📚 文档列表

| 文档 | 路径 | 说明 |
|------|------|------|
| 快速上手指南 | [SCHEDULER_README.md](./SCHEDULER_README.md) | 快速开始使用定时任务 |
| 详细使用文档 | [../../docs/scheduler_guide.md](../../docs/scheduler_guide.md) | 完整的功能说明和配置指南 |
| 配置示例 | [settings_schedule_examples.py](./settings_schedule_examples.py) | 各种定时任务配置示例 |
| 使用方法总结 | [SCHEDULER_SUMMARY.md](./SCHEDULER_SUMMARY.md) | 所有使用方法的总结 |
| 资源监控说明 | [SCHEDULER_RESOURCE_MONITOR.md](./SCHEDULER_RESOURCE_MONITOR.md) | 资源监控功能详细说明 |

## 🚀 快速开始

### 1. 启动定时任务

```bash
python run.py --schedule
```

### 2. 启用资源监控

在 `settings.py` 中设置：

```python
SCHEDULER_RESOURCE_MONITOR_ENABLED = True
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

## ⚙️ 配置文件

定时任务配置位于 `ofweek_standalone/settings.py`：

```python
# 启用定时任务
SCHEDULER_ENABLED = True

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',           # 爬虫名称
        'cron': '*/2 * * * *',       # 每2分钟执行一次
        'enabled': True,              # 任务启用状态
        'args': {},                  # 传递给爬虫的参数
        'priority': 10               # 任务优先级
    }
]

# 定时任务高级配置
SCHEDULER_CHECK_INTERVAL = 1      # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3      # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600      # 单个任务超时时间（秒）

# 资源监控配置（可选）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True   # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300   # 资源检查间隔（秒），默认5分钟
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600  # 资源泄露检测阈值（秒），默认1小时
```

## 📅 Cron 表达式

Cron 表达式格式：`分 时 日 月 周`

### 常用示例

| Cron 表达式 | 说明 |
|------------|------|
| `*/1 * * * *` | 每1分钟执行一次 |
| `*/2 * * * *` | 每2分钟执行一次 |
| `*/5 * * * *` | 每5分钟执行一次 |
| `0 * * * *` | 每小时执行一次 |
| `0 */2 * * *` | 每2小时执行一次 |
| `0 0 * * *` | 每天凌晨执行一次 |
| `0 0 * * 1` | 每周一凌晨执行一次 |
| `0 0 1 * *` | 每月1号凌晨执行一次 |

## 🎯 最佳实践

1. **启用资源监控**：对于长时间运行的调度器，建议启用资源监控
2. **定期检查日志**：定期查看资源监控日志，确保资源使用正常
3. **调整监控间隔**：根据任务执行频率，调整合适的监控间隔
4. **设置合适的阈值**：根据实际情况，设置合适的资源泄露检测阈值
5. **及时处理资源泄露**：如果检测到资源泄露，及时处理

## ❓ 常见问题

### Q: 如何停止调度器？

**A:** 按 `Ctrl+C` 停止调度器。

### Q: 如何修改调度间隔？

**A:** 修改 `settings.py` 中的 `SCHEDULER_JOBS` 配置，然后重启调度器。

### Q: 如何查看任务执行统计？

**A:** 调度器会在日志中输出任务执行统计信息。

### Q: 如何禁用资源监控？

**A:** 将 `SCHEDULER_RESOURCE_MONITOR_ENABLED` 设置为 `False`。

### Q: 资源监控会影响性能吗？

**A:** 资源监控会定期执行垃圾回收，可能会对性能产生轻微影响。如果不需要监控，可以禁用。

### Q: 如何安装 psutil？

**A:** 运行 `pip install psutil` 安装资源监控所需的依赖。

### Q: 调度器不执行任务怎么办？

**A:** 检查以下几点：
1. 确认 `SCHEDULER_ENABLED = True`
2. 确认任务配置中的 `enabled = True`
3. 确认 cron 表达式格式正确
4. 检查日志中是否有错误信息

## 📝 配置参数说明

### 基础配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SCHEDULER_ENABLED` | bool | False | 是否启用定时任务 |
| `SCHEDULER_JOBS` | list | [] | 定时任务配置列表 |

### 高级配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SCHEDULER_CHECK_INTERVAL` | int | 1 | 调度器检查间隔（秒） |
| `SCHEDULER_MAX_CONCURRENT` | int | 3 | 最大并发任务数 |
| `SCHEDULER_JOB_TIMEOUT` | int | 3600 | 单个任务超时时间（秒） |

### 资源监控配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SCHEDULER_RESOURCE_MONITOR_ENABLED` | bool | True | 是否启用资源监控 |
| `SCHEDULER_RESOURCE_CHECK_INTERVAL` | int | 300 | 资源检查间隔（秒），默认5分钟 |
| `SCHEDULER_RESOURCE_LEAK_THRESHOLD` | int | 3600 | 资源泄露检测阈值（秒），默认1小时 |

### 任务配置参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `spider` | str | ✅ | 爬虫名称（对应spider的name属性） |
| `cron` | str | ✅ | cron表达式 |
| `enabled` | bool | ❌ | 任务启用状态（默认True） |
| `args` | dict | ❌ | 传递给爬虫的参数（默认{}） |
| `priority` | int | ❌ | 任务优先级（默认10） |
