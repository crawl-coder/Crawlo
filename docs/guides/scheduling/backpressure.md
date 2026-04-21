# 背压系统

背压系统（Backpressure System）是 Crawlo 框架的核心特性之一，用于防止队列溢出和内存耗尽。

---

## 🎯 什么是背压？

**背压**是一种流量控制机制，当消费者处理速度慢于生产者速度时，通过降低生产者的速度来防止系统过载。

### Crawlo 中的背压场景

```
请求生成 (快)  ──────>  队列  ──────>  请求处理 (慢)
                     ↑
                 队列满了怎么办？
                 背压系统介入！
```

**没有背压的后果**：
- ❌ 内存耗尽（OOM）
- ❌ 队列溢出
- ❌ 系统崩溃
- ❌ 数据丢失

---

## 📊 Crawlo 背压系统架构

Crawlo 实现的是**多维度自适应背压系统**，包含以下策略：

### 1. QueueSizeStrategy（队列大小策略）

**原理**：基于队列使用率动态调整延迟

```python
使用率 = pending_count / max_queue_size
```

**延迟计算**：

| 使用率 | 延迟时间 | 说明 |
|--------|---------|------|
| < 50% | 0.0s | 无背压 |
| 50%-90% | 0.5s - 2.0s | 线性增长 |
| 90%-95% | 2.0s - 5.0s | 指数增长 |
| >= 95% | 5.0s | 最大延迟 |

**配置**：

```python
# settings.py

# 背压策略（推荐 queue_size）
BACKPRESSURE_STRATEGY = 'queue_size'

# 内存队列背压配置
MEMORY_BACKPRESSURE_RATIO = 0.5  # 50% 使用率时触发背压
MEMORY_BACKPRESSURE_DELAY_BASE = 0.5  # 基础延迟0.5秒
MEMORY_BACKPRESSURE_DELAY_MAX = 5.0  # 最大延迟5秒
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 8000  # 队列容量
```

**实际案例**：

优化前：
- 队列容量：3000
- pending：2955
- 使用率：98.5%
- 延迟：5.0s
- 速率：11/min ❌

优化后：
- 队列容量：8000
- pending：2955
- 使用率：36.9%
- 延迟：0.0s ✅
- 速率：53-69/min ✅

**性能提升：482%** 🚀

### 2. 智能背压（多维度自适应）

**原理**：基于队列、吞吐、性能三大维度综合评分

**配置**：

```python
# settings.py
INTELLIGENT_BACKPRESSURE_ENABLED = True  # 启用智能背压

INTELLIGENT_BACKPRESSURE_CONFIG = {
    'window_size': 30,              # 采样窗口（秒）
    'collect_interval': 1,          # 采集间隔（秒）
    'queue_weights': (0.4, 0.3, 0.3),  # 队列:吞吐:性能权重
    'score_thresholds': (50, 70, 85),  # 警告/危险/严重阈值
    'base_delay': 0.5,              # 基础延迟
    'max_delay': 5.0,               # 最大延迟
}
```

> ⚠️ **注意**：对于大多数场景，使用 `queue_size` 策略即可，智能背压适合复杂场景。

```python
# settings.py
BACKPRESSURE_CPU_THRESHOLD = 0.9  # 90% CPU 使用率触发
BACKPRESSURE_CPU_MAX_DELAY = 2.0  # 最大延迟2秒
```

### 4. ErrorRateStrategy（错误率策略）

**原理**：基于请求错误率调整

```python
错误率 = failed_requests / total_requests
```

**配置**：

```python
# settings.py
BACKPRESSURE_ERROR_THRESHOLD = 0.3  # 30% 错误率触发
BACKPRESSURE_ERROR_MAX_DELAY = 4.0  # 最大延迟4秒
```

---

## ⚙️ 配置指南

### 基础配置

```python
# settings.py

# 启用背压系统
BACKPRESSURE_ENABLED = True

# 背压策略（多选）
BACKPRESSURE_STRATEGIES = [
    'queue_size',    # 队列大小策略
    'memory',        # 内存策略
    'cpu',           # CPU策略
    'error_rate',    # 错误率策略
]

# 背压阈值
BACKPRESSURE_RATIO = 0.5  # 队列使用率 50% 触发
BACKPRESSURE_MEMORY_THRESHOLD = 0.8  # 内存 80% 触发
BACKPRESSURE_CPU_THRESHOLD = 0.9  # CPU 90% 触发
BACKPRESSURE_ERROR_THRESHOLD = 0.3  # 错误率 30% 触发

# 最大延迟
BACKPRESSURE_MAX_DELAY = 5.0  # 全局最大延迟（秒）

# 队列容量
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 8000  # 内存队列
REDIS_SCHEDULER_MAX_QUEUE_SIZE = 20000  # Redis 队列
```

### 高级配置

```python
# settings.py

# 背压日志
BACKPRESSURE_LOG_LEVEL = 'INFO'  # DEBUG/INFO/WARNING
BACKPRESSURE_LOG_INTERVAL = 60  # 每 60 秒打印一次背压状态

# 动态调整
BACKPRESSURE_ADAPTIVE = True  # 启用自适应调整
BACKPRESSURE_ADAPTIVE_INTERVAL = 300  # 每 5 分钟调整一次

# 告警
BACKPRESSURE_ALERT_ENABLED = True  # 启用告警
BACKPRESSURE_ALERT_THRESHOLD = 0.9  # 90% 使用率告警
BACKPRESSURE_ALERT_CHANNELS = ['feishu', 'email']  # 告警渠道
```

---

## 📈 监控背压状态

