# Crawlo 爬虫框架设计缺陷分析报告

> 基于全量代码审查，从0梳理框架设计缺陷。审查范围覆盖22个核心模块，识别出 CRITICAL 级缺陷 3 个、HIGH 级缺陷 4 个、MEDIUM 级缺陷 7 个、LOW 级缺陷 2 个。

---

## 缺陷总览

| 等级 | 数量 | 概要 |
|------|------|------|
| CRITICAL | 3 | 异步环境混用线程锁、全局状态污染、重复清理 |
| HIGH | 4 | 事件异常静默、非原子状态检查、信号量非线程安全、协程结果丢失 |
| MEDIUM | 7 | 信号处理时机、注册表同步/异步混用、配置语义丢失、信号量竞争、Redis 队列误判、无界内存增长、去重逻辑反转 |
| LOW | 2 | dataclass ID 不可靠、根 logger handlers 误关 |

---

## CRITICAL 级缺陷

### CRITICAL-1: CoreInitializer 单例 + threading.RLock 在异步环境中导致死锁风险

**位置**:
- `crawlo/initialization/core.py` L20 (`@singleton`), L35 (`_init_lock = threading.RLock()`)
- `crawlo/utils/singleton.py` L50-70 (`@singleton` 装饰器使用 `threading.Lock`)

**问题分析**:

1. `@singleton` 装饰器将 `CoreInitializer` 类替换为函数，内部使用 `threading.Lock` 保证单例创建。`CoreInitializer.initialize()` 内部又使用 `threading.RLock` 保护初始化过程。
2. `_execute_phase_with_timeout` (L172-198) 在新线程中执行初始化阶段，线程通过 `threading.Thread` 启动并 `join(timeout)`。当主线程持有 `_init_lock` 时，如果事件循环中有其他协程也需要初始化框架，将阻塞整个事件循环。
3. `@singleton` 装饰器把类变成函数，破坏了 `isinstance` 检查、类型提示和 IDE 自动补全。

**影响范围**:
- 在异步环境中多次调用 `initialize_framework()` 可能死锁
- 所有依赖 `CoreInitializer` 类型检查的代码失效
- 测试中无法正常 `isinstance(obj, CoreInitializer)`

**修复建议**:

```python
# 方案1: 使用 asyncio.Lock 替代 threading.RLock
class CoreInitializer:
    _instance = None
    _init_lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

# 方案2: 保留同步入口但使用双重检查
class CoreInitializer:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

---

### CRITICAL-2: 全局可变状态导致多实例不隔离

**位置**:
- `crawlo/spider/__init__.py` L42: `_DEFAULT_SPIDER_REGISTRY: Dict[str, Type['Spider']] = {}`
- `crawlo/framework.py` L254: `_global_framework: Optional[CrawloFramework] = None`
- `crawlo/application.py` L101: `_global_context: Optional[ApplicationContext] = None`
- `crawlo/factories/registry.py` L124: `_global_registry = ComponentRegistry()`
- `crawlo/utils/resource_manager.py` L449: `_global_managers: Dict[str, ResourceManager] = {}`

**问题分析**:

框架存在至少 5 个全局可变状态。在同一进程中运行多个独立的爬虫实例时，这些全局状态会互相污染：

1. **爬虫注册表**: 所有爬虫类共享同一个字典，`SpiderMeta` 元类自动注册时无法区分不同应用
2. **框架实例**: `get_framework()` 单例模式无法为不同配置创建独立实例
3. **组件注册表**: 所有 Crawler 共享同一个 `ComponentRegistry`，一个实例的修改影响其他实例
4. **资源管理器**: 全局 `_global_managers` 可能导致跨实例资源泄漏

**影响范围**:
- 同一进程运行多个独立爬虫应用时状态混乱
- 测试隔离困难，一个测试的注册/修改影响其他测试
- 无法支持"一个进程多个独立项目"的场景

**修复建议**:

```python
# 方案: 引入 Context 对象，将全局状态绑定到上下文

class CrawloContext:
    """框架上下文 - 持有所有实例级状态"""
    
    def __init__(self):
        self.spider_registry: Dict[str, Type[Spider]] = {}
        self.component_registry = ComponentRegistry()
        self.resource_managers: Dict[str, ResourceManager] = {}
        self.framework: Optional[CrawloFramework] = None

# 使用 contextvars 实现协程级隔离
import contextvars

