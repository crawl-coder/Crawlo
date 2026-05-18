# Crawlo 生产环境优化计划

> 文档版本: v1.3（新增问题二次验证修正）  
> 创建日期: 2026-05-18  
> 审查范围: 全量代码审查（引擎/背压/调度/下载器/检查点/配置/通知系统）+ 退出/关闭生命周期深度审查  
> 审查视角: 高级爬虫架构师，关注生产环境下的逻辑正确性与容错能力  
> 验证状态: 全部 20 项问题已逐条与源码对照验证，16 项确认、2 项部分确认、1 项描述修正、1 项否认

---

## 一、概述

Crawlo 在架构设计上展现了良好的工程素养——事件驱动的引擎模型、分层背压控制系统、组件工厂依赖注入、层次化异常体系均为成熟的设计选择。本次审查聚焦于**边界条件、错误处理路径、退出生命周期和配置安全性**，这些是生产环境中最容易暴露问题的区域。

共发现 **19 个需要修复的问题**（1 项经源码验证后移除），按严重程度分为三级：

| 严重级别 | 数量 | 定义 |
|----------|------|------|
| P0 - 严重 | 5 | 确定性的崩溃/数据丢失，生产不可接受 |
| P1 - 高 | 6 | 特定场景下功能失效或资源泄漏 |
| P2 - 中 | 8 | 影响运维可观测性或存在安全隐患 |

---

## 二、P0 严重问题

### 2.1 BackpressureController 调用智能计算器参数错误且缺少 await

**文件**: `crawlo/backpressure/__init__.py:140`

**问题描述**:

```python
enhanced = self._intelligent_calc.calculate_delay(queue)  # 两个 Bug
```

- **Bug A**：`IntelligentBackpressureCalculator.calculate_delay()` 方法签名是 `async def calculate_delay(self)`，不接受任何参数。传入 `queue` 会触发 `TypeError: calculate_delay() takes 1 positional argument but 2 were given`。
- **Bug B**：方法为 `async`，调用时缺少 `await`，变量 `enhanced` 将是 coroutine 对象而非 float。下游 `max(delay, enhanced)` 触发 `TypeError: '>' not supported between instances of 'float' and 'coroutine'`。

**影响**: 任何启用智能计算器的场景均确定性崩溃。

**修复方案**:

```python
# 修复前
enhanced = self._intelligent_calc.calculate_delay(queue)

# 修复后
enhanced = await self._intelligent_calc.calculate_delay()
```

同时需要确保 `IntelligentBackpressureCalculator.calculate_delay` 能从内部获取队列信息，而非依赖外部传入。

---

### 2.2 QueueSizeStrategy / AdaptiveStrategy 阈值配置为临界值时除零

**文件**: `crawlo/backpressure/strategies.py:72, 177`

**问题描述**:

```python
norm = (utilization - self._config.threshold) / (
    CRITICAL_UTILIZATION_THRESHOLD - self._config.threshold
)
```

当用户配置 `threshold = 0.95`（即 `CRITICAL_UTILIZATION_THRESHOLD` 的值）时，分母为 0，触发 `ZeroDivisionError`。

**影响**: 当用户恰好将阈值设为临界值时，背压策略计算直接崩溃。

**修复方案**:

```python
denom = CRITICAL_UTILIZATION_THRESHOLD - self._config.threshold
if denom < 1e-9:
    norm = 1.0  # 达到临界值
else:
    norm = (utilization - self._config.threshold) / denom
```

同时在 `ConfigValidator` 中增加校验：`threshold` 必须 `< CRITICAL_UTILIZATION_THRESHOLD`。

---

### 2.3 Checkpoint 恢复后请求丢失 callback/errback（回退路径）

**文件**: `crawlo/checkpoint/manager.py:372-433`

**问题描述**:

> ⚠️ **验证修正**：经源码确认，首选恢复路径（`request_from_dict` 可用时）**已正确恢复** callback/errback（通过 `_callback`/`_errback` 键解析函数路径并重新绑定）。问题仅存在于回退路径。

