# 被封号？被限速？Crawlo 背压控制帮你自动调节

> 并发开高了怕被封，开低了嫌太慢——框架自动帮你找到平衡点。

---

## 永恒的调参困境

每个爬虫工程师都经历过这个循环：

```
并发调高 → 被封号 → 降并发 → 速度太慢 → 再调高 → 又被封 → ...
```

手动调参的问题在于：每个网站的最优并发不同；同一网站不同时段的最优并发也不同。

**Crawlo 的背压系统，就是为了终结这个循环。**

---

## 背压控制是什么？

**背压（Backpressure）** 是一个来自流式计算的概念：当下游处理速度跟不上上游生产速度时，反向传导压力，让上游自动减速。

在爬虫场景下：

- **上游**：产生请求（start_requests、翻页、详情链接）
- **下游**：下载 + 解析（受网络带宽、目标站点响应速度限制）

当下游"消化不良"时，Crawlo 的 Engine 自动暂停请求生成，等待队列消化。

---

## Engine 内置背压

Engine 内置背压控制器，实时监控队列容量和任务并发数：

- 队列接近满时 → 暂停新请求生成
- 在途任务过多时 → 暂停派发新任务
- 队列有空位 + 并发富余时 → 恢复请求生成

**核心参数**：

```python
# settings.py
CONCURRENCY = 32                         # 并发下载数
REQUEST_GENERATION_BATCH_SIZE = 10       # 每批生成的请求数
ENABLE_CONTROLLED_REQUEST_GENERATION = False  # 启用受控请求生成
```

**内存队列背压**：

```python
MEMORY_BACKPRESSURE_RATIO = 0.5          # 触发阈值
MEMORY_BACKPRESSURE_DELAY_BASE = 0.5     # 基础延迟（秒）
MEMORY_BACKPRESSURE_DELAY_MAX = 5.0      # 最大延迟（秒）
```

**Redis 队列背压（分布式模式）**：

```python
REDIS_BACKPRESSURE_RATIO = 0.6           # 触发阈值
REDIS_BACKPRESSURE_DELAY_BASE = 0.5      # 基础延迟（秒）
REDIS_BACKPRESSURE_DELAY_MAX = 5.0       # 最大延迟（秒）
```

---

## 背压策略模块

Crawlo 内置可扩展的背压策略模块（`crawlo.backpressure`），提供多种策略实现：

- **队列大小策略**（QueueSizeStrategy）：根据队列利用率动态调整延迟
- **自适应策略**（AdaptiveStrategy）：根据历史延迟自动调整阈值，有下界保护
- **智能计算器**（IntelligentBackpressureCalculator）：结合多维指标综合计算

```python
# settings.py
BACKPRESSURE_STRATEGY = 'queue_size'        # 背压策略
ADAPTIVE_BACKPRESSURE_ENABLED = False        # 启用自适应背压（实验性）
```

---

## 架构原理

```
                 ┌─────────────────┐
                 │   Engine 主循环   │ ← 检查队列容量 + 任务并发数
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │ BackpressureController│ ← should_pause()/wait_for_capacity()
                 │ (engine_helpers) │
                 │                  │
                 │ max_queue_size   │ ← 队列容量上限
                 │ backpressure_ratio│ ← 触发比例
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ 请求生成任务      │ ← 暂停/恢复请求生成
                 └─────────────────┘
```

**关键设计**：
- 背压内置于 Engine 主循环，不是事后补丁
- 队列容量 + 任务并发数双重监控
- 指数退避等待（initial_wait → max_wait）
- 策略模块与 Engine 解耦，可独立测试和替换

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
