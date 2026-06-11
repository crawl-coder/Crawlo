# 定时任务调度器

> 内置 Cron + Interval 双触发模式，支持守护进程运行、自动重试、并发控制和资源监控。

## 概述

Crawlo 内置定时任务调度器，支持周期性执行爬虫任务。调度器以守护进程方式运行，按计划自动触发爬虫执行。

### 架构

```
┌──────────────────────────────────────────────┐
│                SchedulerDaemon                 │
│                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ TimeTrigger│   │ JobRegistry│  │ JobExecutor│  │
│  │ ─ Cron    │   │ ─ 注册   │   │ ─ 信号量 │  │
│  │ ─ Interval│   │ ─ 查询   │   │ ─ 超时   │  │
│  │ ─ 下次时间│   │ ─ 排序   │   │ ─ 重试   │  │
│  └──────────┘   └──────────┘   └──────────┘  │
│        │              │              │        │
│        ▼              ▼              ▼        │
│  ┌──────────────────────────────────────────┐ │
│  │          Resource Manager                 │ │
│  │  资源监控 + 内存泄漏检测 + 连接池管理     │ │
│  └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

## 快速开始

### 1. 启用调度器

```python
# settings.py
SCHEDULER_ENABLED = True
```

### 2. 配置定时任务

**Cron 表达式（精确到秒）：**

```python
SCHEDULER_JOBS = [
    {
        'spider': 'news_spider',
        'cron': '0 0 * * * *',       # 每小时整点
        'enabled': True,
        'priority': 10,
        'timeout': 3600,              # 单次超时（秒）
        'max_retries': 3,
        'retry_delay': 60,
        'args': {'keyword': 'AI'},
    },
]
```

**时间间隔（更直观）：**

```python
SCHEDULER_JOBS = [
    {'spider': 'heartbeat', 'interval': {'seconds': 30}},                    # 每 30 秒
    {'spider': 'checker',   'interval': {'minutes': 15}},                    # 每 15 分钟
    {'spider': 'monitor',   'interval': {'hours': 1}},                       # 每 1 小时
    {'spider': 'crawler',   'interval': {'days': 1}},                        # 每 24 小时
    {'spider': 'report',    'interval': {'hours': 1, 'minutes': 30}},        # 每 1.5 小时（组合）
]
```

### 3. 启动

```bash
crawlo schedule
# 或
python run.py --schedule
```

## Cron 表达式

### 格式

Crawlo 支持标准的 5 位和 6 位 Cron 表达式：

```
秒 分 时 日 月 星期     （6位，完整）
   分 时 日 月 星期     （5位，秒字段默认为 0）
```

### 字段语法

| 字段 | 范围 | 特殊字符 |
|------|------|---------|
| 秒 (可选) | 0-59 | `*` `*/N` `N` `N-M` `,` |
| 分钟 | 0-59 | `*` `*/N` `N` `N-M` `,` |
| 小时 | 0-23 | `*` `*/N` `N` `N-M` `,` |
| 日 | 1-31 | `*` `*/N` `N` `N-M` `,` |
| 月 | 1-12 | `*` `*/N` `N` `N-M` `,` |
| 星期 | 0-6 (0=周日) | `*` `*/N` `N` `N-M` `,` |

### 常用示例

| 表达式 | 含义 |
|--------|------|
| `0 0 * * * *` | 每小时整点 |
| `0 30 9 * * *` | 每天 9:30 |
| `0 0 0 * * 1` | 每周一凌晨 0:00 |
| `0 */15 * * * *` | 每 15 分钟 |
| `0 0 9,18 * * *` | 每天 9:00 和 18:00 |
| `0 0 */6 * * *` | 每 6 小时 |

## 完整配置参考

### 任务配置（SCHEDULER_JOBS 每个条目）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `spider` | `str` | — | 爬虫名称（必需） |
| `cron` | `str` | `None` | Cron 表达式，与 `interval` 二选一 |
| `interval` | `dict` | `None` | 时间间隔字典，与 `cron` 二选一 |
| `args` | `dict` | `{}` | 传递给爬虫的参数 |
| `enabled` | `bool` | `True` | 启用状态 |
| `priority` | `int` | `0` | 任务优先级（越小越优先） |
| `timeout` | `int` | `None` | 单次超时秒数（不设则用全局 `SCHEDULER_JOB_TIMEOUT`） |
| `max_retries` | `int` | `0` | 失败后重试次数 |
| `retry_delay` | `int` | `60` | 重试间隔（秒） |

### 调度器全局配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SCHEDULER_ENABLED` | `False` | 启用调度器 |
| `SCHEDULER_JOB_TIMEOUT` | `7200` | 全局任务超时（秒），任务级 `timeout` 优先级更高 |
| `SCHEDULER_CHECK_INTERVAL` | `1` | 调度检查间隔（秒） |
| `SCHEDULER_MAX_CONCURRENT` | `3` | 最大并发任务数 |
| `SCHEDULER_RESOURCE_CHECK_INTERVAL` | `300` | 资源监控检查间隔（秒） |
| `SCHEDULER_RESOURCE_MONITOR_ENABLED` | `True` | 启用资源监控（需 psutil） |

## 调度机制

### 主循环

调度器使用基于最近任务时间的智能 Sleep，避免忙轮询：

```python
# daemon/scheduler.py
while self.running:
    min_next = min(job.next_execution_time for job in jobs)
    sleep_sec = min(min_next - now, check_interval)
    await asyncio.sleep(sleep_sec)
    await self._check_and_execute_jobs()
```

### 并发控制

通过 `asyncio.Semaphore` 限制同时运行的任务数，默认最大 3 个并发：

```python
# daemon/executor.py
async def execute_with_semaphore(self, job):
    async with self._semaphore:     # 默认 max_concurrent=3
        await self.execute_job(job)
```

### 任务超时与重叠处理

相同任务不会并发执行。`is_executing` 标志位互斥：

```python
# job.py
def should_execute(self, current_time):
    if current_time >= self.next_execution_time and not self.is_executing:
        return True
    return False
```

当超时触发后：

```
t=0     任务开始，is_executing=True
t=timeout  超时 → cancel → 可选重试（带退避延迟）
           → is_executing=False
t=next_cron  → 正常执行（不丢失）
```

### 时间漂移防止

下次执行时间基于**原定调度时间**（而非实际开始时间）计算，防止长时间任务导致 cron 漂移：

```
cron '0 */6 * * *', 0:00 开始, 8:00 完成
修复前: next = 6:00 + 6h → 14:00（漂移）
修复后: next = get_next_time(6:00) → 12:00（对齐）
```

## Cron vs Interval 对比

| 维度 | Cron | Interval |
|------|------|----------|
| 精度 | 秒级 | 秒/分/时/天 |
| 场景 | "每周一三五早上 8 点" | "每 2 小时" |
| 易读性 | 需要查表 | 直观 |
| 灵活度 | 高（可组合） | 低（固定间隔） |

**建议**：简单间隔用 `interval`，复杂时间规则用 `cron`。

## 监控与运维

### 查看执行统计

```python
from crawlo.scheduling.registry import get_job_registry

registry = get_job_registry()
for job in registry.get_all_jobs():
    print(f"{job.spider_name}: next at {job.get_next_execution_time()}")
```

### 日志

```python
LOG_FILE = 'logs/scheduler.log'
LOG_LEVEL = 'INFO'
```

### 资源监控

启用时自动检测：内存泄漏、CPU 使用率、活跃资源数量。依赖 `psutil`：

```bash
pip install psutil
```