`restore_request` 有两条路径：
- **首选路径**（`request_from_dict` 可用时）：调用 `request_from_dict(request_data, spider)`，该方法已实现 callback/errback 的恢复。**此路径正常。**
- **回退路径**（`request_from_dict` 不可用/ImportError 时）：手动构建 `request_kwargs`，**未包含 `callback` 和 `errback`**。此路径下恢复后的请求是**无回调的**——下载完成但不会触发解析。

同时，`_extract_pending_requests` 将请求从队列出队→序列化→放回，放回过程失败无重试机制，可能导致请求永久丢失。

**影响**:
- 回退路径（`request_from_dict` 导入失败时）恢复的请求无回调，爬虫静默失败
- 极端情况下请求永久丢失

**修复方案**:

1. 在回退路径中，从 `request_data` 提取 `_callback`/`_errback` 并手动恢复绑定
2. 为 `_extract_pending_requests` 的放回操作增加重试机制（指数退避，最多 3 次）
3. 增加验证：恢复后校验恢复请求数与序列化的请求数一致

---

### 2.4 Engine 中 shutdown 原因无法传递至 `close_spider()`

**文件**: `crawlo/core/engine.py:308-320, 580-586`, `crawlo/utils/process_utils.py:37-40`

> ⚠️ **验证修正**：原描述称"信号处理器设置 `_close_reason = 'shutdown'` 被 finally 覆盖"——经源码确认，信号处理器（`ProcessSignalHandler`）仅设置 `shutdown_event` 和 `shutdown_requested`，**从未**设置 `engine._close_reason = 'shutdown'`，也从未调用 `close_spider(reason='shutdown')`。实际问题更根本：**不存在任何代码路径能将 shutdown 原因传递给 `close_spider()`**。

**问题描述**:

```python
# 信号处理器只做这些：
def signal_handler(signum, frame):
    self.shutdown_requested = True
    self.shutdown_event.set()
    # ❌ 没有设置 engine._close_reason = 'shutdown'
    # ❌ 没有调用 engine.close_spider(reason='shutdown')

# crawl() 的 finally:
try:
    await self.close_spider()  # reason 默认为 'finished'，永远是 'finished'

# close_spider 中:
self._close_reason = reason  # 永远是 'finished'
```

完整的信号→关闭链条中断：信号处理器设置 `shutdown_event` → `CrawlerProcess.crawl()` 检测到 shutdown → `crawl_task.cancel()` → `Crawler._lifecycle_manager` 捕获 `CancelledError` → 调用 `_cleanup(reason='shutdown')`（清理资源）→ 但 **Engine.crawl()** 的 finally 块仍调用 `close_spider()` 使用默认 `reason='finished'`，shutdown 原因从未到达 Engine 层。

**影响**:
- Shutdown 场景下 checkpoint 被错误清除（`close_spider` 中仅对 `'shutdown'` 保存 checkpoint，对 `'finished'` 清除 checkpoint）
- Shutdown 时不会等待活跃任务完成（`close_spider` 中仅对非 `'finished'` 等待活跃任务）

**修复方案**:

> ⚠️ **注意**：此问题与 2.5（generation_task 死锁）位于同一个 `finally` 块中，建议合并修复。

方案一：在 finally 中根据 shutdown 事件决定 reason：

```python
# crawl() 的 finally:
# 检查是否收到过 shutdown 信号
shutdown_requested = (
    self.crawler is not None
    and hasattr(self.crawler, '_process')
    and getattr(self.crawler._process, '_shutdown_requested', False)
)
reason = 'shutdown' if shutdown_requested else 'finished'
try:
    await self.close_spider(reason=reason)
except asyncio.CancelledError:
    self.logger.debug("close_spider cancelled")
```

方案二：修改 `close_spider` 逻辑，仅在 reason 不为 None 时覆盖：

```python
async def close_spider(self, reason=None):
    if self._spider_closed:
        return
    self._spider_closed = True
    if reason is not None:
        self._close_reason = reason
    # ... 使用 self._close_reason
```

### 2.5 Engine 中 `await generation_task` 在 finally 块中永久阻塞

**文件**: `crawlo/core/engine.py:310-314`, `crawlo/core/engine_generation.py:165`

> 🆕 **退出逻辑深度审查新增发现**

**问题描述**:

```python
# engine.py finally 块:
if generation_task and not generation_task.done():
    try:
        await generation_task  # 可能永远不返回！
    except asyncio.CancelledError:
        self.logger.debug("Generation task cancelled")
```

