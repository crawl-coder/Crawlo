# 定期执行不操心：Crawlo 定时任务调度

> 每天凌晨 3 点自动爬新闻，每周一爬一次报表——设好就不用管了。

---

## 爬虫不是跑一次就完事的

很多爬虫场景需要周期性执行：

- 每天早上 8 点爬取新闻头条
- 每小时监控一次商品价格变化
- 每周一凌晨生成数据报表
- 每 30 分钟采集一次天气数据

手动执行？不现实。`crontab`？管理起来很麻烦。**Crawlo 内置了定时任务调度器。**

---

## 快速上手

### 1. 启用调度器

```python
# settings.py
SCHEDULER_ENABLED = True
```

### 2. 配置定时任务

两种触发方式任选：

**Cron 表达式（精确到秒）：**

```python
SCHEDULER_JOBS = [
    {
        'spider': 'of_week',
        'cron': '*/2 * * * *',       # 每 2 分钟执行一次
        'enabled': True,              # 任务启用状态
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'args': {},                   # 传递给爬虫的参数
    },
]
```

**时间间隔（更直观）：**

```python
SCHEDULER_JOBS = [
    {
        'spider': 'heartbeat_spider',
        'interval': {'seconds': 30},     # 每 30 秒
    },
    {
        'spider': 'price_checker',
        'interval': {'minutes': 15},     # 每 15 分钟
    },
    {
        'spider': 'monitor_spider',
        'interval': {'hours': 1},        # 每 1 小时
    },
    {
        'spider': 'weekly_report',
        'cron': '0 0 0 * * 1',           # 每周一凌晨 0 点
    },
]
```

### 3. 启动调度器

```bash
crawlo schedule
```

调度器作为守护进程运行，自动按计划执行配置好的任务。

---

## Cron 表达式速查

Crawlo 支持 5 位和 6 位 Cron 表达式：

```
秒 分 时 日 月 星期     （6位）
   分 时 日 月 星期     （5位，秒默认为0）
```

| 表达式 | 含义 |
|--------|------|
| `0 0 * * * *` | 每小时整点 |
| `0 30 9 * * *` | 每天 9:30 |
| `0 0 0 * * 1` | 每周一凌晨 0:00 |
| `0 */15 * * * *` | 每 15 分钟 |
| `0 0 9,18 * * *` | 每天 9:00 和 18:00 |
| `0 0 */6 * * *` | 每 6 小时 |

---

## 配置详解

### 任务配置

```python
SCHEDULER_JOBS = [
    {
        'spider': 'my_spider',       # 爬虫名称
        'cron': '0 0 8 * * *',       # cron 或 interval 二选一
        'interval': {'hours': 2},    # interval 模式（与 cron 二选一）
        'args': {'keyword': 'AI'},   # 传递给 Spider 的参数
        'enabled': True,             # 是否启用
        'priority': 0,               # 优先级（数值越小越优先）
        'timeout': 3600,             # 单次超时（秒），不同爬虫可设不同值
        'max_retries': 3,            # 失败后重试次数
        'retry_delay': 120,          # 重试间隔（秒）
    },
]
```

### 调度器配置

```python
SCHEDULER_ENABLED = True                # 启用调度器
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300 # 资源检查间隔（秒）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True  # 启用资源监控
```

---

## 运行调度器

两种启动方式任选：

### 方式一：项目 run.py（推荐）

`crawlo startproject` 生成的 `run.py` 自带 `--schedule` 入口：

```python
# run.py（startproject 自动生成）
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # 定时任务模式
        from crawlo.scheduling import start_scheduler
        project_root = os.path.dirname(os.path.abspath(__file__))
        start_scheduler(project_root)
    else:
        # 正常爬虫模式
        asyncio.run(CrawlerProcess().crawl('my_spider'))
```

```bash
# 正常爬虫
python run.py

# 定时任务调度器
python run.py --schedule

# 等价 CLI 命令
crawlo run myspider       # 立即执行爬虫
crawlo run schedule       # 启动定时任务调度器
```

两种方式效果相同，内部调用同一个 `start_scheduler()`。`run.py --schedule` 的优势是自动识别项目根目录。

调度器会持续运行，自动管理任务执行：

```
08:00:00 → 执行 news_spider
08:00:01 → 计算 next = 明天 08:00
08:30:00 → 执行 weather_spider  
09:00:00 → 执行 news_spider（次日）
...
```

---

## Cron vs Interval 对比

| 维度 | Cron | Interval |
|------|------|----------|
| 精度 | 秒级，支持复杂规则 | 秒/分/时/天 |
| 场景 | "每周一三五早上 8 点" | "每 2 小时跑一次" |
| 易读性 | 需要查表 | 直观 |
| 灵活度 | 高（可组合多个时间点） | 低（固定间隔） |

**建议**：简单间隔用 `interval`，复杂时间规则用 `cron`。

---

## 生产环境建议

### 1. 日志持久化

```python
# settings.py
LOG_FILE = 'logs/scheduler.log'
LOG_LEVEL = 'INFO'
```

### 2. 监控告警

调度器会记录每个任务的执行统计：
- 总执行次数
- 成功/失败次数
- 上次执行时间
- 下次计划执行时间

```python
from crawlo.scheduling.registry import get_job_registry

registry = get_job_registry()
for job in registry.get_all_jobs():
    print(f"{job.spider_name}: next at {job.get_next_execution_time()}")
```

---

Crawlo 的定时调度让你**设好就不用管**——到时间自动跑，跑完自动停，下次自动来。

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