### 1. 查看日志

背压系统会定期打印状态：

```
2024-04-20 10:00:00 - INFO: 背压状态:
  - 队列使用率: 36.9% (2955/8000)
  - 内存使用率: 45.2%
  - CPU 使用率: 32.1%
  - 错误率: 2.3%
  - 背压延迟: 0.0s
  - 爬取速率: 53/min
```

### 2. 在爬虫中查看

```python
class MySpider(Spider):
    async def parse(self, response):
        # 查看队列大小
        queue_size = await self.crawler.scheduler.queue.size()
        self.logger.info(f"队列大小: {queue_size}")
        
        # 查看背压延迟
        backpressure_delay = self.crawler.settings.get('BACKPRESSURE_CURRENT_DELAY', 0)
        self.logger.info(f"当前背压延迟: {backpressure_delay}s")
```

### 3. 使用扩展监控

```python
# settings.py
EXTENSIONS = {
    'crawlo.extension.BackpressureExtension': 100,
}
```

---

## 💡 最佳实践

### 1. 始终启用背压

```python
# 推荐配置
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.5  # 50% 就触发，不要设太高
```

### 2. 合理设置队列容量

**内存队列**：
```python
# 小项目（< 10万条）
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000

# 中等项目（10-50万条）
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 10000

# 大项目（> 50万条）
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 20000  # 或使用 Redis
```

**Redis 队列**：
```python
# 推荐使用较大的值
REDIS_SCHEDULER_MAX_QUEUE_SIZE = 20000
```

### 3. 监控告警

```python
# 生产环境推荐
BACKPRESSURE_ALERT_ENABLED = True
BACKPRESSURE_ALERT_THRESHOLD = 0.9  # 90% 告警
BACKPRESSURE_ALERT_CHANNELS = ['feishu']  # 飞书告警
```

### 4. 动态调整

```python
# 启用自适应调整
BACKPRESSURE_ADAPTIVE = True

# 系统会根据历史数据自动优化参数
```

---

## 🔧 故障排查

### 问题 1: 背压延迟过高

**现象**：爬取速率很慢，日志显示背压延迟 5.0s

**原因**：队列使用率过高（> 95%）

**解决方案**：

1. 增大队列容量
```python
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 15000  # 从 8000 增加到 15000
```

2. 降低并发数
```python
CONCURRENCY = 8  # 从 16 降低到 8
```

3. 检查消费速度
```python
# 是否数据库写入慢？
# 是否选择器复杂？
# 是否网络请求慢？
```

### 问题 2: 背压不生效

**现象**：队列满了但没触发背压

**原因**：未启用背压或配置错误

**解决方案**：

```python
# 确保启用
BACKPRESSURE_ENABLED = True

# 检查策略
BACKPRESSURE_STRATEGIES = ['queue_size']  # 至少启用一个
```

### 问题 3: 背压频繁触发

**现象**：背压频繁触发，爬取不稳定

**原因**：背压阈值设置过低

**解决方案**：

```python
# 提高阈值
BACKPRESSURE_RATIO = 0.6  # 从 0.5 提高到 0.6
```

---

## 📊 性能调优

### 场景 1: 高速爬取（目标网站允许）

```python
# settings.py
CONCURRENCY = 32
DOWNLOAD_DELAY = 0
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.7  # 提高到 70%
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 20000
```

### 场景 2: 稳定爬取（推荐）

```python
# settings.py
CONCURRENCY = 12
DOWNLOAD_DELAY = 1.0
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.5  # 50%
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 10000
```

### 场景 3: 保守爬取（严格反爬）

```python
# settings.py
CONCURRENCY = 4
DOWNLOAD_DELAY = 2.0
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.4  # 降低到 40%
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000
```

---

## 🎓 工作原理

### 背压计算流程

```python
# 伪代码
async def calculate_backpressure():
    delays = []
    
    # 1. 队列大小策略
    if 'queue_size' in strategies:
        usage = pending / max_size
        if usage >= BACKPRESSURE_RATIO:
            delay = calculate_queue_delay(usage)
            delays.append(delay)
    
    # 2. 内存策略
    if 'memory' in strategies:
        mem_usage = get_memory_usage()
        if mem_usage >= BACKPRESSURE_MEMORY_THRESHOLD:
            delay = calculate_memory_delay(mem_usage)
            delays.append(delay)
    
    # 3. CPU 策略
    if 'cpu' in strategies:
        cpu_usage = get_cpu_usage()
        if cpu_usage >= BACKPRESSURE_CPU_THRESHOLD:
            delay = calculate_cpu_delay(cpu_usage)
            delays.append(delay)
    
    # 4. 错误率策略
    if 'error_rate' in strategies:
        error_rate = get_error_rate()
        if error_rate >= BACKPRESSURE_ERROR_THRESHOLD:
            delay = calculate_error_delay(error_rate)
            delays.append(delay)
    
    # 取最大延迟
    return max(delays) if delays else 0.0
```

### 延迟应用

```python
# 在调度器中应用背压延迟
async def schedule_next_request():
    delay = await calculate_backpressure()
    
    if delay > 0:
        logger.info(f"背压触发，延迟 {delay}s")
        await asyncio.sleep(delay)
    
    request = await queue.pop()
    await downloader.download(request)
```

---

## 📚 相关文档

- [调度指南概览](../index.md)
- [配置指南](../configuration/index.md)
- [核心概念](../../concepts/index.md)
- [限速策略](rate-limiting.md)
- [性能优化 FAQ](../../faq/performance.md)

---

**需要更多帮助？** 查看 [常见问题](../../faq/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