原因链分析：

1. `generation_task` 内部循环条件是 `while self.running`（`engine_generation.py:165`）
2. `self.running` 只在 `__init__`（设 `False`）和 `engine_start()`（设 `True`）中赋值，**运行时永不设 `False`**
3. 信号处理器（`process_utils.py`）仅设置 `shutdown_event`，**不设置** `engine.running = False`
4. `crawl_task.cancel()` 只取消顶层任务，**不传递到子任务 `generation_task`**
5. `generation_task` 在 `while self.running` 中持续自旋，除非 `start_requests` 迭代器自行耗尽

**影响**:
- 单爬虫 Ctrl+C 时，`await generation_task` 永久阻塞，其后的 `close_spider()` 和 `_graceful_shutdown()` 均无法执行
- 多爬虫 Ctrl+C 时，`generation_task` 死锁；`_graceful_shutdown()` 通过外层 `KeyboardInterrupt` 捕获路径仍可执行，但 Engine 层的 finally 块卡死
- 整体表现为 Ctrl+C 后数秒（或数十秒）无响应，最终被 asyncio 超时或用户二次 Ctrl+C 强制终止

**修复方案**:

```python
# engine.py crawl() 的 finally 块:
finally:
    # 1. 先设置 running=False，让 generation_task 自行退出循环
    self.running = False
    
    # 2. 取消并等待 generation_task
    if generation_task and not generation_task.done():
        generation_task.cancel()
        try:
            await generation_task
        except asyncio.CancelledError:
            self.logger.debug("Generation task cancelled")
    
    # 3. 保留信号处理器设置的 close_reason
    try:
        await self.close_spider(
            reason=getattr(self, '_close_reason', 'finished')
        )
    except asyncio.CancelledError:
        self.logger.debug("close_spider cancelled")
```

---

## 三、P1 高风险问题

### 3.1 Redis 队列下背压控制完全不生效

**文件**: `crawlo/core/scheduler.py:421, crawlo/core/engine_helpers.py:168`

**问题描述**:

`BackpressureController.is_queue_full()` 调用 `len(scheduler)` 获取队列长度，而 Scheduler 的 `__len__` 对 Redis 队列类型永远返回 0。背压控制对 Redis queue 形同虚设。

**影响**: Redis 队列可能无限增长，导致 Redis OOM 及爬虫行为不可预测。

**修复方案**:

1. 为 Redis 队列实现 `__len__`，通过 Redis 的 `LLEN`/`ZCARD` 等命令获取真实长度
2. 或在 `BackpressureController` 中为不同队列类型注入不同的容量查询策略
3. 同时对 Redis 队列调用增加缓存 TTL，避免每次检查都访问 Redis（高频 `should_apply` 调用会造成 Redis 压力）

---

### 3.2 HybridDownloader.close() 未调用 super().close()

**文件**: `crawlo/downloader/hybrid_downloader.py:254-262`

**问题描述**:

```python
async def close(self) -> None:
    for name, downloader in self._downloaders.items():
        try:
            await downloader.close()
        except Exception as e:
            self.logger.warning(f"Error closing {name} downloader: {e}")
    self._downloaders.clear()
    # 缺少 super().close()
```

父类 `DownloaderBase.close()` 设置 `self._closed = True`。`HybridDownloader` 关闭后 `_closed` 仍为 `False`，`fetch()` 入口的 `_closed` 检查失效。

**影响**: 关闭后可继续接受请求并发送到已关闭的 session，导致异常行为。

**修复方案**:

```python
async def close(self) -> None:
    for name, downloader in self._downloaders.items():
        try:
            await downloader.close()
        except Exception as e:
            self.logger.warning(f"Error closing {name} downloader: {e}")
    self._downloaders.clear()
    await super().close()  # ← 添加这行
```

---

### 3.3 Checkpoint 写入非原子 — 已验证为误报

**文件**: `crawlo/checkpoint/storage.py:60-84`

> ❌ **验证修正**：经源码确认，存储层已实现原子写入。`JsonStorage.save()` 使用 `tempfile.mkstemp` + `os.replace` 原子替换模式；`SqliteStorage.save()` 使用显式事务保障。**此问题不存在，已从修复计划中移除。**

