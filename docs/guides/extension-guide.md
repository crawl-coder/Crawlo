# 扩展系统 (Extensions)

> Crawlo 内置 8 个扩展，覆盖日志、监控、健康检查和请求录制等场景。

## 概述

扩展（Extension）是 Crawlo 的插件机制，类似中间件但作用于爬虫生命周期而非单个请求/响应。扩展通过事件订阅实现对爬虫行为的增强。

### 与中间件的区别

| | Extension | Middleware |
|---|---|---|
| 作用域 | 爬虫生命周期 | 请求/响应级别 |
| 事件驱动 | 是（subscribe/notify） | 否（链式调用） |
| 典型场景 | 统计、监控、心跳上报 | 重试、代理、Header 注入 |

## 使用方式

```python
# settings.py
EXTENSIONS = [
    'crawlo.extension.LogIntervalExtension',
    'crawlo.extension.HealthCheckExtension',
]
```

## 内置扩展

### 1. LogIntervalExtension — 定期日志输出

定时输出爬取进度，显示：已抓取页面数、每分钟速率、Item 数、队列 pending 数。

```python
LOG_INTERVAL = 60                  # 输出间隔（秒，默认 60）
```

输出示例：
```
Crawled 239 pages (at 239 pages/min), Got 179 items, Queue: 0 pending
```

### 2. LogStats — 统计收集

自动收集、汇总爬虫运行期间的各项统计指标：

```python
# 自动激活，无需额外配置
# 统计项包括：
#   - request_scheduler_count
#   - response_received_count
#   - item_successful_count
#   - item_discard_count
```

运行结束时输出完整统计摘要。

### 3. HealthCheckExtension — 健康检查

定期上报 Worker 健康状态：

```python
HEALTH_CHECK_INTERVAL = 60                    # 检查间隔（秒）
HEALTH_CHECK_CRITICAL_TASKS_THRESHOLD = 100   # 任务堆积告警阈值
```

检测项：
- Worker 是否正常收发请求
- 队列是否堆积
- 连续空闲时间是否过长
- 任务成功率是否过低

### 4. MemoryMonitorExtension — 内存监控

自动监控进程内存使用情况：

```python
MEMORY_MONITOR_THRESHOLD_MB = 1024            # 内存告警阈值（MB）
MEMORY_MONITOR_CHECK_INTERVAL = 30            # 检查间隔（秒）
```

超阈值时自动记录告警日志，并可选执行垃圾回收。

### 5. MySQLMonitorExtension — MySQL 连接池监控

监控 MySQLPipeline 的连接池状态：

```python
MYSQL_MONITOR_INTERVAL = 60                   # 监控间隔（秒）
```

监控指标：活跃连接数、空闲连接数、等待队列长度、执行耗时分布。

### 6. RedisMonitorExtension — Redis 状态监控

监控 Redis 连接状态和去重集合大小：

```python
REDIS_MONITOR_INTERVAL = 60                   # 监控间隔（秒）
```

监控指标：去重集合大小、内存使用、命中率、连接数。

### 7. RequestRecorderExtension — 请求录制

记录所有发出的请求，便于事后分析：

```python
REQUEST_RECORDER_ENABLED = True                # 启用录制
REQUEST_RECORDER_DIR = 'requests_record'       # 存储目录
REQUEST_RECORDER_FORMAT = 'json'               # 输出格式: json / csv
```

每条记录包含：URL、方法、请求头、状态码、响应时间、重试次数。

### 8. PerformanceMonitor — 性能监控

实时监控爬虫整体的 CPU、内存、网络 I/O 性能指标：

```python
PERFORMANCE_MONITOR_INTERVAL = 30              # 采集间隔（秒）
```

## ExtensionManager 架构

```python
from crawlo.extension import ExtensionManager

# 内部流程：
# 1. ExtensionManager 从 settings 加载 EXTENSIONS 列表
# 2. 实例化每个扩展，调用 from_crawler() 或 __init__()
# 3. 根据扩展实现的方法自动订阅对应事件
# 4. 事件发生时按优先级通知所有订阅者
```

### 事件订阅映射

| 扩展实现的方法 | 自动订阅的事件 |
|--------------|-------------|
| `spider_opened` | `SPIDER_OPENED` |
| `spider_closed` | `SPIDER_CLOSED` |
| `request_scheduled` | `REQUEST_SCHEDULED` |
| `response_received` | `RESPONSE_RECEIVED` |
| `item_successful` | `ITEM_SUCCESSFUL` |
| `item_discard` | `ITEM_DISCARD` |

## 自定义扩展

```python
# myextensions.py
from crawlo.extension import BaseExtension

class CustomExtension(BaseExtension):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.start_time = None

    async def spider_opened(self, spider):
        self.start_time = time.time()
        self.logger.info(f"爬虫 {spider.name} 启动")

    async def spider_closed(self, spider):
        elapsed = time.time() - self.start_time
        self.logger.info(f"爬虫 {spider.name} 结束，耗时 {elapsed:.0f}s")
```

```python
# settings.py
EXTENSIONS = ['myproject.myextensions.CustomExtension']
```