_current_context: contextvars.ContextVar['CrawloContext'] = contextvars.ContextVar('crawlo_context')

def get_context() -> CrawloContext:
    ctx = _current_context.get(None)
    if ctx is None:
        ctx = CrawloContext()
        _current_context.set(ctx)
    return ctx
```

---

### CRITICAL-3: Crawler._cleanup 重复清理 Engine 导致资源释放异常

**位置**: `crawlo/crawler.py` L415-496

**问题分析**:

`_cleanup()` 方法的清理顺序如下:

```
1. L428: await self._resource_manager.cleanup_all()   # 清理所有注册资源（含 Engine）
2. L435: await self._cleanup_engine(reason)            # 再次清理 Engine
3. L438: await self._cleanup_stats(reason)             # 再次清理 Stats
```

在 `_initialize_components()` (L320-329) 中，Engine 被注册到 `_resource_manager`:

```python
self._resource_manager.register(
    self._engine,
    lambda e: e.close() if hasattr(e, 'close') else None,
    ResourceType.OTHER,
    name="engine"
)
```

因此 `cleanup_all()` 已经调用了 `engine.close()`，之后 `_cleanup_engine()` 又调用 `engine.close()` 和 `engine.close_spider()`。对已关闭的资源执行二次操作:

1. `Engine.close()` (L531-556) 内部 `await asyncio.gather(*self.task_manager.current_task)` — 二次执行时 `current_task` 已空，但 `self.scheduler.close()` 会被再次调用
2. `Engine.close_spider()` 内部 `await self.processor.pipelines.close()` — 已关闭的 pipeline 可能抛异常
3. Stats 也存在同样的双重清理问题

**影响范围**:
- 爬虫关闭时可能产生不可预测的异常
- 资源可能被重复释放（如 Redis 连接池关闭两次）
- 日志中出现大量 warning 级别的 "cleanup failed" 信息

**修复建议**:

```python
async def _cleanup(self, reason: str = 'finished') -> None:
    async with self._state_lock:
        if self._state not in [CrawlerState.CLOSING, CrawlerState.CLOSED]:
            self._state = CrawlerState.CLOSING
    
    try:
        # 方案: 移除 _cleanup_engine 和 _cleanup_stats 的直接调用
        # 统一由 ResourceManager 管理清理顺序
        
        # 1. 先触发 spider_closed 事件（在资源清理之前）
        if self.subscriber:
            from crawlo.event import CrawlerEvent
            await self.subscriber.notify(CrawlerEvent.SPIDER_CLOSED, reason=reason)
        
        # 2. 统一由 ResourceManager 清理所有资源
        # 需要确保 Engine 的注册包含 close_spider 逻辑:
        #   self._resource_manager.register(
        #       self._engine,
        #       lambda e: (await e.close_spider(), await e.close()),
        #       ResourceType.OTHER,
        #       name="engine"
        #   )
        cleanup_result = await self._resource_manager.cleanup_all()
        
        async with self._state_lock:
            self._state = CrawlerState.CLOSED
    except Exception as e:
        self._logger.error(f"Cleanup error: {e}")
```

---

## HIGH 级缺陷

### HIGH-1: Subscriber.notify 事件异常被静默吞噬

**位置**: `crawlo/subscriber.py` L120-204

**问题分析**:

默认 `error_handling="log"` 模式下:

```python
# L183-188
if isinstance(result, Exception):
    if first_error is None:
        first_error = result
    logger.error(f"任务 {receiver.__name__} 异常：{result}")
else:
    logger.debug(f"任务 {receiver.__name__} 完成")
results.append(result)
```

- 订阅者异常只记录日志，不向上传播
- `notify()` 返回结果列表，但调用方普遍不检查返回值
- 关键事件（如 `SPIDER_CLOSED`）处理失败时，扩展可能未正确清理资源
- 调用方无法区分"无订阅者"和"订阅者全部失败"

**影响范围**:
- 扩展初始化/清理失败时静默忽略，资源泄漏
- 数据处理管道错误无法传播到上层
- 调试困难，错误只在日志中体现

**修复建议**:

```python
async def notify(self, event: str, *args, **kwargs) -> NotifyResult:
    """增强返回值，包含执行状态"""
    results = []
    errors = []
    
    for receiver, priority in sorted_subscribers:
        try:
            result = await asyncio.wait_for(receiver(*args, **kwargs), timeout=self._timeout)
            results.append(result)
        except Exception as e:
            errors.append((receiver, e))
            self._logger.error(f"Subscriber {receiver.__name__} failed: {e}")
    
    # 关键事件失败时至少输出 WARNING
    if errors and event in (CrawlerEvent.SPIDER_CLOSED, CrawlerEvent.SPIDER_ERROR):
        self._logger.warning(
            f"Critical event {event} had {len(errors)} failed subscribers"
        )
    
    return NotifyResult(results=results, errors=errors, event=event)