---

### 3.4 AdaptiveStrategy 动态阈值无下界

**文件**: `crawlo/backpressure/strategies.py:244-248`

**问题描述**:

```python
self._dynamic_threshold = min(
    self._dynamic_threshold * (1 - adaptation_rate),
    self._config.threshold
)
```

高延迟持续时，阈值以 `(1 - rate)^n` 指数衰减，无下界保护。例如 `rate=0.1`，约 70 次调整后阈值就降至原值的 0.1% 以下。

**影响**: 背压策略逐渐失效，在高负载场景下爬虫可能逐步失去流量控制。

**修复方案**:

```python
MIN_THRESHOLD = self._config.threshold * 0.3  # 不低于原始阈值的 30%
self._dynamic_threshold = max(
    MIN_THRESHOLD,
    min(
        self._dynamic_threshold * (1 - adaptation_rate),
        self._config.threshold
    )
)
```

---

### 3.5 Engine 中 `_fetch` 返回 None 时请求静默丢失

**文件**: `crawlo/core/engine.py:410-423`

**问题描述**:

```python
async def _fetch(self, request):
    if self.downloader is None:
        return None      # 无日志
    _response = await self.downloader.fetch(request)
    if _response is None:
        return None      # 无日志，无 errback
```

**影响**: 请求在无任何通知的情况下消失。生产环境中排查极度困难。

**修复方案**:

```python
async def _fetch(self, request):
    if self.downloader is None:
        self.logger.error("Downloader is not initialized")
        return Failure(request, RuntimeError("Downloader not available"))
    _response = await self.downloader.fetch(request)
    if _response is None:
        self.logger.warning(f"Downloader returned None for {request}")
        return Failure(request, RuntimeError("Empty response from downloader"))
    return _response
```

---

### 3.6 AioHttpDownloader 临时 Session 的 connector 双重关闭隐患

**文件**: `crawlo/downloader/aiohttp_downloader.py:272-279`

> ⚠️ **验证修正**：原声称 NameError 不成立——当 `TCPConnector()` 构造失败时，异常在 `try` 块之前抛出，Python 不执行 `finally` 块，因此不会触发 `NameError`。

**实际问题描述**:

`ClientSession` 会接管 connector 的所有权。当 `async with ClientSession(...)` 退出时，session 的 `__aexit__` 会关闭 connector。之后 `finally` 中的 `await connector.close()` 尝试关闭一个已关闭的 connector，可能触发 aiohttp 的警告或异常。

**影响**: 每次使用临时 session 重试时，都会产生 connector 双重关闭的警告日志。

**修复方案**:

移除 `finally` 中的手动 `connector.close()`，由 `ClientSession` 的上下文管理器负责清理：

```python
if timeout is not None:
    async with ClientSession(
        connector=TCPConnector(**temp_connector_kwargs),
        timeout=timeout
    ) as temp_session:
        async with await self._send_request(temp_session, request) as resp:
            return await self._process_response(request, resp)
    # connector 由 ClientSession 自动关闭
else:
    async with await self._send_request(self.session, request) as resp:
        return await self._process_response(request, resp)
```

---

### 3.7 `run.py` 调用不存在的 `crawl_multiple` 方法

**文件**: `crawlo/commands/run.py:277`

> 🆕 **退出逻辑深度审查新增发现**

**问题描述**:

```python
# run.py 第 277 行
run_with_cleanup(process.crawl_multiple(spider_names))
```

`CrawlerProcess` 只有 `crawl(spider_cls_or_name)` 方法（接受列表时分发到 `_crawl_multiple`），**没有** `crawl_multiple` 公共方法。

**影响**: `crawlo run --all` 路径运行时抛出 `AttributeError: 'CrawlerProcess' object has no attribute 'crawl_multiple'`。

**修复方案**:

```python
# 修复为调用正确的公共 API
run_with_cleanup(process.crawl(spider_names))
```

同时检查 `crawlo/framework.py:192` 中的相同调用 `self._process.crawl_multiple(...)`。

---

## 四、P2 中等风险问题

### 4.1 Engine 流控/取消日志标志永不重置

**文件**: `crawlo/core/engine.py:253-257, 398`

