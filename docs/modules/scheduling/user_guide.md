# Crawlo 定时任务功能使用指南

## 1. 概述

Crawlo 定时任务功能允许用户在不依赖系统 crontab 的情况下，在应用程序内部实现定时爬虫任务。该功能完全独立于 Crawlo 主进程运行，与主框架解耦，用户可根据需要选择启用或禁用。

## 2. 功能特点

- **可插拔性**：用户可自由选择启用或禁用，不影响原有功能
- **独立运行**：定时任务独立于 Crawlo 主进程，不受其生命周期影响
- **零侵入性**：不对现有 Crawlo 核心代码进行修改
- **配置驱动**：通过配置文件控制功能行为
- **资源隔离**：独立的资源管理和内存空间
- **兼容现有模式**：不破坏现有的启动方式
- **并发控制**：防止资源耗尽
- **超时保护**：防止任务无限期运行
- **错误重试**：提高任务可靠性
- **监控统计**：便于问题排查和性能优化

## 3. 安装和配置

定时任务功能已集成到 Crawlo 框架中，无需额外安装。

## 4. 配置选项

### 4.1 基础配置

```python
# settings.py
SCHEDULER_ENABLED = False      # 启用定时任务 - 默认禁用
SCHEDULER_JOBS = []           # 定时任务配置列表
```

### 4.2 高级配置

```python
SCHEDULER_CHECK_INTERVAL = 1   # 调度器检查间隔（秒）- 默认1秒
SCHEDULER_MAX_CONCURRENT = 3   # 最大并发任务数 - 默认3个
SCHEDULER_JOB_TIMEOUT = 3600   # 单个任务超时时间（秒）- 默认1小时
```

### 4.3 任务配置

```python
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',             # 爬虫名称（对应spider的name属性）
        'cron': '0 */2 * * *',          # 每2小时执行一次
        'enabled': True,                 # 任务启用状态
        'args': {},                      # 传递给爬虫的参数
        'priority': 10,                  # 任务优先级
        'max_retries': 3,               # 最大重试次数
        'retry_delay': 60                # 重试延迟（秒）
    },
    {
        'spider': 'my_hourly_spider',    # 爬虫名称
        'interval': {'minutes': 30},     # 每30分钟执行一次
        'enabled': True
    }
]
```

## 5. 使用方式

### 5.1 不使用定时任务（默认）

```python
# settings.py - 默认配置，定时任务不运行
SCHEDULER_ENABLED = False  # 默认值
SCHEDULER_JOBS = []        # 空列表
```

### 5.2 启用定时任务

```python
# settings.py
SCHEDULER_ENABLED = True   # 显式启用
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',             # 爬虫名称（对应spider的name属性）
        'cron': '0 */2 * * *',          # 每2小时执行一次
        'enabled': True,                 # 任务启用状态
        'args': {},                      # 传递给爬虫的参数
        'priority': 10                   # 任务优先级
    },
    {
        'spider': 'my_hourly_spider',    # 爬虫名称
        'interval': {'minutes': 30},     # 每30分钟执行一次
        'enabled': True
    }
]
```

## 6. 启动方式

### 6.1 通过现有脚本启动

```python
# examples/ofweek_standalone/run.py 的增强版本
import sys
import asyncio
from crawlo.crawler import CrawlerProcess

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # 启动定时任务模式
        from crawlo.scheduling import start_scheduler
        start_scheduler()
    else:
        # 正常爬虫运行模式 - 不破坏现有启动方式
        asyncio.run(CrawlerProcess().crawl('of_week'))

if __name__ == '__main__':
    main()
```

启动命令：
```bash
# 启动定时任务守护进程
python run.py --schedule
```

### 6.2 通过 Crawlo 命令启动

```bash
# 启动定时任务服务
crawlo schedule  # 启动定时任务服务
```

## 7. Cron 表达式语法

支持标准的5位cron表达式：`分钟 小时 日 月 星期`

- `*`：任意值
- `*/n`：步长，如 `*/5` 表示每隔5个单位
- `n-m`：范围，如 `1-5` 表示1到5
- `n,m,o`：多个值，如 `1,3,5` 表示1、3、5

常用示例：
- `0 */2 * * *`：每2小时的0分执行
- `0 2 * * *`：每天凌晨2点执行
- `*/30 * * * *`：每30分钟执行一次
- `0 0 * * 0`：每周日凌晨0点执行

## 8. 时间间隔语法

也可以使用时间间隔方式：

```python
{
    'spider': 'my_spider',
    'interval': {
        'seconds': 30,    # 每30秒
        'minutes': 5,     # 每5分钟
        'hours': 2,       # 每2小时
        'days': 1         # 每天
    },
    'enabled': True
}
```

## 9. 实际使用场景

### 9.1 场景1：仅定时运行