```

---

### HIGH-2: Processor 非原子状态检查导致竞态条件

**位置**: `crawlo/core/processor.py` L285-292

**问题分析**:

```python
def idle(self) -> bool:
    return len(self) == 0 and len(self._processing) == 0
```

`len(self)` 检查 `self.queue.qsize()`，`len(self._processing)` 检查正在处理的项数。两个检查之间没有原子保证：

1. 时刻 T1: `queue.qsize() == 0` (True)
2. 时刻 T2: 另一个协程向 queue 放入新数据
3. 时刻 T3: `len(self._processing) == 0` (True)
4. 结果: `idle()` 返回 True，但实际上 queue 中有数据

Engine 的 `_should_exit()` (L455-526) 依赖 `processor.idle()` 判断退出，可能误判退出导致数据丢失。

**影响范围**:
- 爬虫可能过早退出，丢失尚未处理的数据
- 分布式场景下更为严重，因为数据可能还在传输中

**修复建议**:

```python
def idle(self) -> bool:
    """使用单一原子检查判断空闲状态"""
    # 使用 _lock 保护整个检查过程
    # 但 idle() 是同步方法，不能使用 async with
    # 方案: 使用 _processing 和 queue 的组合原子标志
    return (self.queue.empty() and 
            len(self._processing) == 0 and
            self._state != ProcessorState.RUNNING)

# 或者 Engine 中统一使用 idle_async()
async def idle_async(self) -> bool:
    async with self._lock:
        return self.queue.empty() and len(self._processing) == 0
```

---

### HIGH-3: DynamicSemaphore.release() 与 _adjust_semaphore_value() 锁使用不一致

**位置**: `crawlo/task_manager.py` L107-118, L158-172

**问题分析**:

```python
# release() - 无锁
def release(self) -> None:
    self._active_count = max(0, self._active_count - 1)
    try:
        while not self._waiters.empty() and self._active_count < self._target_value:
            event = self._waiters.get_nowait()
            self._active_count += 1
            event.set()
    except asyncio.QueueEmpty:
        pass

# _adjust_semaphore_value() - 有锁
async def _adjust_semaphore_value(self, new_value: int) -> None:
    old_value = self._current_value
    self._current_value = new_value
    self._target_value = new_value
    if new_value > old_value:
        try:
            while not self._waiters.empty() and self._active_count < self._target_value:
                event = self._waiters.get_nowait()
                self._active_count += 1
                event.set()
        except asyncio.QueueEmpty:
            pass
```

两个方法都操作 `_active_count`、`_waiters`、`_target_value`，但一个有锁一个无锁。虽然在单线程 asyncio 事件循环中通常安全，但:

1. `release()` 在 `done_callback` 中调用，如果 `adjust_concurrency()` 同时被触发，状态可能不一致
2. `_waiters.empty()` 和 `_waiters.get_nowait()` 之间可能有其他协程插入
3. `acquire()` 的锁外等待逻辑 (`await event.wait()`) 可能在 `_adjust_semaphore_value` 修改 `_target_value` 后仍等待旧值

**影响范围**:
- 高并发场景下可能丢失唤醒信号
- 并发数调整可能不生效

**修复建议**:

```python
def release(self) -> None:
    """释放信号量 - 确保与 acquire 的锁一致性"""
    self._active_count = max(0, self._active_count - 1)
    # 唤醒逻辑移到事件循环安全的调度中
    self._wake_waiters()

def _wake_waiters(self) -> None:
    """安全唤醒等待者"""
    try:
        while not self._waiters.empty() and self._active_count < self._target_value:
            event = self._waiters.get_nowait()
            self._active_count += 1
            event.set()
    except asyncio.QueueEmpty:
        pass
```

---

### HIGH-4: Engine._fetch 协程结果未正确 await 导致数据丢失

**位置**: `crawlo/core/engine.py` L399-416

**问题分析**:

```python
async def _fetch(self, request):
    async def _successful(_response):
        if self.spider is None:
            return None
        callback: Callable = request.callback or self.spider.parse
        if _outputs := callback(_response):
            if iscoroutine(_outputs):
                await _outputs          # 问题: await 协程只返回 None
            else:
                return transform(_outputs, _response)  # 只有生成器走这里

    # ...
    output = await _successful(_response)
    return output