**问题描述**:

`_fc_logged` 和 `_cancel_logged` 标志设为 `True` 后永不重置。当流控恢复后再次进入流控状态时，不再打印日志。

**影响**: 生产运维中丢失关键的观测信号。

**修复方案**:

在流控/取消条件解除时重置标志：

```python
# 当流控解除时
if utilization < HIGH_UTILIZATION_THRESHOLD:
    self._fc_logged = False
```

---

### 4.2 BackpressureMonitor 可被重复启动

**文件**: `crawlo/backpressure/monitor.py:84-92`

**问题描述**:

`start()` 方法没有检查当前是否已在运行。重复调用会创建新的监控任务而旧任务成为孤儿。

**影响**: 监控任务泄漏，可能产生重复告警。

**修复方案**:

```python
async def start(self):
    if self._monitor_task is not None and not self._monitor_task.done():
        self.logger.warning("Monitor is already running")
        return
    # ... 启动逻辑
```

---

### 4.3 Engine 非关键错误无内置重试

**文件**: `crawlo/core/engine.py:380-385`

**问题描述**:

```python
if ErrorClassifier.is_critical(e):
    ...
    raise
return None  # 非关键错误：静默丢弃
```

**影响**: 网络抖动等常见场景下请求直接丢失，爬取成功率降低。

**修复方案**:

为非关键错误增加可配置的重试机制（默认 0 次，保持向后兼容）：

```python
retries = getattr(request, 'retry_count', 0)
max_retries = request.meta.get('max_retries', self.settings.getint('MAX_RETRY_TIMES', 0))
if not ErrorClassifier.is_critical(e) and retries < max_retries:
    request.retry_count = retries + 1
    self.scheduler.enqueue_request(request)
    return None
```

---

### 4.4 ConfigValidator 验证覆盖严重不足

**文件**: `crawlo/config.py:84-174`

**问题描述**:

当前仅验证约 10 个设置项（`PROJECT_NAME`、`DOWNLOAD_TIMEOUT`、`DOWNLOAD_DELAY`、`MAX_RETRY_TIMES`、`CONNECTION_POOL_LIMIT`、`CONCURRENCY`、`MAX_RUNNING_SPIDERS`、`QUEUE_TYPE`、`SCHEDULER_MAX_QUEUE_SIZE`、`REDIS_HOST`/`REDIS_PORT`），而项目有 80+ 个配置项，覆盖率约 12%。缺失关联性验证。

**影响**: 不合理的配置组合被静默接受，在运行时以难以排查的方式暴露。

**修复方案**:

增加以下验证规则：

| 验证项 | 规则 |
|--------|------|
| `VERIFY_SSL` | 必须为 bool 类型 |
| `DOWNLOAD_MAXSIZE` | 必须 > 0 |
| `CONNECTION_POOL_LIMIT_PER_HOST` | 必须 ≤ `CONNECTION_POOL_LIMIT` |
| `CONCURRENCY` | 必须 ≤ `CONNECTION_POOL_LIMIT` |
| `HYBRID_DEFAULT_*_DOWNLOADER` | 下载器类必须存在 |
| `DOWNLOADER` / `MIDDLEWARES` / `PIPELINES` | 类路径存在性校验 |
| `RETRY_HTTP_CODES` | 列表元素均为合法 HTTP 状态码 |
| Backpressure 阈值 | `WARNING_THRESHOLD < CRITICAL_THRESHOLD` |
| `REDIS_DB` | 必须在 0-15 范围内 |
| `SCHEDULER_JOBS` | cron 表达式格式校验 + 爬虫名称存在性校验 |

---

### 4.5 BackpressureController `_apply_count` 语义不准确

**文件**: `crawlo/backpressure/__init__.py:119`

**问题描述**:

`should_apply` 每次返回 `True` 都累加计数，而非仅在"新触发"时累加。`get_stats` 中的 `avg_delay` 因此被稀释。

**影响**: 统计指标失真，不利于调优决策。

**修复方案**:

改为仅在新触发时累加：

```python
def should_apply(self, queue) -> bool:
    result = self._strategy.should_apply(queue)
    if result and not self._active:
        self._apply_count += 1
        self._active = True
    elif not result:
        self._active = False
    return result
```

---