```bash
# 启动定时任务守护进程
python run.py --schedule
# 或
crawlo schedule
```

### 9.2 场景2：混合模式

```bash
# 既可手动运行爬虫，也可定时运行
crawlo run of_week  # 手动运行
crawlo schedule     # 启动定时任务
```

## 10. 高级功能

### 10.1 并发控制

通过 `SCHEDULER_MAX_CONCURRENT` 配置控制同时运行的任务数量：

```python
SCHEDULER_MAX_CONCURRENT = 5  # 最多同时运行5个任务
```

### 10.2 超时处理

通过 `SCHEDULER_JOB_TIMEOUT` 配置任务超时时间：

```python
SCHEDULER_JOB_TIMEOUT = 7200  # 任务超时时间为2小时
```

### 10.3 错误重试

在任务配置中添加重试参数：

```python
{
    'spider': 'of_week',
    'cron': '0 */2 * * *',
    'enabled': True,
    'max_retries': 3,      # 最多重试3次
    'retry_delay': 60       # 每次重试间隔60秒
}
```

### 10.4 监控统计

获取调度器统计信息：

```python
from crawlo.scheduling import SchedulerDaemon
from crawlo.project import get_settings

settings = get_settings()
daemon = SchedulerDaemon(settings)
stats = daemon.get_stats()
print(stats)
```

输出示例：
```json
{
    "total_executions": 100,
    "successful_executions": 95,
    "failed_executions": 5,
    "job_stats": {
        "of_week": {
            "total": 50,
            "successful": 48,
            "failed": 2,
            "last_execution": 1234567890.0,
            "last_success": 1234567890.0,
            "last_failure": 1234567880.0
        }
    }
}
```

## 11. 错误处理

- 任务执行异常被捕获和记录
- 不影响其他任务的执行
- 支持错误重试机制
- 任务超时自动终止
- 防止资源泄露
- 优雅的任务停止

## 12. 注意事项

1. **配置控制**：必须显式设置 `SCHEDULER_ENABLED = True` 才会启动定时任务
2. **资源管理**：注意控制并发任务数量，避免资源耗尽
3. **监控日志**：提供充分的日志支持，便于问题排查
4. **安全性**：确保定时任务的安全性，避免无限循环等问题
5. **兼容性**：确保与现有启动模式的兼容性，不要破坏原有功能
6. **独立进程**：定时任务以独立进程运行，需要单独启动
7. **优雅停止**：停止时会等待正在运行的任务完成（最多30秒）
8. **资源清理**：停止时会自动清理所有注册的资源

## 13. 最佳实践

### 13.1 合理设置并发数

根据服务器资源和任务特性设置合适的并发数：

```python
# 低配置服务器
SCHEDULER_MAX_CONCURRENT = 1

# 中等配置服务器
SCHEDULER_MAX_CONCURRENT = 3

# 高配置服务器
SCHEDULER_MAX_CONCURRENT = 5
```

### 13.2 设置合理的超时时间

根据任务执行时间设置超时：

```python
# 快速任务（几分钟内完成）
SCHEDULER_JOB_TIMEOUT = 600  # 10分钟

# 中等任务（半小时内完成）
SCHEDULER_JOB_TIMEOUT = 1800  # 30分钟

# 慢速任务（几小时内完成）
SCHEDULER_JOB_TIMEOUT = 7200  # 2小时
```

### 13.3 使用重试机制

对于不稳定的任务，启用重试：

```python
{
    'spider': 'unstable_spider',
    'cron': '0 */2 * * *',
    'enabled': True,
    'max_retries': 3,
    'retry_delay': 120  # 重试间隔2分钟
}
```

### 13.4 监控任务执行

定期查看统计信息，了解任务执行情况：

```python
# 在调度器运行时，可以通过日志查看统计信息
# 或者通过 get_stats() 方法获取
```

## 14. 故障排查

### 14.1 任务未执行

检查以下内容：
1. 确认 `SCHEDULER_ENABLED = True`
2. 确认任务配置正确
3. 检查 cron 表达式或时间间隔
4. 查看日志文件

### 14.2 任务超时

检查以下内容：
1. 增加 `SCHEDULER_JOB_TIMEOUT` 值
2. 优化爬虫性能
3. 检查网络连接
4. 查看任务执行日志

### 14.3 资源耗尽

检查以下内容：
1. 减少 `SCHEDULER_MAX_CONCURRENT` 值
2. 优化爬虫资源使用
3. 检查服务器资源使用情况
4. 查看系统日志

## 15. 示例项目

完整的示例项目请参考：
- [examples/ofweek_standalone](file:///Users/oscar/projects/Crawlo/examples/ofweek_standalone)
- [examples/ofweek_standalone/settings_schedule_example.py](file:///Users/oscar/projects/Crawlo/examples/ofweek_standalone/ofweek_standalone/settings_schedule_example.py)