```

当 `callback` 返回协程对象时（如 `async def parse` 返回普通值而非生成器），`await _outputs` 返回 None，数据被丢弃。只有当 callback 返回同步/异步生成器时，`transform()` 才会被调用。

实际上 `iscoroutine(_outputs)` 为 True 的场景:
- 用户写了一个 `async def parse` 但没有用 `yield`（返回普通值而非生成器）
- 此时 `await _outputs` 的结果被丢弃

而 `_handle_spider_output` (L432-445) 期望接收 `AsyncGenerator`，如果传入 None 会被直接跳过。

**影响范围**:
- 使用异步回调函数但忘记使用 `yield` 的用户，数据会静默丢失
- 没有任何错误提示，极难调试

**修复建议**:

```python
async def _successful(_response):
    if self.spider is None:
        return None
    callback: Callable = request.callback or self.spider.parse
    _outputs = callback(_response)
    
    if _outputs is None:
        return None
    
    if isasyncgen(_outputs):
        # 异步生成器 - 正确处理
        return transform(_outputs, _response)
    elif isgenerator(_outputs):
        # 同步生成器 - 正确处理
        return transform(_outputs, _response)
    elif iscoroutine(_outputs):
        # 协程 - await 获取结果后再判断
        result = await _outputs
        if result is not None:
            # 单个返回值包装为生成器
            if isinstance(result, (Request, Item)):
                async def single_output():
                    yield result
                return transform(single_output(), _response)
        return None
    else:
        # 其他类型（同步返回值）
        if isinstance(_outputs, (Request, Item)):
            async def single_output():
                yield _outputs
            return transform(single_output(), _response)
        return None
```

---

## MEDIUM 级缺陷

### MEDIUM-1: CrawlerProcess 信号处理初始化时机问题

**位置**: `crawlo/crawler.py` L572-585

**问题分析**:

```python
def _setup_signal_handlers(self):
    self._signal_handler.set_crawlers(self._crawlers)
    try:
        loop = asyncio.get_running_loop()
        self._signal_handler.setup_signal_handlers()
    except RuntimeError:
        # 事件循环尚未启动，将在 crawl() 方法中设置
        self._logger.debug("Event loop not running, signal handlers will be set up later")
```

`CrawlerProcess.__init__` 调用 `_setup_signal_handlers()`，但通常在事件循环启动前创建。信号处理器延迟到 `crawl()` 方法中设置，这意味着从创建到运行之间存在一个无信号保护的窗口期。

**修复建议**:

在 `crawl()` 方法开头确保信号处理器已设置，并添加文档说明初始化时机。

---

### MEDIUM-2: ComponentRegistry 同步/异步方法混用

**位置**: `crawlo/factories/registry.py` L29-129

**问题分析**:

`ComponentRegistry` 同时提供同步方法 (`register`, `create`, `get_spec`) 和异步方法 (`register_async`, `get_spec_async`)。但:

1. `create()` 是同步方法，被 `Crawler._initialize_components()` 调用
2. `AsyncRLock` 在 `ComponentRegistry` 中初始化，但同步方法不使用它
3. 如果 `register_async` 和 `register` 并发调用，可能导致注册表状态不一致
4. 同步方法标记了 `:deprecated` 但仍然是主入口

**修复建议**:

统一为一种模式。由于 `create()` 在异步上下文中被调用，建议全部迁移为异步方法，同步方法改为调用异步方法的包装。

---

### MEDIUM-3: SettingManager.get() 返回 None 时与 default 混淆

**位置**: `crawlo/settings/setting_manager.py` L241-253

**问题分析**:

```python
def get(self, key: str, default: Any = None) -> Any:
    value = self.attributes.get(key, default)
    return value if value is not None else default
```

如果用户显式设置了 `None` 值 (`settings.set('KEY', None)`)，`get('KEY', 'fallback')` 会返回 `'fallback'` 而非 `None`。这导致:

1. 无法区分"未设置"和"设置为 None"
2. 对于布尔配置，`None`（未设置）与 `False`（显式禁用）语义不同但被混淆
3. 某些配置项可能需要 `None` 表示"自动检测"

**修复建议**:

```python
_SENTINEL = object()  # 哨兵值