### 4.6 `graceful_shutdown` 中任务取消缺少 Crawler 状态检查

**文件**: `crawlo/utils/process_utils.py:84-99`

> 🆕 **退出逻辑深度审查新增发现**

> ⚠️ **验证修正**：原描述称"对已完成任务重复调用 cancel"——经源码确认，代码已有 `if not task.done()` 检查（第 96 行），不会对已完成任务调用 cancel。实际问题为缺少 Crawler 级别的状态检查。

**问题描述**:

```python
async def graceful_shutdown(self):
    # 取消所有正在运行的任务
    for crawler in self.crawlers:
        engine = getattr(crawler, '_engine', None)
        task_manager = getattr(engine, 'task_manager', None) if engine else None
        if task_manager:
            for task in list(getattr(task_manager, 'current_task', [])):
                if not task.done():   # ← 已有任务级完成检查
                    task.cancel()     # 但缺少 Crawler 级别的状态检查
```

与后续的 `_cleanup` 调用不同（第 105-112 行有 Crawler 状态检查，仅对非 CLOSING/CLOSED 实例执行），这部分任务取消**没有 Crawler 级别的状态检查**。在关闭序列中，`_lifecycle_manager` 可能已经完成了 `_cleanup(reason='shutdown')` 且 Crawler 已进入 CLOSED 状态，但 `graceful_shutdown` 仍会尝试访问其 `task_manager` 并取消任务——虽然 `task.done()` 检查避免了实际 cancel 调用，但在 Crawler 已关闭后仍访问其内部状态是不安全的。

**影响**: 对已关闭的 Crawler 访问内部 task_manager，可能遇到已释放的资源。实际概率低（关闭后 current_task 大概率为空列表），但违反关闭顺序约束。

**修复方案**:

增加 Crawler 状态检查，与后续 `_cleanup` 的逻辑一致：

```python
async def graceful_shutdown(self):
    for crawler in self.crawlers:
        # 状态检查：跳过已关闭或正在关闭的 Crawler
        current_state = getattr(crawler, '_state', 'unknown')
        closing_states = ['CLOSING', 'closing', 'CLOSED', 'closed']
        if hasattr(current_state, 'value'):
            current_state = current_state.value
        if str(current_state) in closing_states:
            continue

        try:
            engine = getattr(crawler, '_engine', None)
            task_manager = getattr(engine, 'task_manager', None) if engine else None
            if task_manager:
                for task in list(getattr(task_manager, 'current_task', [])):
                    if not task.done():
                        task.cancel()
        except Exception as e:
            self.logger.warning(f"取消爬虫任务时出错: {e}")
```

---

### 4.7 `_spider_closed` 标志在 CancelledError 半关闭时无法复原

**文件**: `crawlo/core/engine.py:319-320, 582, 654-656`

> 🆕 **退出逻辑深度审查新增发现**

**问题描述**:

```python
async def close_spider(self, reason='finished'):
    if self._spider_closed:
        return
    self._spider_closed = True
    # ... 清理逻辑 ...
    except Exception:
        self._spider_closed = False  # 仅在 Exception 时重置
        raise
```

如果 `CancelledError` 在 `close_spider()` 中途抛出（Python 3.9+ 中 `CancelledError` 不是 `Exception` 子类），`_spider_closed` 保持 `True` 不被重置，但清理只完成了一部分。随后 `engine.py:319` 吞掉这个 `CancelledError`，阻塞了重试路径。

**影响**: 实际发生概率极低（`close_spider` 只被调用一次），但一旦触发会导致清理不完整。

**修复方案**:

```python
except BaseException:
    self._spider_closed = False
    raise
```

---

### 4.8 Python 3.8 兼容性：CancelledError 被错误包装

**文件**: `crawlo/crawler.py:380`

> 🆕 **退出逻辑深度审查新增发现**

**问题描述**:

```python
except Exception as e:
    raise RuntimeError(f"Spider {self._spider_cls.name} failed: {e}") from e
```

在 Python 3.8 中，`asyncio.CancelledError` 是 `Exception` 的子类，会被此捕获器拦截并包装为 `RuntimeError`，破坏取消传播链。Python 3.9+ 中 `CancelledError` 归入 `BaseException`，不受影响。

