# Crawlo 定时任务功能技术文档

## 1. 概述

为满足用户在不依赖服务器 crontab 的场景下实现定时爬虫的需求，设计一个可插拔的定时任务功能模块。该功能独立于 Crawlo 主进程运行，与主框架解耦，用户可根据需要选择启用或禁用。

## 2. 设计原则

- **可插拔性**：用户可自由选择启用或禁用，不影响原有功能
- **独立运行**：定时任务独立于 Crawlo 主进程，不受其生命周期影响
- **零侵入性**：不对现有 Crawlo 核心代码进行修改
- **配置驱动**：通过配置文件控制功能行为
- **资源隔离**：独立的资源管理和内存空间

## 3. 架构设计

### 3.1 核心组件

#### 3.1.1 SchedulerDaemon（调度守护进程）
- 独立运行的守护进程
- 管理所有定时任务的执行
- 与 Crawlo 主进程完全解耦
- 支持并发控制、超时处理、错误重试
- 提供监控统计功能

#### 3.1.2 ScheduledJob（定时任务）
- 代表单个定时任务
- 包含任务配置和执行逻辑
- 支持 cron 表达式和固定间隔
- 支持重试配置

#### 3.1.3 TimeTrigger（时间触发器）
- 解析时间表达式
- 计算下次执行时间
- 触发任务执行

### 3.2 文件结构

```
crawlo/
├── scheduling/                 # 定时任务模块
│   ├── __init__.py
│   ├── scheduler_daemon.py     # 调度守护进程
│   ├── job.py                 # 任务定义
│   ├── trigger.py             # 时间触发器
│   └── registry.py            # 任务注册表
├── commands/
│   └── schedule.py            # 命令行支持
└── settings/
    └── default_settings.py    # 默认配置
```

## 4. 配置选项

### 4.1 基础配置
```python
# settings.py
SCHEDULER_ENABLED = False      # 启用定时任务 - 默认禁用
SCHEDULER_JOBS = []           # 定时任务配置列表
```

### 4.2 高级配置
```python
SCHEDULER_CHECK_INTERVAL = 1   # 检查间隔（秒）- 默认1秒
SCHEDULER_MAX_CONCURRENT = 3   # 最大并发任务数 - 默认3个
SCHEDULER_JOB_TIMEOUT = 3600   # 单个任务超时时间（秒）- 默认1小时
```

### 4.3 任务配置
```python
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',             # 爬虫名称（对应爬虫的name属性）
        'cron': '0 */2 * * *',          # 每2小时执行一次
        'enabled': True,                 # 任务启用状态
        'args': {'date': 'today'},       # 传递给爬虫的参数
        'priority': 10,                 # 任务优先级
        'max_retries': 3,               # 最大重试次数
        'retry_delay': 60               # 重试延迟（秒）
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
        'spider': 'of_week',             # 爬虫名称（对应爬虫的name属性）
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
        process = CrawlerProcess()
        asyncio.run(process.crawl('of_week'))

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

## 7. 运行机制

### 7.1 独立守护进程
- 定时任务以独立守护进程方式运行
- 与 Crawlo 主进程完全分离
- 主进程退出不影响定时任务运行

### 7.2 任务调度逻辑
```python
# 调度主循环伪代码
async def scheduler_main_loop():
    while daemon_running:
        for job in active_jobs:
            if should_execute(job):
                execute_job(job)
        await asyncio.sleep(CHECK_INTERVAL)
```

### 7.3 并发控制
- 使用 `asyncio.Semaphore` 控制并发任务数
- 防止资源耗尽
- 可通过 `SCHEDULER_MAX_CONCURRENT` 配置

### 7.4 超时处理
- 使用 `asyncio.wait_for` 实现超时控制
- 超时后取消任务并记录日志
- 可通过 `SCHEDULER_JOB_TIMEOUT` 配置

### 7.5 错误重试
- 支持任务失败后自动重试
- 可配置最大重试次数和重试延迟
- 重试成功后重置重试计数

### 7.6 监控统计
- 记录任务执行次数、成功率、失败次数
- 提供每个任务的详细统计信息
- 可通过 `get_stats()` 方法获取

### 7.7 生命周期管理
- **启动**：通过配置或命令启动独立进程
- **运行**：持续监控和执行定时任务
- **停止**：支持优雅停止和信号处理
- **清理**：自动清理所有注册的资源

## 8. 与现有启动模式的兼容性

### 8.1 脚本启动模式兼容
- 现有启动方式 `python run.py` 不受影响
- 新增 `python run.py --schedule` 启动定时任务
- 通过命令行参数区分运行模式

### 8.2 命令行启动模式兼容
- 现有启动方式 `crawlo run of_week` 不受影响
- 新增 `crawlo schedule` 命令启动定时任务
- 与现有的命令行扩展机制集成

### 8.3 配置系统集成
- 定时任务配置通过 settings 系统管理
- 与现有的配置优先级和加载机制一致
- 不需要修改现有配置文件结构

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

## 10. 错误处理

### 10.1 任务执行错误
- 任务执行异常被捕获和记录
- 不影响其他任务的执行
- 支持错误重试机制

### 10.2 资源管理
- 任务超时自动终止
- 防止资源泄露
- 优雅的任务停止
- 统一的资源清理

## 11. 监控和统计

### 11.1 统计信息
调度器提供以下统计信息：
- 总执行次数
- 成功执行次数
- 失败执行次数
- 每个任务的详细统计

### 11.2 获取统计信息
```python
from crawlo.scheduling import SchedulerDaemon

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

## 12. 优势

1. **完全可插拔**：用户可选择启用或禁用，不影响原有功能
2. **独立运行**：定时任务独立于主进程，不受其生命周期影响
3. **配置简单**：只需修改配置即可启用或禁用
4. **零侵入性**：不对现有代码进行修改
5. **资源隔离**：独立的资源管理，避免相互干扰
6. **灵活部署**：支持独立运行或集成运行
7. **兼容现有模式**：不破坏现有的启动方式
8. **无缝集成**：与 Crawlo 的配置系统和命令行系统完美集成
9. **并发控制**：防止资源耗尽
10. **超时保护**：防止任务无限期运行
11. **错误重试**：提高任务可靠性
12. **监控统计**：便于问题排查和性能优化

## 13. 注意事项

1. **配置控制**：必须显式设置 `SCHEDULER_ENABLED = True` 才会启动定时任务
2. **资源管理**：注意控制并发任务数量，避免资源耗尽
3. **监控日志**：提供充分的日志支持，便于问题排查
4. **安全性**：确保定时任务的安全性，避免无限循环等问题
5. **兼容性**：确保与现有启动模式的兼容性，不要破坏原有功能
6. **独立进程**：定时任务以独立进程运行，需要单独启动
7. **优雅停止**：停止时会等待正在运行的任务完成（最多30秒）
8. **资源清理**：停止时会自动清理所有注册的资源