def get(self, key: str, default: Any = _SENTINEL) -> Any:
    if key in self.attributes:
        return self.attributes[key]
    if default is not _SENTINEL:
        return default
    return None
```

---

### MEDIUM-4: CrawlerProcess._crawl_single 信号量与 shutdown_event 竞争

**位置**: `crawlo/crawler.py` L697-765

**问题分析**:

```python
async with self._semaphore:  # 获取信号量
    crawl_task = asyncio.create_task(crawler.crawl())
    done, pending = await asyncio.wait(
        [crawl_task, asyncio.create_task(self._shutdown_event.wait())],
        return_when=asyncio.FIRST_COMPLETED
    )
```

在信号量内等待 `shutdown_event`，如果 shutdown 被触发:
- 信号量被持有，其他爬虫无法启动
- 但 shutdown 可能需要等待其他爬虫完成才能执行清理
- 多爬虫场景下可能形成等待链

**修复建议**:

将 `shutdown_event.wait()` 移到信号量外部，使用 `asyncio.shield` 保护爬虫任务。

---

### MEDIUM-5: QueueManager.empty() 对 Redis 队列始终返回 True

**位置**: `crawlo/queue/queue_manager.py` L611-626

**问题分析**:

```python
def empty(self) -> bool:
    try:
        if self._queue and self._queue_type == QueueType.MEMORY:
            if hasattr(self._queue, 'qsize'):
                return self._queue.qsize() == 0
        # Redis 队列: 返回 True（"确保程序能正常退出"）
        return True
    except Exception:
        return True
```

对 Redis 队列始终返回 `True`，这意味着 `Scheduler.idle()` 对 Redis 队列也返回 `True`。Engine 的退出判断路径复杂:

- `_exit()` (L447-453) 使用 `scheduler.idle()`（同步） — 可能误判
- `_should_exit()` (L455-526) 使用 `scheduler.async_idle()` — 正确但路径复杂
- 主循环中两个方法都被调用，同步版本可能触发过早退出

**修复建议**:

```python
def empty(self) -> bool:
    """同步空检查 - 对不确定的队列返回 False（保守策略）"""
    try:
        if self._queue and self._queue_type == QueueType.MEMORY:
            if hasattr(self._queue, 'qsize'):
                return self._queue.qsize() == 0
        # Redis 队列: 无法同步确定，返回 False（保守）
        return False
    except Exception:
        return False
```

---

### MEDIUM-6: IntelligentScheduler 无界内存增长

**位置**: `crawlo/queue/queue_manager.py` L38-174

**问题分析**:

`IntelligentScheduler` 维护了多个字典:
- `domain_stats: Dict[str, dict]` — 无大小限制
- `url_stats: Dict[str, int]` — 无大小限制，广度爬取时可达百万级
- `error_counts: Dict[str, int]` — 无大小限制
- `crawl_frequency: Dict[str, dict]` — 无大小限制
- `content_type_preferences: Dict[str, Any]` — 无大小限制

只有 `response_times` 限制了最近 10 条记录。长时间运行的爬虫（尤其是广度爬取），这些字典会持续增长，导致内存泄漏。

**影响范围**:
- 广度爬取时 `url_stats` 可能达到数百万条目
- 每个域名/URL 的统计信息累积，无法清理
- 内存使用随运行时间线性增长

**修复建议**:

```python
from collections import deque

class IntelligentScheduler:
    MAX_DOMAINS = 1000        # 最多跟踪 1000 个域名
    MAX_URLS = 10000          # 最多跟踪 10000 个 URL
    STATS_RETENTION = 3600    # 统计信息保留 1 小时
    
    def update_stats(self, request: "Request"):
        domain = self._extract_domain(request.url)
        
        # 超出限制时淘汰最旧的记录
        if len(self.domain_stats) >= self.MAX_DOMAINS and domain not in self.domain_stats:
            self._evict_oldest_domain()
        
        # URL 统计使用 LRU 策略
        if len(self.url_stats) >= self.MAX_URLS:
            self._evict_oldest_urls(int(self.MAX_URLS * 0.1))
        
        # ... 原有逻辑