**影响**: 仅影响 Python 3.8 用户。

**修复方案**:

在 `except Exception` 前增加 `except asyncio.CancelledError: raise` 守卫。

---

## 五、默认配置优化

| 配置项 | 当前值 | 风险 | 建议值 | 原因 |
|--------|--------|------|--------|------|
| `PLAYWRIGHT_IGNORE_HTTPS_ERRORS` | `True` | 默认忽略所有 HTTPS 证书错误，中间人攻击风险 | `False` | 生产安全基线 |
| `MYSQL_PASSWORD` | `'123456'` | 公开弱密码 | `''`（空字符串，强制用户设置） | 安全最佳实践 |
| `ALLOWED_DOMAINS` | `[]` | 无域名限制，爬虫可能爬取外部域名 | 保持不变，增加文档警告 | 保持灵活性 |
| `HYBRID_DEFAULT_DYNAMIC_DOWNLOADER` | `"cloakbrowser"` | 需特殊安装 Chromium，开箱不可用 | `"drissionpage"` | 降低使用门槛 |
| `DOWNLOAD_TIMEOUT` | `15`（settings）vs `30`（config.BASE_CONFIG） | 两处不一致 | 统一为 `15` | 一致性 |
| `CONNECTION_POOL_LIMIT` | `100`（settings）vs `50`（config.BASE_CONFIG） | 两处不一致 | 统一为 `100` | 一致性 |
| `SCHEDULER_JOBS` | 含占位示例 `'spider_name'` | 开箱启用即报错 | 移除示例或默认 `SCHEDULER_ENABLED=False` | 防止误用 |
| `REDIS_TTL` | `0` | 去重指纹永不过期 | 保持不变，增加文档说明 | Redis 有自身过期策略 |

---

## 六、实施计划

### 第一阶段（1-2 天）：修复 P0 问题

| 序号 | 内容 | 文件 | 风险等级 |
|------|------|------|----------|
| 1.1 | 修复 BackpressureController 智能计算器调用 | `backpressure/__init__.py` | 低 |
| 1.2 | 修复 QueueSizeStrategy/AdaptiveStrategy 除零 | `backpressure/strategies.py` | 低 |
| 1.3 | 修复 Checkpoint 恢复后丢失 callback/errback（回退路径） | `checkpoint/manager.py` | 中 |
| 1.4 | 修复 Engine shutdown 原因无法传递 | `core/engine.py` | 中 |
| 1.5 | 修复 `await generation_task` 死锁 + `self.running` 不设 False | `core/engine.py` | 中 |

### 第二阶段（2-3 天）：修复 P1 问题

| 序号 | 内容 | 文件 | 风险等级 |
|------|------|------|----------|
| 2.1 | 修复 Redis 队列背压失效 | `core/scheduler.py`, `core/engine_helpers.py` | 中 |
| 2.2 | 修复 HybridDownloader.close() | `downloader/hybrid_downloader.py` | 低 |
| 2.3 | 修复 AdaptiveStrategy 阈值下界 | `backpressure/strategies.py` | 低 |
| 2.4 | 修复 `_fetch` 返回 None 的日志 | `core/engine.py` | 低 |
| 2.5 | 修复临时 session connector 双重关闭 | `downloader/aiohttp_downloader.py` | 低 |
| 2.6 | 修复 `run.py` 调用不存在的 `crawl_multiple` | `commands/run.py`, `framework.py` | 低 |

### 第三阶段（1-2 天）：修复 P2 问题 + 配置优化

| 序号 | 内容 | 文件 |
|------|------|------|
| 3.1 | 流控/取消日志标志重置 | `core/engine.py` |
| 3.2 | Monitor 重复启动检查 | `backpressure/monitor.py` |
| 3.3 | 非关键错误重试机制 | `core/engine.py` |
| 3.4 | ConfigValidator 扩展 | `config.py` |
| 3.5 | `_apply_count` 语义修正 | `backpressure/__init__.py` |
| 3.6 | 默认配置优化 | `settings/default_settings.py` |
| 3.7 | `graceful_shutdown` 增加 Crawler 状态检查 | `utils/process_utils.py` |
| 3.8 | `_spider_closed` 在 BaseException 时重置 | `core/engine.py` |
| 3.9 | Python 3.8 CancelledError 兼容性守卫 | `crawler.py` |

