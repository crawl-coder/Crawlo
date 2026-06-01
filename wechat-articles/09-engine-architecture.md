# 架构解密：Crawlo Engine 是如何运转的

> 理解引擎，才能用好框架。

---

## Engine：框架的心脏

如果把 Crawlo 比作一个人，Spider 是大脑（决定爬什么），Downloader 是手脚（执行下载），那 **Engine 就是心脏**——它负责让血液（数据）在整个系统中流转。

```
                    ┌───────────────────────────────────┐
                    │             Engine                  │
                    │                                     │
    Request ───────►│  ┌─────────┐   ┌──────────────┐   │
                    │  │Scheduler│──►│  Downloader   │──►│── Response
    ◄───────────────│  └─────────┘   └──────────────┘   │
     Item           │       ▲              │             │
                    │       │              ▼             │
                    │  ┌────┴────┐   ┌──────────┐       │
                    │  │Processor│   │Middleware │       │
                    │  └────┬────┘   └──────────┘       │
                    │       │                           │
                    │  ┌────▼────┐                      │
                    │  │ Pipeline │                      │
                    │  └─────────┘                      │
                    └───────────────────────────────────┘
```

---

## 请求的完整生命周期

一个请求从诞生到消亡，会经历以下阶段：

```
1. 诞生：Spider.start_requests() 或 Spider.parse() yield Request
        │
2. 入队：Engine → Scheduler.enqueue_request()
        │  去重检查（DupeFilter）
        │  优先级排序（PriorityQueue）
        │
3. 出队：Engine 主循环 → Scheduler.next_request()
        │
4. 中间件（请求阶段）：Middleware.process_request()
        │  可修改 Request / 抛出异常 / 返回 Response（短路）
        │
5. 下载：Downloader.fetch(request)
        │  aiohttp / Playwright / CloakBrowser / ...
        │
6. 中间件（响应阶段）：Middleware.process_response()
        │  可修改 Response / 替换 Response
        │
7. 回调：Spider.parse(response) / 自定义 callback
        │  产出新的 Request 或 Item
        │
8a. Request → 回到步骤 2（新的请求）
8b. Item   → Processor → Pipeline → 存储
```

---

## 核心设计：请求生成混入

Engine 的职责被拆分为两个类：

- **Engine** (`engine.py`)：主循环、组件管理、生命周期控制
- **RequestGenerationMixin** (`engine_generation.py`)：请求生成逻辑

这是 **Mixin 模式**，好处是：
- Engine 主类不会过于臃肿
- 请求生成逻辑可以独立测试
- 未来支持新的生成策略时，只需新增 Mixin

### 两种请求生成模式

**传统模式**（`_traditional_generation`）：
```
start_requests() → 逐个 yield → 入队 → 主循环消费
```
简单直接，适合大多数场景。

**受控模式**（`_controlled_generation`）：
```
start_requests() → 批量 yield → 流控检查 → 入队 → 主循环消费
                        │
                   背压控制器
                   （队列满时暂停生成）
```
支持流控和背压，适合大规模爬取。

---

## 并发控制

Engine 的并发模型基于 `asyncio.Task`：

```python
# 每个 _crawl(request) 是一个独立的后台任务
self._create_background_task(self._crawl(req))
```

### 并发限制

```python
# 流控：在途任务数不超过 concurrency + 3
max_inflight = self.concurrency + 3

if len(self._background_tasks) >= max_inflight:
    # 等待任务完成后再派发
    while len(self._background_tasks) >= max_inflight:
        await asyncio.sleep(0.01)
```

### 批量获取

```python
# 批量获取请求，减少调度器交互次数
batch_size = max(self.concurrency, 10)
requests = await self.scheduler.next_request_batch(batch_size)
```

### 深度自动传播

```python
# Engine 自动传播请求深度，用户无需手动设置
if request.depth is None:
    request.depth = (parent_request.depth or 0) + 1
```

---

## 优雅关闭

Engine 的关闭流程尽可能避免数据丢失：

```
收到 Ctrl+C / SIGTERM
        │
        ▼
1. self.running = False          ← 通知主循环退出
2. generation_task.cancel()       ← 停止请求生成
3. 等待活跃任务完成               ← 不中途丢弃
4. 确定关闭原因（shutdown/finished）
5. close_spider(reason=reason)    ← 传入正确的 reason
        │
        ├─ reason='shutdown' → 保存检查点
        ├─ reason='finished' → 清除检查点
        │
6. 关闭 Pipeline（刷新批量数据）
7. 关闭 Downloader（5s 超时保护）
8. 关闭 Scheduler（5s 超时保护）
```

---

## TaskManager：异步任务管家

TaskManager 管理所有后台任务，提供：

- **任务追踪**：记录每个 Task 的状态
- **超时控制**：任务超时自动取消
- **异常收集**：统一收集和报告任务异常
- **动态调频**：根据系统负载动态调整并发度

```python
class TaskManager:
    def create_task(self, coro, name=None):
        """创建受管理的异步任务"""
        task = asyncio.create_task(coro)
        task.add_done_callback(self._on_task_done)
        self._current_tasks.add(task)
        return task
```

---

## 组件初始化顺序

Engine 严格按照以下顺序初始化组件，确保依赖关系正确：

```
1. Scheduler.open()          ← 队列管理器就绪
2. Downloader 实例化         ← 需要配置和事件循环
3. Processor 创建             ← 需要 Pipeline 列表
4. 下载器注册到 ResourceManager ← 资源管理
5. Extension Manager          ← 扩展就绪
6. 集群组件（分布式模式）      ← 需要 Scheduler 和 Redis
7. 检查点恢复（如果存在）      ← 需要 Scheduler 就绪
8. start_requests 解析        ← 需要所有组件就绪
```

---

## 从设计中学到什么

### 1. 职责分离

Engine 不做具体下载，只做调度。Downloader 不做解析，只做下载。每个模块职责单一清晰。

### 2. 异步优先

所有 I/O 操作都是异步的——网络请求、数据库写入、文件 I/O。`async/await` 让代码既高效又可读。

### 3. 背压感知

Engine 从设计层面支持背压——不是事后加的补丁，而是架构的一部分。

### 4. 优雅降级

每个组件都有超时保护和异常兜底，单个组件失败不会拖垮整个系统。

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