```

---

### MEDIUM-7: Spider.start_requests 分布式模式 dont_filter 逻辑问题

**位置**: `crawlo/spider/__init__.py` L238-249

**问题分析**:

```python
yield Request(
    url=url, 
    callback=self.parse,
    dont_filter=not is_distributed,  # 单机=True, 分布式=False
    meta={'spider_name': self.name}
)
```

| 模式 | `is_distributed` | `dont_filter` | 效果 |
|------|-------------------|---------------|------|
| 单机 | False | True | 跳过去重 |
| 分布式 | True | False | 启用去重 |

逻辑意图是: 分布式模式下多个实例共享 Redis 去重集合，需要对 start_urls 去重避免重复入队; 单机模式下只有一个实例，start_urls 不会重复。

但问题在于: 单机模式下 `start_urls` 如果包含重复 URL，也会被跳过去重直接入队，导致重复请求。正确的做法应该是:

- 单机模式: 也应去重（通过内存过滤器），只是不需要担心多实例重复
- 分布式模式: 必须去重（避免多实例重复入队）

**修复建议**:

```python
# 统一使用 dont_filter=False，由过滤器决定是否去重
yield Request(
    url=url, 
    callback=self.parse,
    dont_filter=False,  # 始终经过过滤器
    meta={'spider_name': self.name}
)
```

或者如果确实需要 start_urls 不被过滤（保证每个实例都能启动），则应该注释说明设计意图:

```python
# 单机模式: 仅一个实例，start_urls 不需要跨实例去重
# 分布式模式: 多个实例共享队列，需要去重避免重复入队
dont_filter=not is_distributed
```

---

## LOW 级缺陷

### LOW-1: ApplicationContext.id 使用 id(self) 在 dataclass 中不可靠

**位置**: `crawlo/application.py` L31

**问题分析**:

```python
@dataclass
class ApplicationContext:
    id: str = field(default_factory=lambda: str(id(self)))
```

`id(self)` 在 `default_factory` lambda 中执行时，`self` 尚未完全构造。Python 的 `id()` 返回对象的内存地址，在 `default_factory` 调用时 `self` 可能还没有稳定。此外，`default_factory` 接受无参函数，但 lambda 中引用了 `self`，这在 dataclass 的字段默认值机制中可能产生意外行为。

**修复建议**:

```python
import uuid

@dataclass
class ApplicationContext:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

---

### LOW-2: Crawler._close_logger_handlers 关闭根 logger 所有 handlers

**位置**: `crawlo/crawler.py` L497-522

**问题分析**:

```python
def _close_logger_handlers(self) -> None:
    try:
        if self._logger:
            for handler in self._logger.handlers[:]:
                try:
                    handler.close()
                    self._logger.removeHandler(handler)
                except Exception:
                    pass
            
            # 也关闭根logger的handlers（如果有的话）
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                try:
                    handler.close()
                except Exception:
                    pass
    except Exception:
        pass
```

关闭根 logger 的所有 handlers 是危险操作:

1. 多爬虫场景下，一个爬虫关闭会移除根 logger 的 handlers，影响其他正在运行的爬虫的日志输出
2. 其他库（如 `aiohttp`、`redis`）的日志也会受影响
3. 关闭后无法恢复，后续日志全部丢失

**修复建议**:

```python
def _close_logger_handlers(self) -> None:
    """只关闭当前 crawler 自己创建的 handlers"""
    try:
        if self._logger:
            for handler in self._logger.handlers[:]:
                try:
                    handler.close()
                    self._logger.removeHandler(handler)
                except Exception:
                    pass
            # 不要关闭根 logger 的 handlers
    except Exception:
        pass
```

---

## 修复优先级建议

| 优先级 | 缺陷 | 修复难度 | 建议时间 |
|--------|------|----------|----------|
| P0 | CRITICAL-3 (重复清理) | 低 | 立即 |
| P0 | CRITICAL-1 (线程锁死锁) | 中 | 1-2天 |
| P1 | CRITICAL-2 (全局状态) | 高 | 需设计 |
| P1 | HIGH-4 (协程结果丢失) | 中 | 1天 |
| P1 | HIGH-1 (事件异常静默) | 低 | 0.5天 |
| P2 | HIGH-2 (非原子状态检查) | 中 | 1天 |
| P2 | HIGH-3 (信号量锁不一致) | 中 | 1天 |
| P2 | MEDIUM-7 (去重逻辑) | 低 | 0.5天 |
| P3 | MEDIUM-5 (Redis 空检查) | 低 | 0.5天 |
| P3 | MEDIUM-6 (无界内存) | 中 | 1天 |
| P3 | 其余 MEDIUM/LOW | 低-中 | 分批处理 |