---

## 七、测试建议

每个修复项建议附带以下测试：

1. **P0 修复**: 至少一个验证修复行为的单元测试
2. **P1 修复**: 单元测试 + 集成测试（如 Redis 背压需启动 Redis 进行验证）
3. **P2 修复**: 单元测试

建议为 `CheckpointManager` 和 `BackpressureController` 增加专门的集成测试套件，覆盖：
- checkpoint 保存/恢复往返
- 不同队列类型（内存/Redis）下的背压行为
- 异常场景（连接断开、OOM 模拟）

---

## 八、审查总结

Crawlo 的架构设计展现了成熟的工程思考——事件驱动的引擎、分层背压控制、组件工厂依赖注入等均为行业最佳实践。当前的问题主要集中在**边界条件和错误处理路径**上，这些正是生产环境与开发环境差异最大的区域。建议优先修复 P0 四个问题，其余问题可分两个迭代完成，预计总工期约 **4-7 天**。

---

## 附录：源码验证结果

全部 20 项问题已逐条与源码对照验证（含二次验证），结果如下：

| 编号 | 问题 | 验证结论 | 说明 |
|------|------|----------|------|
| P0-2.1 | 智能计算器调用崩溃 | ✅ 确认 | 参数不匹配 + 缺少 await，确定性 TypeError |
| P0-2.2 | 背压策略除零 | ✅ 确认 | threshold=0.95 时分母为 0 |
| P0-2.3 | Checkpoint 恢复丢失 callback | ⚠️ 部分确认 | 主路径正常，仅 ImportError 回退路径丢失 |
| P0-2.4 | shutdown 原因无法传递 | ⚠️ 修正 | 信号处理器未设置 `_close_reason='shutdown'`；实际是无任何代码路径传递 shutdown 原因 |
| P1-3.1 | Redis 队列背压失效 | ✅ 确认 | `__len__` 对 Redis 返回 0，is_queue_full 永远为 False |
| P1-3.2 | HybridDownloader.close() 缺少 super() | ✅ 确认 | _closed 标志不会被设置 |
| P1-3.3 | Checkpoint 非原子写入 | ❌ 否认 | storage.py 已实现 tempfile+os.replace 原子写入 |
| P1-3.4 | AdaptiveStrategy 阈值无下界 | ✅ 确认 | 下降路径仅有上限约束，阈值可趋近 0 |
| P1-3.5 | _fetch 返回 None 无日志 | ✅ 确认 | 两处静默 return None |
| P1-3.6 | 临时 session NameError | ⚠️ 修正 | NameError 不成立，实际问题为 connector 双重关闭 |
| P2-4.1 | 日志标志永不重置 | ✅ 确认 | _fc_logged / _cancel_logged 永不重置为 False |
| P2-4.2 | Monitor 重复启动 | ✅ 确认 | start() 无运行中检查 |
| P2-4.3 | 非关键错误无重试 | ✅ 确认 | 引擎层直接 return None 丢弃 |
| P2-4.4 | ConfigValidator 不足 | ✅ 确认 | 仅验证 10/80+ 项，约 12% 覆盖率 |
| P2-4.5 | _apply_count 语义 | ✅ 确认 | 每次 should_apply=True 均递增，非状态转换时 |
| P0-2.5 | generation_task 死锁 | ✅ 确认 | self.running 永不设 False，generation_task 永不退出 |
| P1-3.7 | run.py crawl_multiple 不存在 | ✅ 确认 | CrawlerProcess 无 crawl_multiple 方法 |
| P2-4.6 | graceful_shutdown 缺少 Crawler 状态检查 | ⚠️ 修正 | 原称"对已完成任务重复 cancel"不成立（已有 `task.done()` 检查）；实际为缺少 Crawler 级状态检查 |
| P2-4.7 | _spider_closed + CancelledError 半关闭 | ✅ 确认 | CancelledError 不是 Exception 子类，标志不重置 |
| P2-4.8 | Python 3.8 CancelledError 包装 | ✅ 确认 | 被 except Exception 捕获包装为 RuntimeError |
| 配置项 | 全部 5 项 | ✅ 确认 | 均与源码一致 |
