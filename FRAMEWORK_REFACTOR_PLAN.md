# Crawlo 架构重构计划

> 制定时间：2026-08-07
> 问题来源：[FRAMEWORK_REVIEW.md](./FRAMEWORK_REVIEW.md)（架构类问题 #1~#5、#10）
> 验证状态：2026-08-07 已逐条对照代码核实，报告中的 P0/P1 项（#6~#9、#11 及大部分代码质量问题）均已修复；**本计划覆盖仍然存在的架构类问题**。
> 目标分支：develop（逐 Phase 合入，每个 Phase 独立成 PR；Phase 6 Breaking Change 走 v2.0 独立分支）

## 现状核实摘要

| 条目 | 状态 | 证据 |
|------|------|------|
| #1 Engine God Object | 仍存在 | `engine.py` 1022 行，`__init__` 约 44 个 `self.` 赋值，29 处 `_cluster_*` |
| #2 全局状态/单例泛滥 | 仍存在 | `_DEFAULT_SPIDER_REGISTRY` 模块级注册表 + `ApplicationContext` 25+ 字段 + `SingletonMeta`（CoreInitializer/LogManager）+ `get_framework()` 全局单例 |
| #3 延迟导入糊循环依赖 | 仍存在 | `crawler.py` 9 处、`spider.py` 6 处、`framework.py` 3 处、`processor.py` 2 处方法内导入 |
| #4 同步/异步双 API | 仍存在 | `idle()/async_idle()`、`idle()/idle_async()`、`empty()/async_empty()`；`Scheduler.__len__` 对 Redis 返回 0 |
| #5 背压双层重复 | 仍存在 | `Scheduler.enqueue_request` 100×0.5s 重试后 drop（已加日志/统计，不再静默）；`QueueManager.put` 另有硬限制+软延迟+信号量 |
| #10 SpiderMeta 导入时强制注册 | 仍存在 | `spider.py:65-71` 名称冲突直接 `raise ValueError` |

## 总体策略

**增量重构、每步可发布、行为兼容优先。** 不搞大爆炸重写。每个 Phase 独立成 PR，带回归测试。先立防护网（架构测试），再动刀子。

---

## Phase 0：防护网（前置，约 2 天）

在动任何架构前先建约束，否则重构没有验收标准。**Phase 0 完成前禁止开始 Phase 1~5。**

### 0.0 测试基础设施清理（半天，前置中的前置）

当前 `tests/` 平铺 342 个文件，混入大量调试脚本（`debug_*.py`、`final_*.py`、`verify_*.py`、`stress_*.py`、`run_*.py`、`_comprehensive_test.py`），import 时直接执行并 `sys.exit(1)`，导致 pytest collection 崩溃。

- 新建 `scripts/debug_tests/` 目录，把无 `test_` 函数/`Test` 类或 import 即执行 `main()/sys.exit()` 的脚本**物理迁出** `tests/`，保持 `tests/` 下所有文件对 pytest 可 cleanly collect。
- 新建 `tests/unit/`、`tests/integration/`、`tests/arch/` 三级目录，现有脚本按性质迁入（粗略分类即可，不追求完美，只追求 CI 收集稳定）。
- 提交后 CI：`python -m pytest tests/ --collect-only -q` 必须 0 error（含 `tests/scrapy_comparison/` 作为 optional，无 scrapy 环境跳过即可）。

### 0.1 分层契约（半天）

1. **引入 `import-linter`**，在 CI 中声明分层契约：`spider → network → core → queue`，禁止反向依赖。现有违规先全部列入 `ignore_imports` 白名单，之后每修一处删一条。

### 0.2 架构守护测试（半天）

2. **架构守护测试**（`tests/arch/`）：
   - `test_engine_size.py`：断言 `engine.py` 行数只减不增（基线 1022 行）；断言 `Engine.__init__` 顶层 `self.xxx = ` 赋值数 ≤ 基线值。
   - `test_public_api_signatures.py`：对 `Engine`、`ApplicationContext`、`Scheduler`、`QueueManager`、`Processor` 的**公共方法签名**做快照（`dir()` + `inspect.signature()` 哈希），重构期间仅允许加 `@property` 委托，不允许删或改签名；加新方法是允许的。保证重构期间**公共 API 100% 向后兼容**。
   - `test_no_silent_except.py`：基线 `git grep -cE "except\s+Exception\s*:\s*pass" crawlo/`（排除已有 ACK 静默吞错修完后的新计数），重构期间该计数只减不增——防止迁代码时顺手写回 `except: pass`。

### 0.3 行为基线（半天，characterization tests = 把 bug 固化成断言）

3. **行为基线测试**：为后续 Phase 要改的关键行为写 characterization tests，**把当前 buggy 的现状当成「正确」锁死**，改完后再改测试。重构时 failing vs passing 的过渡就是改行为的证据链。
   - `tests/arch/char/char_enqueue_full.py::test_scheduler_enqueue_full_drops_after_50s`：满队列条件下断言 `enqueue_request` 50s 超时后 `return False` + `scheduler/enqueue_dropped_count == 1`（**这是 Phase 2 要改掉的 bug，先锁成基线**）。
   - `tests/arch/char/char_idle_semantics.py::test_idle_sync_vs_async`：对比 `Scheduler.idle()` 返回值 vs `await async_idle()` 的返回值差异（Redis 下 `__len__` 返回 0 的陷阱也要写成断言），Phase 1 改完后此文件整体**删掉**或改成新行为。
   - `tests/arch/char/char_spider_registry.py::test_import_same_name_raises_import_time`：重复定义同名 Spider 时，断言**在 import 阶段就抛 ValueError**（Phase 1 要把这个延后到解析时，所以先锁死旧行为，Phase 1 改完再把这个断言改成 `not raised at import, raised at get_spider_by_name`）。
   - `tests/arch/char/char_spider_registry.py::test_registry_double_data_source_sync`：断言 `_DEFAULT_SPIDER_REGISTRY` 与 `ApplicationContext().spider_registry` 在手动同步后内容一致（Phase 4 要消双数据源，先锁现状）。

---

## Phase 1：#10 注册冲突延迟 + #4 双 API deprecation（约 3 天，低风险）

### #10 SpiderMeta：注册与校验分离，冲突延迟到解析时

1. `SpiderMeta.__new__` 不再 raise。冲突时后注册覆盖先注册，`warnings.warn(SpiderNameConflictWarning)`，并把候选类记入 `_conflicts[name]`。
2. **硬错误推迟到解析时**：`get_spider_by_name(name)` 命中 `_conflicts` 时 raise `AmbiguousSpiderError`，错误信息列出所有候选类的完整模块路径——用户拿到可行动的诊断，而不是 import 就崩。
3. 提供显式 API：`register_spider(name, cls, override=True)` 供高级用户消除歧义。
4. 测试隔离已有 `reset_spider_registry()`，补一个 ctx 级隔离用例（配合 #2 第 2 步）。

### #4 双 API：async 为唯一实现，sync 走 deprecation 通道

1. `Scheduler.idle()`、`Processor.idle()`、`QueueManager.empty()`、`Scheduler.__len__`：保留但加 `DeprecationWarning`（"use async_idle()/async_empty()/async_size(), will be removed in v2.0"）。
2. `__len__` 对 Redis 返回 0 最危险（`if len(scheduler)` 语义错误）——**优先处理**：下一 minor 版本起对非内存队列 `__len__` 直接 raise `TypeError`，引导用 `async_size()`。属 breaking change，release notes 显著标注。
3. 内部调用点全部改走 async 版本（Engine 内 `_check_components_idle` 等已是 async 上下文，改造容易）。
4. 文档加迁移表；v2.0 物理删除 sync 版本。

---

## Phase 2：#5 背压双层合并（约 4 天，中风险）

### 现状

- `Scheduler.enqueue_request`：Condition 等待 + 100×0.5s 重试 + 超限 `return False`（请求丢弃，已有日志/统计兜底）。
- `QueueManager.put`：硬限制拒绝 + 软限制 sleep + 信号量。

两套策略可能互相打架：Scheduler 等 50 秒放弃，QueueManager 软限制又在 put 内部 sleep，等待时间不可预测叠加。

### 方案：等待策略下沉到 QueueManager，Scheduler 只管去重和转发

1. `QueueManager.put(request, priority, *, timeout=None)` 获得阻塞语义：队列满时内部用 Condition/信号量等待（内存队列已有 `_queue_semaphore`，`await acquire()` 即天然阻塞）；超时后抛 `QueueFullTimeout` 异常而非返回 False——**把"丢弃"从隐式返回值变成显式异常**，调用方必须决策。
2. 新增配置：
   - `ENQUEUE_FULL_POLICY = 'block' | 'drop_with_counter' | 'raise'`（**默认 `'drop_with_counter'`**，与当前行为一致：不丢进程、不挂死，有日志+统计兜底）。
     - `block`：入队调用无限期挂起直到有空位，适合确定会消费完的场景。
     - `drop_with_counter`：超时后丢弃并递增 `scheduler/enqueue_dropped_count`，进程继续。
     - `raise`：抛 `QueueFullTimeout` 给上层，由用户决策。
   - `ENQUEUE_BLOCK_TIMEOUT`（默认 `None` = 无限，仅在 `block` 策略生效）。
   - **新增** `ENQUEUE_BLOCK_STALL_ALERT_SECONDS`（默认 `120`）：`block` 模式下，如果引擎 N 秒内既**没有入队成功**也**没有出队消费**，则打一条 `ERROR` 级日志+触发 `notifier.error()` 告警，避免爬虫默默挂死无人知。
3. `Scheduler.enqueue_request` 删除整个 retry/Condition 循环（约 60 行），简化为：去重 → `await queue_manager.put(...)` → 按 policy 处理 `QueueFullTimeout`。`scheduler/enqueue_dropped_count` 统计保留。
4. QueueManager 内"软限制 sleep 背压"保留（流量整形，非等待），但与阻塞等待统一由 `BackpressureController` 协调，避免双重延迟。
5. **关键：阻塞时的 idle 判定修复**（不写就会出死锁）：
   - Engine 新增 `self._pending_enqueue_count: int = 0`（atomic），每次进入 `enqueue_request` 阻塞等待前 `+1`，退出（不管成功/异常/超时）`-1`。
   - `_check_all_idle` 空闲判定条件加一条：`_pending_enqueue_count == 0`。否则"入队在 block 等待"会被判为"没事干" → Engine 提前退出 → 主循环停了 → 消费者也停了 → 入队永远等不到消费 → 死锁。
   - 测试：`tests/arch/test_backpressure_deadlock.py` 构造 1 个消费者、队列满 → 50 个生产者 block → 验证 Engine 不提前退出、不丢请求、最终全部消费完（用 `time_limit` 守护，超时即失败）。
6. **验收测试**：
   - `policy=block` 时满队列不丢请求、不提前退出；
   - `timeout` 到时抛 `QueueFullTimeout`；
   - `policy=drop_with_counter` 时 `enqueue_dropped_count` 正确递增且进程不挂；
   - `STALL_ALERT_SECONDS` 触发告警（mock notifier 断言）。

### 风险

- 默认从"50 秒后丢弃"变为 `'drop_with_counter'`（行为一致，已有计数），不会出现 hang 问题。**若用户显式切 `'block'` 必须配告警守护**，否则"消费者永远不消费（如 pipeline 全 raise）+ 生产者无限阻塞"= 进程僵死，release notes 显著说明。
- **最大的坑已在上文第 5 步写明解法**：`_pending_enqueue_count` 纳入 idle 判定 + 专门死锁回归测试。

---

## Phase 3：#1 Engine God Object 拆解（约 6 天，中风险）

### 职责归属表

| 职责 | 现状位置 | 去向 |
|------|----------|------|
| 集群生命周期 | `ClusterMixin`（已抽出） | 保留，迁入残留 |
| 种子锁（Lua 抢锁/续期/释放） | `_SEED_LOCK_LUA`、`_try_acquire_seed_lock_atomic`、`_renew_seed_lock` | **迁入 `ClusterMixin`**（本就属于分布式协调，已持有 `_cluster_redis`/`_cluster_worker_id`） |
| 检查点 | `_try_resume_from_checkpoint`、`_save_checkpoint`、`_clear_checkpoint` | **新组件 `CheckpointCoordinator`** |
| 日志清理 | `_cleanup_old_logs` | **移入 `LogManager`** |
| 请求生成/输出处理 | `RequestGenerationMixin`、`_handle_spider_output` 等 | 保留 mixin 或转组合 |
| 主循环/调度/背压 | `_run_main_loop`、`_dispatch_requests` 等 | Engine 核心职责，**本期不动** |

### 步骤

**第 1 步（低风险）：迁移游离职责。**
- 种子锁三个成员移入 `ClusterMixin`；Engine 侧只留 `self._seed_lock_key` 状态。
- `_cleanup_old_logs` 移入 `LogManager.cleanup_old_logs()`，Engine 只调用一行。
- 检查点三方法抽成 `crawlo/core/checkpoint_coordinator.py`：**用组合不用 mixin**——`self._checkpoint = CheckpointCoordinator(settings, crawler)`。mixin 共享 `self` 命名空间，是 god object 的变种；新代码一律组合（`ClusterMixin` 保持现状，改造成本大于收益）。

**第 2 步（中风险）：收敛 `__init__`。**
- 15 个 `_cluster_*` 字段收进 `ClusterState` dataclass，`ClusterMixin` 只读写 `self._cluster_state`。
  - **可变/不可变边界显式声明**：`ClusterState` 用 `@dataclass(slots=True)`，字段分两组：
    - **Immutable 组**（初始化完成后不应变动，若被修改应视为 bug）：`worker_id`、`namespace`、`redis`、`stream_key`、`consumer_group`、`heartbeat_interval`、`seed_lock_timeout`、`seed_lock_key_prefix`。加 `frozen=False` 但赋值处只有 `__init__` + **只读 `@property`** 暴露给 mixin，运行时赋值会触发 `AttributeError`。
    - **Mutable 组**（运行时可改）：`heartbeat_last_sent_ts`、`is_leader`、`leader_id`、`shutdown_requested`、`registered`、`last_ping_ts`、`delivery_count_limit`、`dead_letter_exceeded_max`。保留普通字段，附注释说明修改场景。
  - 这样做的目的：迁移之后新加入的开发者必须**显式经过 getter/setter 边界**才能改不可变字段，比直接写 `self._cluster_worker_id` 难以误改得多。
- Engine `__init__` 目标 ≤ 15 个赋值。

**第 3 步（验收）：** `engine.py` ≤ 600 行，Phase 0 守护测试收紧阈值。

### 风险

- Mixin 初始化顺序：迁移种子锁需确保 `_cluster_redis` 先于种子锁逻辑初始化。
- 主循环是 Engine 的合法核心职责，动它风险远超收益，明确划出范围。

---

## Phase 4：#2 全局状态收敛（约 4 天，中风险）

**第 1 步：`ApplicationContext` 拆分为三个内聚子上下文（组合）。**

```text
ApplicationContext
├── registries: RegistryContext        # spider/component/initializer/job registry
├── notifications: NotificationContext # 5 个 channel + deduplicator + locks
└── runtime: RuntimeContext            # redis_manager, pools, fetchers, resources
```

`ApplicationContext` 保留旧字段名为 `@property` 委托（如 `ctx.dingtalk_channel` → `ctx.notifications.dingtalk_channel`），打 `DeprecationWarning`，两个版本后删除——外部代码零破坏。

**第 2 步：消灭双数据源。**
当前 `_DEFAULT_SPIDER_REGISTRY`（模块级）与 `ctx.spider_registry` 靠 `get_global_spider_registry()` 手动同步。方案：**ctx 成为唯一数据源**，模块级 dict 改为 PEP 562 `__getattr__` 属性转发：

```python
# spider.py —— 向后兼容别名
def __getattr__(name):
    if name == '_DEFAULT_SPIDER_REGISTRY':
        return get_global_context().registries.spider_registry
```

**第 3 步：单例去魔化。**
- `CoreInitializer(metaclass=SingletonMeta)` → 实例挂 `ctx.runtime.initializer`，`get_framework_initializer()` 改为从 ctx 取。
  - **关键：facade 必须 lazy，不能 import 时就抓 ctx。** 全仓到处 `from crawlo.initialization import get_framework_initializer`，如果 facade 在模块加载期就访问 `ctx.runtime.initializer`，而 ctx 此时未 ready（典型场景：用户 import 自己的 spider 时触发 spider_meta 注册→registration 路径上某个代码 import 了 initializer），会抛 `AttributeError`。方案：

    ```python
    # crawlo/initialization/__init__.py 推荐实现
    def get_framework_initializer() -> CoreInitializer:
        """Lazy facade: 调用时才从 context 解析，模块加载期不访问 ctx。"""
        if _FRAMEWORK_INITIALIZER_SINGLETON_OVERRIDE is not None:
            return _FRAMEWORK_INITIALIZER_SINGLETON_OVERRIDE   # 测试注入路径
        ctx = get_global_context(create_if_missing=False)
        if ctx is None or ctx.runtime.initializer is None:
            # 兼容路径：若 ctx 未初始化，回退到进程级单例（旧代码行为），打一条 DeprecationWarning
            warnings.warn("get_framework_initializer() called before ApplicationContext ready, falling back to global singleton",
                          DeprecationWarning, stacklevel=2)
            return _legacy_global_initializer_instance
        return ctx.runtime.initializer
    ```
  - 提供测试钩子 `_override_framework_initializer(None|instance)` 让单元测试可无 ctx 注入 mock。
- `LogManager` 的 `SingletonMeta` 保留（日志是进程级资源，单例合理），文档注明这是有意为之的例外。
- `get_framework()` 保留为 facade，内部改为 `ctx.runtime.framework`，同样走 lazy 逻辑（同上 `create_if_missing=False` + 回退 fallback + warnings.warn），不再自创全局。
- **CI 验证**：Phase 0 `test_no_silent_except.py` 的兄弟测试 `tests/arch/test_no_import_time_side_effects.py` 断言："import crawlo + 10 个常用子模块"不触发任何 `get_global_context(create_if_missing=True)`、不创建任何 `ApplicationContext`。

---

## Phase 5：#3 循环依赖治理（约 3 天，低风险）

### 环路事实 + 分类处置原则

```text
依赖方向（上层→下层，单向箭头合法，反向违规）：

CrawlerProcess （组合N个Crawler，属于"进程/启动层"）
       │
       ▼
  Crawler（应用容器，组合Engine）
       │
       ▼
   Engine（调度主循环，组合 Scheduler / Processor / MiddlewareManager 等）
       │
       ├─────────┬───────────────┐
       ▼         ▼               ▼
  Scheduler   Processor    Downloader / Middleware
       │         │               │
       └─────────┴───────┬───────┘
                         ▼
                  QueueManager / Filter / Spider
                         │
                         ▼
              Settings / Request / Response / Item （纯数据层，无下游引用）
```

- `crawler.py:71` 方法内导入 `Spider`；`spider.py:25`（TYPE_CHECKING 块）导入 `Crawler`——**类型注解环**，合法但需规范（见下文 #1）。
- `crawler.py:511` 方法内导入 `CrawlerProcess`——**真环（下层指向上层），必须切**。
- `spider.py:485` 方法内导入 `Request`——运行时导入，可上提。
- `framework.py`/`processor.py` 的延迟导入多为"避免过早初始化"，非真环。

### 方案（按编号对应上面事实）

1. **类型注解环**：全部收进 `if TYPE_CHECKING:` + `from __future__ import annotations`。禁止在运行时 import 仅作注解用的类；Phase 0 结束后 import-linter 会把"运行时反向 import"列成违规，白名单逐项清零。
2. **真环（crawler ↔ crawler_process）：依赖倒置 + 物理删除引用。**
   - 规则：**Crawler（下层）永远不能 import CrawlerProcess（上层）**。箭头只能单向从上往下。
   - `crawler.py:511` 里逻辑如果是"访问 process 层的全局配置/管理能力"：**上移到 CrawlerProcess 中实现**，或通过回调/事件下发给 Crawler，不能由 Crawler 反向 import Process。
   - 硬约束：CI 中加 `git grep -n "from crawlo.core.crawler_process import" crawlo/core/crawler.py`（和其他下层文件）= 0。
3. **"怕初始化"型**：多数可直接上提（如 `spider.py:78` 导入 `get_logger` 纯属多余防御）；确实需要惰性的用 loader 函数显式表达（`def _load_xxx() -> X` + `functools.lru_cache`），禁止把 `from xxx import yyy` 藏在方法体里当"懒加载"——这种行为本质上把依赖图从静态变成运行时，等于把问题转交给了用户和调试器。
4. **固化成果**：每修一处从 import-linter 白名单删一条；白名单清零后，新循环依赖在 CI 直接失败。

---

## 执行顺序与里程碑

| Phase | 内容 | 依赖 | 工期 | 风险 |
|-------|------|------|------|------|
| 0 | 防护网：import-linter + 守护测试 + 行为基线 | 无 | 2d | 低 |
| 1 | #10 注册冲突延迟 + #4 双 API deprecation | 0 | 3d | 低 |
| 2 | #5 背压合并 | 0（行为基线） | 4d | **中**（阻塞语义影响退出检测） |
| 3 | #1 Engine 拆解 | 0 | 6d | 中 |
| 4 | #2 Context 拆分 + 单例去魔化 | 3 | 4d | 中 |
| 5 | #3 延迟导入清零 + CI 契约收紧 | 2、4 | 3d | 低 |

**顺序逻辑**：先做低风险高回报的 #10/#4 建立信心；#5 涉及正确性，赶在架构大动前完成；#1 拆解为 #2 的 ctx 拆分减负；#3 最后做——前面几步会自然消灭一部分延迟导入，且 import-linter 契约要等依赖稳定后才收得紧。

**总计约 22 个工作日**，每个 Phase 结束都可发 minor 版本。

---

## 验收标准（Definition of Done）

- [ ] **Phase 0 (必须先通过)**：`python -m pytest tests/ --collect-only -q` 0 collection error；import-linter 契约落地且白名单已建立（不是空）；`engine.py` 行数/`__init__` 赋值基线写入守护测试；`except Exception: pass` 计数基线 + 公共签名快照基线写入守护测试。
- [ ] `engine.py` ≤ 600 行，`__init__` ≤ 15 赋值，`grep -c "self\._cluster_" crawlo/core/engine.py` = 0（`_cluster_*` 全收进 `ClusterState`）。
- [ ] 方法内延迟导入清零：`grep -rE '^\s+from crawlo\.' crawlo/ --include='*.py' | grep -v TYPE_CHECKING` 无结果。
- [ ] import-linter CI 通过且无白名单（Phase 5 最终验收，中间 Phase 允许白名单递减）。
- [ ] `Scheduler.enqueue_request` 无 retry 循环；`ENQUEUE_FULL_POLICY` 三策略行为有测试覆盖，block 模式下 `_pending_enqueue_count > 0` 不触发 `_check_all_idle` 提前退出（死锁专项回归）。
- [ ] `get_spider_by_name` 冲突时抛 `AmbiguousSpiderError`（含候选类全路径），import 阶段**不**崩，仅 `warnings.warn`。
- [ ] sync API 全部带 DeprecationWarning，文档有迁移表；非内存队列 `len(scheduler)` 抛 `TypeError`，release notes 显著标注。
- [ ] **公共签名 100% 向后兼容**：Phase 0 的 `test_public_api_signatures.py` 全通过（Engine/ApplicationContext/Scheduler/QueueManager/Processor）。
- [ ] **静默吞错计数归零**：Phase 0 `test_no_silent_except.py` 中 `except Exception: pass` 计数 ≤ 基线（严格只减不增，目标重构完归零或仅剩有明确注释的例外）。
- [ ] **facade 懒加载**：`tests/arch/test_no_import_time_side_effects.py` 通过，import crawlo 不触发 `ApplicationContext` 自动创建。

---

## 与 FRAMEWORK_REVIEW.md 的闭环对照

| 报告条目 | 处置 | 状态 |
|----------|------|------|
| #1 Engine God Object | Phase 3 | 待实施 |
| #2 全局状态/单例泛滥 | Phase 4 | 待实施 |
| #3 延迟导入 | Phase 5 | 待实施 |
| #4 双 API | Phase 1 | 待实施 |
| #5 背压双层 | Phase 2 | 待实施 |
| #6 信号量泄漏 | — | ✅ 已修复（核实于 2026-08-07） |
| #7 ACK 静默吞错 | — | ✅ 已修复（核实于 2026-08-07） |
| #8 种子锁非原子 | — | ✅ 已修复（核实于 2026-08-07，Lua 原子化） |
| #9 Item 类级污染 | — | ✅ 已修复（核实于 2026-08-07，实例级 `_dynamic_fields`） |
| #10 SpiderMeta 强制注册 | Phase 1 | 待实施 |
| #11 pickle 默认序列化 | — | ✅ 已修复（核实于 2026-08-07，默认 json） |
| 代码质量类（print/死代码/emoji/License 矛盾等） | — | ✅ 大部分已修复；遗留：`requirements.txt` 中 `aioredis` 待清理 |
| 测试工程化（342 文件平铺、调试脚本混入） | 另行立项 | 待规划（不在本计划范围） |

---

## Phase 6-8：三项后续建议的分步改造计划

> 制定时间：2026-08-08
> 背景：Phase 0-5 执行完毕后遗留的三项**架构例外 / 技术债收尾项**（见 Phase 5 结束时的「后续建议」）。
> 注意：**Phase 6 是 v2.0 Breaking Change，不能在 develop 分支直接发布**；Phase 7、8 可在 develop 分支发布 minor/patch。
> 目标分支：develop（Phase 6 Breaking Change 除外，须走 v2.0 独立分支）
> 依赖关系：Phase 7 可独立执行；Phase 6 与 Phase 8 无相互依赖；Phase 8 可接在 Phase 4 之后独立推进（建议 Phase 7 先做或与 Phase 8 并行）。

| # | 名称 | 性质 | 发布方式 | 估工期 |
|---|------|------|----------|--------|
| Phase 6 | 物理删除 `crawlo.crawler.CrawlerProcess` facade | v2.0 Breaking Change | 必须走 v2.0 分支 | 0.5 天 |
| Phase 7 | `scheduling.daemon.executor` 上提到 commands 层（消除下层调上层架构例外） | 包布局重排（non-breaking，向后兼容 facade） | 合入 develop → v1.x minor | 1 天 |
| Phase 8 | 引入依赖注入替代 35 处 `get_global_context` 全局访问 | 新增基础设施层 | 合入 develop → v1.x major（建议 v2.0 之前完成并磨合） | 5–7 天 |

---

### Phase 6：v2.0 物理删除 CrawlerProcess facade

**要解决的问题**：Phase 5 结束时 `crawlo.crawler.__getattr__` 仍保留 `CrawlerProcess` 反向导出，以 DeprecationWarning 过渡。v2.0 是 breaking change 窗口，应物理删除此反向依赖，彻底消除 `crawlo.crawler → crawlo.crawler_process` 真环。

**影响范围盘点（2026-08-08 现状）**：

| 分类 | 数量 | 说明 |
|------|------|------|
| 框架源码（`crawlo/`） | **0** ✅ | Phase 5 已全部迁移到 `crawlo.crawler_process` |
| 单元/集成测试（`tests/`） | **约 14 处** | `test_automatic_asyncio_fix`（含一条故意验证旧路径）、`test_multiple_spider_modules`、`simple_spider_test`、`test_cloakbrowser_full` 等 |
| `scripts/debug_tests/` | **约 16 处** | 调试脚本（`distributed_test`、`simple_crawlo_test`、`baidu_performance_test` 等） |
| `examples/` | **约 10 处** | `ofweek_standalone`、`ofweek_distributed`、`infoq_dynamic_test`、`errback_examples`、`ofweek_spider` 等 10 个 example run.py |

**分步执行**：

1. **Step 6.1（0.1 天）**：改 `tests/` 下 13 处到新路径；保 1 处专门测试删除后 `AttributeError` 行为，替换现有「故意验证旧路径」的断言
   - `tests/integration/test_automatic_asyncio_fix.py:63` 原断言「旧路径仍工作」→ 改为 `pytest.raises(AttributeError, match="CrawlerProcess")`
2. **Step 6.2（0.1 天）**：改 `scripts/debug_tests/` 下 16 处到新路径
3. **Step 6.3（0.1 天）**：改 `examples/` 下 10 处到新路径（example 是用户参考样板，必须最干净）
4. **Step 6.4（0.1 天）**：物理删除 `crawlo/crawler.py` 中 `__getattr__` 函数 + 模块 docstring 内的 facade 注释段落
5. **Step 6.5（0.1 天）**：删 `pyproject.toml` 的 `crawlo.crawler -> crawlo.crawler_process` 白名单条目 + 注释；同时删 `tests/arch/test_public_api_signatures.py` 中对 `crawlo.crawler.CrawlerProcess` 作为可导入符号的基线（如有）

**验收标准**：

- [ ] `grep -rE "from crawlo\.crawler import CrawlerProcess" /repo --include='*.py'` 仅允许命中 0 处（含 tests/scripts/examples）
- [ ] `python -c "from crawlo.crawler import CrawlerProcess"` 在 v2.0 分支必须抛 `AttributeError: module 'crawlo.crawler' has no attribute 'CrawlerProcess'`
- [ ] `from crawlo.crawler_process import CrawlerProcess` 正常导入
- [ ] import-linter 白名单中 `crawlo.crawler -> crawlo.crawler_process` 条目已删除，`lint-imports` 仍全通过（这意味着 crawler↔crawler_process 真环被彻底打破）
- [ ] CI 全绿：`pytest tests/unit tests/integration tests/arch -q`

**风险**：

- **外部用户私有代码风险**：第三方用户若仍从 `crawlo.crawler` 导入，v2.0 直接 `AttributeError`，必须在 release notes 顶部用警告框说明迁移命令（`sed -i` 一键替换示例）
- Mitigation：发布前写 `crawlo/_migration/v2_crawlerprocess_import.py` 一次性诊断脚本，扫描全目录旧导入

---

### Phase 7：scheduling.daemon.executor 上提到 commands 层

**要解决的问题**：分层契约定义 `commands/shell/mcp/cli` 在 L1，`crawler_process` 在 L2，`scheduling` 在 L4；但 `scheduling.daemon.executor` 作为**进程级爬虫启动器**，必须调用 `CrawlerProcess`（L2），产生「下层调上层」的架构例外。Phase 5 为此单开 1 条带注释的白名单。其真实语义等价于 `crawlo run` 的守护进程版本，**物理位置应在 L1**。

**耦合分析（2026-08-08 现状）**：

```
scheduling.daemon.scheduler ──import──▶ scheduling.daemon.executor.JobExecutor
scheduling.daemon.scheduler ──import──▶ scheduling.daemon.cleanup.ResourceCleanup

job = ScheduledJob(...)  # crawlo.scheduling.job  (L4 内部)
JobExecutor:
  deps: settings(Dict) + _stats(Dict 共享引用) + logger
  职责: 并发控制(semaphore) → execute_job → _run_spider_job → CrawlerProcess.crawl
  唯一「上层调用」：configure_logging()、LoggerFactory.clear_cache()、CrawlerProcess()
```

关键结论：`JobExecutor` 与 `ResourceCleanup`、`SchedulerDaemon` 之间只有构造器参数耦合，没有循环导入。**可以整类上提而不破坏 daemon 内部调度逻辑**，只需在 `scheduling.daemon.scheduler` 里加 `from crawlo.commands.job_executor import JobExecutor` 的兼容导入。

**分步执行**：

1. **Step 7.1（0.1 天）**：新增 `crawlo/commands/job_executor.py`，从 `scheduling/daemon/executor.py` 拷贝 `JobExecutor` 类过去（类体不加改动，保持 API 一致）
   - 同时在 `crawlo/commands/__init__.py` 导出 `JobExecutor`（可选，给内部调用点一个稳定短路径）
2. **Step 7.2（0.2 天）**：旧位置 `crawlo/scheduling/daemon/executor.py` 改为 re-export facade + DeprecationWarning
   ```python
   # crawlo/scheduling/daemon/executor.py
   import warnings
   from crawlo.commands.job_executor import JobExecutor  # noqa: F401  兼容 re-export
   warnings.warn(
       "Importing JobExecutor from crawlo.scheduling.daemon.executor is deprecated; "
       "use crawlo.commands.job_executor instead.",
       DeprecationWarning, stacklevel=2,
   )
   ```
   - `DaemonExecutor` 类（如果外部有人调用）也一并 re-export 带 DeprecationWarning
3. **Step 7.3（0.1 天）**：迁移 `scheduling.daemon.scheduler:14` 的导入路径到 `crawlo.commands.job_executor`（这是唯一框架内部导入点）
4. **Step 7.4（0.1 天）**：更新 `pyproject.toml` 的 import-linter 白名单：
   - 删 `crawlo.scheduling.daemon.executor -> crawlo.crawler_process` 条目（不再存在）
   - `crawlo.commands.job_executor -> crawlo.crawler_process` 是合法的「L1 → L2」调用，**无需白名单**
   - `crawlo.scheduling.daemon.scheduler -> crawlo.commands.job_executor` 是「L4 → L1」的反向依赖，但此路径仅为 SchedulerDaemon 调用 job runner，单开 1 条白名单并注释（等价于 scheduler 调用 commands API 启动子进程）
5. **Step 7.5（0.2 天）**：grep 全仓 `from crawlo.scheduling.daemon.executor` 替换为新路径；tests 里如有 1 处故意验证旧路径，改为验证 DeprecationWarning
6. **Step 7.6（0.3 天）**：跑 SchedulerDaemon 端到端路径验证：新建 `tests/integration/test_job_executor_relocation.py`，断言：
   - `from crawlo.commands.job_executor import JobExecutor` 直接导入正常
   - `from crawlo.scheduling.daemon.executor import JobExecutor` 触发 DeprecationWarning
   - 构造最小 `SchedulerDaemon` + mock 定时任务，验证 executor 调用链通过（可 monkeypatch `CrawlerProcess.crawl` 做 dry-run）

**验收标准**：

- [ ] `lint-imports` 全通过；白名单中 `crawlo.scheduling.daemon.executor -> crawlo.crawler_process` 已删除
- [ ] 新路径 `from crawlo.commands.job_executor import JobExecutor` 正常使用；旧路径抛 DeprecationWarning
- [ ] `SchedulerDaemon` 初始化到 `execute_with_semaphore` 的完整链路用 monkeypatch dry-run 测试通过
- [ ] 代码审计：`crawlo/scheduling/daemon/executor.py` 仅剩 re-export 代码（类体代码数应从 175 行减到 ~15 行）
- [ ] CI 全绿

**风险**：

- **JobExecutor 导入路径变化**：若有第三方用户代码直接 `from crawlo.scheduling.daemon.executor import JobExecutor`，先收到 DeprecationWarning，v2.0 再物理删除旧文件（参考 Phase 6 节奏）
- **DaemonExecutor 类**：如果外部有人用到 `executor.py:top-level` 导出的 `DaemonExecutor` 类，同步在新 `commands/job_executor.py` 里上提即可（调研确认目前只导出 `JobExecutor`）
- **Mitigation**：白名单过渡期至少 1 个 minor 版本再物理删旧 executor.py

---

### Phase 8：引入依赖注入替代 35 处 `get_global_context` 全局访问

**要解决的问题**：ApplicationContext 虽然已拆成 3 个子上下文，但 35 处「模块内 / 函数内 `from crawlo.core.application import get_global_context; ctx = get_global_context()`」仍是「全局服务定位器」反模式，带来：(a) 测试困难（每个调用点都要 mock ctx）；(b) 依赖隐藏（函数签名看不出依赖什么）；(c) ctx 必须提前创建，与 `test_no_import_time_side_effects.py` 的懒初始化目标冲突。引入轻量 DI 容器，把 35 处按场景迁移。

**35 处 `get_global_context` 场景分类（2026-08-08 现状）**：

| 组 | 调用点 | 实际访问 ctx 字段 | 建议 DI 策略 | 估算 |
|----|--------|-------------------|--------------|------|
| A. 通知渠道 | `bot/channels/*.py`（5 个） × 2 处 ≈ 10 次 | `ctx.notifications.bot_channels / notifier` | 构造器注入 `NotifierRegistry` | 1 天 |
| B. 扩展监控 | `extension/monitor/monitor_manager.py` (1)、`performance_monitor.py` (1)、`bot/core/notifier.py` (2)、`bot/core/handlers.py` (1) | `ctx.runtime._monitor_manager / error_handler_instance` | 构造器注入 `MonitorManager` / `ErrorHandler` | 0.5 天 |
| C. 连接池 & 资源 | `utils/redis/pool.py`（3 处）、`utils/resource_manager.py`（2 处）、`queue/redis_priority_queue.py`（1 处）、`utils/error_handler.py`（1 处） | `ctx.runtime.connection_pools / redis_manager / resources / queue_error_handler` | `get_pool(redis_uri)` 改成资源池 self-host，不再挂全局 ctx | 1 天 |
| D. 注册表类 | `factories/__init__.py`（1）、`factories/registry.py`（1）、`initialization/registry.py`（1）、`scheduling/registry.py`（1）、`bot/templates/manager.py`（1）、`bot/monitoring/templates.py`（1）、`bot/utils/deduplicator.py`（2）、`bot/utils/config_loader.py`（1） | `ctx.registries.component_registry / initializer_registry / template_registry / dedup_registry / job_registry / notification_templates` | 各 Registry 改为类级全局 instance（已在 Phase 4 清理了双数据源，已安全）+ 显式 `default_registry()` 工厂方法 | 1 天 |
| E. MCP 单例 | `mcp/quick_fetcher.py`（2 处）、`mcp/server.py`（1 处） | `ctx.runtime.quick_fetcher / mcp_fetcher / mcp_fetcher_lock` | 用 `functools.lru_cache` / `weakref` 模块级 lazy 创建，不走 ctx 存储 | 0.5 天 |
| F. Spider registry proxy | `spider/spider.py`（2 处） | `ctx.registries.spider_registry` | 已在 Phase 4 用 `_SpiderRegistryProxy` 处理，**不做迁移**（proxy 机制本身就是对 ctx 的轻访问，改构造器注入会破坏 `@Spider` 装饰器易用性） | 0 |
| G. CrawlerProcess facade | `crawlo/core/__init__.py:lazy facade`（1 处）、`crawlo/framework.py`（2 处） | `ctx.runtime.initializer` + 通用访问 | Lazy facade 是合理存在，**不做迁移**（这是 ctx 被设计为中心入口的点） | 0 |
| **合计** | 35 处 | | A-F 六组 | 4–5 天核心迁移 + 1 天容器基础设施 + 1 天测试 = 5–7 天 |

**现有 `ComponentRegistry`（factories 层）的能力边界**：
- 现有机制能做：根据 name + component_type 查找 spec、注入 `crawler` 依赖、按 spec.factory_func 创建实例
- 现有机制**不能**做：
  - 实例生命周期管理（singleton / transient / scoped 作用域）——目前 `ComponentRegistry.clear()` 会清所有单例，但没有作用域概念
  - 非 Crawler 依赖注入（比如 bot channels 需要 `NotifierRegistry`、`redis_manager`，`crawler` kwarg 不够用）
  - 构造器参数自动解析（必须手动 `**kwargs` 传）
  - lazy injection（直到用到才创建实例，以满足 import 期不创建 ctx 的约束）

**新增基础设施（Container）**：
在 `crawlo/container.py` 新建一个最小 DI 容器（不引入第三方库，保持轻量；单文件 ~300 行），API 设计：

```python
# crawlo/container.py

from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")

class Container:
    """最小依赖注入容器。

    语义：
    - Scope.SINGLETON: 每次 resolve 返回同一实例（类级全局）
    - Scope.TRANSIENT: 每次 resolve 新建
    - Scope.REQUEST: 每个 CrawlerProcess run 作用域（借 ctx.runtime.crawlers 的生命周期）

    注入方式：
    1. 装饰器 @inject 标记 __init__ 参数（按类型 resolve）
    2. register_factory(Type, factory_callable) 手动注册无法 auto-wire 的资源
    3. Container.resolve(Type) 显式获取
    """

    # 构造器：不依赖 ApplicationContext（满足 import 期零副作用）
    def register_singleton(self, cls: Type[T], factory: Callable[[], T]) -> None: ...
    def register_transient(self, cls: Type[T], factory: Callable[[], T]) -> None: ...
    def register_instance(self, cls: Type[T], instance: T) -> None: ...
    def resolve(self, cls: Type[T]) -> T: ...
    def clear(self) -> None: ...

# 模块级全局容器（替代 35 处 get_global_context()；它是纯 registry，不带业务状态）
default_container = Container()

def inject(func: Callable) -> Callable:
    """类构造器装饰器：按类型注解从 default_container 自动 resolve 参数。

    用法:
        class DingTalkChannel:
            @inject
            def __init__(self, notifier: NotifierRegistry):
                self.notifier = notifier
    未注册的类型会抛 ContainerResolutionError（包含缺啥、已注册啥、调用栈）
    """
```

**关键约束**：
- `Container` 本身零外部依赖（只依赖 typing），import `crawlo.container` **不得**触发 `ApplicationContext` 创建（`test_no_import_time_side_effects.py` 必须继续通过）
- 与 ApplicationContext 的桥接：ApplicationContext 在 `__init__` 里把 `registries.*`、`runtime.*`、`notifications.*` 的实例 `register_instance` 进 `default_container`，**仅此一处** — 之后 35 处调用点不再需要碰 ctx

**分步执行（5–7 天）**：

1. **Step 8.1（1 天）容器基础设施**
   - 新建 `crawlo/container.py`，实现 `Scope`、`Container`、`@inject`、`default_container`
   - 单元测试：`tests/unit/test_container.py` — singleton/transient/作用域、`@inject` 自动装配、未注册类型抛 `ContainerResolutionError`、线程安全（Container 内部用 RLock）
   - **架构守护测试**：`python -c "import crawlo.container"` 后检查 `_global_context is None`

2. **Step 8.2（0.5 天）ApplicationContext ↔ Container 桥接**
   - 在 `ApplicationContext.__init__` 末尾加 `_bind_to_container(self)`：把三个子上下文的公共实例 register 进 default_container
   - 提供 `ApplicationContext.cleanup` 后的 `Container.clear(ctx_id)` 语义（避免跨 ctx 残留）
   - 签名快照基线要更新（ApplicationContext 只加私有方法，公共接口不变 → Phase 0 测试仍 pass）

3. **Step 8.3（1 天）注册表类组迁移（D 组，9 处）**
   - 每个 Registry 类：构造器加 `@inject` + 类型注解；删内部 `get_global_context()` 调用
   - `factories/registry.py:get_component_registry()`：`return default_container.resolve(ComponentRegistry)`
   - 关键：保持「首次 resolve 时 lazy 创建」（singleton factory，不是 eager），满足 import 期零副作用
   - 验证：9 处从 `ctx.registries.*` 访问变 `container.resolve()`，等价行为

4. **Step 8.4（1 天）连接池 & 资源组（C 组，7 处）**
   - `utils/redis/pool.py`：`_close_all_pools`、`_close_pool` 把 `ctx.connection_pools` 改为模块级 `_POOLS: Dict[str, RedisPool]` + `Lock`（其实就是从「挂在全局 ctx」改为「挂在模块级」，语义完全等价，但容器统一管理生命周期）
   - `utils/resource_manager.py`：`ResourceManager` 构造器加 `@inject resource_managers_registry: ResourceManagersRegistry`
   - 关键回归：`close_all_pools()` 关闭所有池的行为不变（写 characterization test 先锁现状）

5. **Step 8.5（1 天）通知渠道组（A 组，10 处）**
   - 5 个 channel 类 + `handlers.py`：构造器加 `@inject notifier: NotifierRegistry`
   - `NotifierRegistry` 作为容器 singleton，首次 resolve 时从 `ctx.notifications.bot_channels` 懒加载
   - 验证：钉钉/飞书/企微/邮件/短信发送功能集成测试通过（mock HTTP 外发即可）

6. **Step 8.6（0.5 天）扩展监控组（B 组，5 处）**
   - `MonitorManager`、`PerformanceMonitor`、`ErrorHandler` 改为容器 singleton + `@inject`
   - `bot/core/notifier.py` 2 处 + `handlers.py` 1 处迁移
   - 注意：`extension.monitor.monitor_manager.py` 现有模块级 `monitor_manager = MonitorManager()` 单例保留（与 container.resolve 返回同一对象，通过 register_instance 对齐）

7. **Step 8.7（0.5 天）MCP 单例组（E 组，3 处）**
   - `quick_fetcher.py`：用 `functools.lru_cache(maxsize=1)` 包裹 `_get_quick_fetcher()`，不再存 `ctx.runtime.quick_fetcher`
   - `server.py`：`ctx.mcp_fetcher` 同上改模块级缓存
   - 注意：`mcp_fetcher_lock` threading.Lock 本来就是运行时创建，保持模块级即可

8. **Step 8.8（1 天）验收测试 + 代码审计**
   - 全仓 grep：`get_global_context()` 调用点只留 G 组（crawlo.core facade/framework.py 的 lazy facade）和 F 组（spider proxy）——**目标 < 5 处**
   - 新增 `tests/arch/test_container_imports_lazy.py`：`import crawlo.bot.channels.dingtalk` 之后不触发 ctx 创建
   - 新增 `tests/arch/test_no_get_global_context_in_utils.py`：`grep "get_global_context" crawlo/utils crawlo/bot crawlo/extension crawlo/queue crawlo/mcp` = 0（按包拆分断言，允许白名单过渡）
   - 跑全量测试 + import-linter；CI 绿

**验收标准**：

- [ ] `grep -rE "= get_global_context\(\)|from crawlo\.core\.application import get_global_context" crawlo/{utils,bot,extension,queue,mcp,factories,initialization,scheduling} --include='*.py'` = 0（或仅剩 ≤ 3 处带注释的白名单过渡）
- [ ] 新容器单元测试覆盖：singleton/transient/`@inject` 自动装配/未注册报错/线程安全/clear 重入，全部通过
- [ ] `test_no_import_time_side_effects.py` 仍然通过（容器 + 所有 @inject 类 import 后不触发 `ApplicationContext` 创建）
- [ ] Characterization tests（Redis 池关闭、bot 通知、Monitor 统计上报）行为等价 100% 通过
- [ ] `tests/arch/test_no_get_global_context_in_utils.py` 通过（utils/bot/extension/queue/mcp 包内「零全局 ctx 访问」）

**风险与缓释**：

| 风险 | 影响 | 缓释 |
|------|------|------|
| Container 首次装配时找不到注册实例 → `ContainerResolutionError` | 启动期崩溃（而非运行时） | 在 `ApplicationContext._bind_to_container()` 之后跑自检（`Container.resolve_all_registered()`），失败时把「已注册列表 + 失败类」打在日志里，启动期失败比运行时好定位 |
| 与现有 `ComponentRegistry` 双轨制 → 两套注册表不同步 | 代码膨胀、困惑 | Step 8.3 把 `ComponentRegistry` 本身作为 Container 的 singleton 注册进去，并在注释里写清：`ComponentRegistry` = 「Crawler 内部组件的工厂集合」；`Container` = 「跨层全局资源的定位器」，两者不同维度 |
| Singleton 类内部缓存与 Container 冲突（双重单例） | 同一类两个实例 | 采用 register_instance 优先：凡已有模块级 instance（如 `monitor_manager`），直接把它 register 进去，不在 Container 里再创建一个 |
| 第三方扩展直接 `get_global_context()` 未迁移 | 破坏行为兼容 | `get_global_context()` 本身保留，只是框架内部不使用；外部代码继续工作，只是在文档里推荐迁移到 DI |

---

## 三项计划的执行顺序建议

```
develop 分支（v1.x）
 ├─ Phase 7（立即）── 0 风险 non-breaking，优先合入
 ├─ Phase 8（并行或 Phase 7 之后）── 大型改造，建议分 8 个 Step 逐 PR 合入，每个 Step 都可独立发布
 └─ Phase 6（最后，等 v2.0 分支）── Breaking Change，必须与「sync idle() 物理删除」「len(scheduler) 物理抛 TypeError」等 v2.0 批次一起处理
```

优先级排序（从高到低）：
1. **Phase 7**：收益/成本比最高（1 天改完，白名单 -1，不再有「下层调上层」例外，non-breaking）
2. **Phase 8 Step 8.1 + 8.2**：容器基础设施（独立 PR，无业务影响）
3. **Phase 8 Step 8.3（注册表组）**：改动独立，风险最低的一组
4. **Phase 8 Step 8.6（扩展监控组）**：与注册表组互不依赖
5. **Phase 8 Step 8.5（通知渠道）**：依赖 8.2 的桥接
6. **Phase 8 Step 8.4（连接池）**：可能有并发问题，谨慎单独立项
7. **Phase 8 Step 8.7（MCP）**：独立小步
8. **Phase 8 Step 8.8（总验收）**
9. **Phase 6**：v2.0 分支执行

每项开始时在 todo 中标记 `in_progress`，完成后标记 `completed` 并写 summary。

---

## Phase 9：架构债收尾（B 档 8 条，约 12–15 天）

> 制定时间：2026-08-08
> 背景：Phase 6–8 完成后，双视角架构审查（高级工程师 + 普通工程师）识别出 8 条架构债。这些不是 bug，而是影响**上手体验、可维护性、可演进性**的结构性缺陷。按「收益/成本比」从高到低分 5 个 Step 推进。
> 目标分支：develop（Step 9.5 物理删除部分须走 v2.0 分支）
> 依赖关系：Step 9.1–9.4 可在 develop 分支并行或串行；Step 9.5 依赖 9.1–9.4 全部完成，且须走 v2.0 分支。

### 总览

| Step | 名称 | 对应 B 档条目 | 优先级 | 估工期 | 发布方式 |
|------|------|--------------|--------|--------|----------|
| 9.1 | examples 结构统一 + scheduling 双入口合并 | #1 #2 | P0 | 2 天 | develop minor |
| 9.2 | 公共 API 别名从 `__all__` 移除 + scheduler 模块重命名 | #3 #4 | P1 | 1.5 天 | develop minor |
| 9.3 | utils/ 根目录膨胀切块 | #5 | P1 | 3 天 | develop minor |
| 9.4 | 顶层大文件拆分（interfaces / exceptions / config） | #6 | P2 | 3–4 天 | develop minor |
| 9.5 | commands↔scheduling 依赖方向反转 + v2.0 删除清单归档 | #7 #8 | P2 | 2.5 天 | v2.0 Breaking |

**总计约 12–15 个工作日**，Step 9.1–9.4 可在 develop 分支逐 PR 合入，Step 9.5 须走 v2.0。

---

### Step 9.1：examples 结构统一 + scheduling 双入口合并（2 天，P0）

**问题 #1**：examples/ 下 7 个示例目录结构不一致（有的双层嵌套 `proj/proj/spiders/`，有的单层 `proj/spiders/`），run.py 入口也不统一（仅 2 个支持 `--schedule`，其余不支持），新手「照 A 抄 B」路径错误。

**问题 #2**：`crawlo.scheduling` 有两个 `start_scheduler()`——[scheduling/__init__.py#L24](file:///Users/oscar/projects/Crawlo/crawlo/scheduling/__init__.py#L24) 转发到 [scheduling/daemon_scheduler.py#L11](file:///Users/oscar/projects/Crawlo/crawlo/scheduling/daemon_scheduler.py#L11)，普通工程师 grep 迷惑。

#### 9.1.1 examples 统一（1 天）

1. **结构对齐**：9 个 Crawlo 原生 example（除 `scrapy_ofweek/`）统一为 `<project_name>/spiders/`、`<project_name>/settings.py` 双层嵌套（与 `crawlo startproject` 生成的真实结构一致）
   - 需改结构：`ofweek_standalone/`、`ofweek_spider/`、`errback_examples/`（目前是单层）
   - 保持不变：`eastmoney_fin_report_crawler/`、`infoq_dynamic_test/`、`listed_companies_market_value_info/`、`ofweek_distributed/`（已是双层）
2. **run.py 入口统一**：所有 example 的 `run.py` 支持两种模式：
   - 默认：`asyncio.run(CrawlerProcess().crawl('spider_name'))`
   - `--schedule`：`from crawlo.scheduling import start_scheduler; start_scheduler(project_root)`
3. **补充 README**：`examples/README.md` 列出每个示例的「学什么 + 怎么跑 + 关键配置项」三行表

#### 9.1.2 scheduling 双入口合并（1 天）

1. **删除 `scheduling/daemon_scheduler.py`**，把 `start_scheduler()` 实现搬进 [scheduling/__init__.py](file:///Users/oscar/projects/Crawlo/crawlo/scheduling/__init__.py#L24)（当前只是 3 行转发，合并后减少一层间接）
2. **或**：把 `start_scheduler()` 移到 [commands/schedule.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/schedule.py)（「启动调度器」本质是 CLI 概念），`scheduling/__init__.py` 改为 re-export facade
3. 更新 `examples/*/run.py` 中 `from crawlo.scheduling import start_scheduler` 的导入路径（如果选择方案 2）
4. grep 全仓确认 `start_scheduler` 只有一个定义点

**验收标准**：
- [ ] `grep -rn "def start_scheduler" crawlo/` 仅命中 1 处
- [ ] 所有 example `python run.py --help` 输出包含 `--schedule` 选项
- [ ] `python run.py --schedule` 在任一 example 下不报 ImportError
- [ ] `examples/README.md` 存在且包含 9 个示例的索引表

---

### Step 9.2：公共 API 别名清理 + scheduler 模块重命名（1.5 天，P1）

**问题 #3**：`core/__init__.py` 的 3 个 deprecated 别名（`async_initialize_framework`、`bootstrap_framework`、`get_bootstrap_manager`）仍在公共 `__all__` 里，新手混用。

**问题 #4**：`core/scheduler.py`（引擎内 TaskScheduler）与 `scheduling/`（定时任务 Cron/Interval）都叫 scheduler，grep 命中 4+ 文件。

#### 9.2.1 别名从 `__all__` 移除（0.5 天）

1. [core/__init__.py](file:///Users/oscar/projects/Crawlo/crawlo/core/__init__.py#L104-L114)：把 `async_initialize_framework`、`bootstrap_framework`、`get_bootstrap_manager` 从 `__all__` 列表移除
2. 函数本身保留（加 DeprecationWarning 已有），只是不再作为推荐公共 API 导出
3. grep 全仓确认无框架内部代码使用这三个别名（仅外部用户可能用，DeprecationWarning 已覆盖）
4. 同步检查 [crawlo/__init__.py](file:///Users/oscar/projects/Crawlo/crawlo/__init__.py#L109-L117) 的 `__all__`，移除 `get_bootstrap_manager`

#### 9.2.2 core/scheduler.py 重命名（1 天）

1. `crawlo/core/scheduler.py` → `crawlo/core/task_scheduler.py`，类名 `Scheduler` → `TaskScheduler`（或保留类名，仅改文件名）
2. 旧路径 `crawlo/core/scheduler.py` 保留为 re-export facade + DeprecationWarning
3. 更新所有内部导入点（grep `from crawlo.core.scheduler import` / `from crawlo.core import scheduler`）
4. 更新 `test_public_api_signatures.py` 基线（如果改了类名）
5. **风险评估**：`Scheduler` 被 Engine 组合，是高频内部引用；改文件名风险低，改类名风险中（需要签名基线更新），建议**仅改文件名 + 保留类名**，v2.0 再改类名

**验收标准**：
- [ ] `grep -rn "async_initialize_framework\|bootstrap_framework\|get_bootstrap_manager" crawlo/ --include='*.py'` 仅命中定义处 + DeprecationWarning，不在任何 `__all__` 中
- [ ] `from crawlo.core.task_scheduler import Scheduler` 正常导入
- [ ] `from crawlo.core.scheduler import Scheduler` 抛 DeprecationWarning
- [ ] `test_public_api_signatures.py` 全通过

---

### Step 9.3：utils/ 根目录膨胀切块（3 天，P1）

**问题 #5**：utils/ 根目录 16 个文件 7 个 300+ 行（encoding_detector 601L、resource_manager 498L、misc 325L、curl_parser 324L、error_handler 304L、process_utils 295L、async_lock 289L），而 db/redis/request/batch 已按主题切子目录——根目录是历史垃圾桶。

#### 9.3.1 建子目录 + 迁移（2 天）

按主题切 5 个子目录：

| 新路径 | 迁入文件 | 行数 |
|--------|---------|------|
| `utils/encoding/` | `encoding_detector.py` | 601 |
| `utils/concurrency/` | `async_lock.py`、`asyncio_utils.py`、`process_utils.py` | 663 |
| `utils/parsing/` | `curl_parser.py`、`page_utils.py`、`time_format.py` | 546 |
| `utils/errors/` | `error_handler.py` | 304 |
| `utils/_compat/` | `py314_compat.py` | 131 |

保留在 utils/ 根目录的仅限：
- `__init__.py`（导出转发）
- `misc.py`（逐步清空，内容按主题迁入子目录或删除）
- `singleton.py`（85L，通用工具，放根目录合理）
- `decorators.py`（27L，同上）
- `func_tools.py`（52L，同上）
- `config_manager.py`（31L，同上）
- `resource_manager.py`（498L，Phase 8 RuntimeContext 一等公民，建议 v2.0 迁入 `core/runtime/`，本期保留原位）

#### 9.3.2 旧路径 re-export facade（0.5 天）

每个迁移的文件在旧位置保留 1 个 re-export facade：

```python
# crawlo/utils/encoding_detector.py（旧路径）
import warnings
from crawlo.utils.encoding.encoding_detector import *  # noqa: F401,F403
warnings.warn("Importing from 'crawlo.utils.encoding_detector' is deprecated; "
              "use 'crawlo.utils.encoding' instead.",
              DeprecationWarning, stacklevel=2)
```

#### 9.3.3 misc.py 清理（0.5 天）

1. 逐函数审查 `misc.py`（325L），把有明确主题的函数迁入对应子目录
2. 剩余真正的"杂项"函数 ≤ 50 行时保留，否则标记为 v2.0 删除候选

**验收标准**：
- [ ] `utils/` 根目录 `.py` 文件 ≤ 8 个（当前 16 个）
- [ ] 每个旧路径 import 仍可用（带 DeprecationWarning）
- [ ] `grep -rE "from crawlo\.utils\.(encoding_detector|async_lock|curl_parser|error_handler|process_utils)" crawlo/ --include='*.py'` 框架内部 = 0（全迁新路径）
- [ ] CI 全绿（含 `test_no_import_time_side_effects.py`）

---

### Step 9.4：顶层大文件拆分（3–4 天，P2）

**问题 #6**：`interfaces.py`（657L）、`config.py`（493L）、`exceptions.py`（484L）三个顶层文件过大，import 一个 bot 异常会把整个引擎异常类拉进来。

#### 9.4.1 exceptions.py 拆分（1 天）

1. 按领域拆分：
   - `core/exceptions.py`：引擎级（EngineError、EngineNotRunning 等）
   - `network/exceptions.py`：下载级（DownloadError、TimeoutError 等）
   - `bot/exceptions.py`：通知级（NotificationError、ChannelError 等）
   - `queue/exceptions.py`：队列级（QueueFull、QueueEmpty 等）—— `queue/interfaces.py` 已有部分，合并
2. 顶层 `exceptions.py` 改为 re-export facade + DeprecationWarning
3. 更新所有 `from crawlo.exceptions import X` 内部导入点

#### 9.4.2 interfaces.py 拆分（1.5 天）

1. 按领域拆分：
   - `core/interfaces/scheduler.py`：IScheduler
   - `pipelines/interfaces.py`：IPipeline（`pipelines/` 已有部分）
   - `queue/interfaces.py`：IQueue（`queue/interfaces.py` 已存在，合并）
   - `downloader/interfaces.py`：IDownloader（`downloader/` 已有部分）
2. 顶层 `interfaces.py` 改为 re-export facade
3. **风险评估**：interfaces 被全仓引用，拆分后每个接口文件变小但导入路径变多；建议**仅拆 ≥ 200 行的大块**，小接口留原处

#### 9.4.3 config.py 审查（0.5–1 天）

1. `config.py`（493L）审查内容，判断是否可按领域拆分或部分逻辑迁入 `settings/`
2. 如果大部分是「配置加载 + 环境变量解析」，可拆为 `config/loader.py` + `config/env.py`
3. 如果大部分是「默认配置常量」，迁入 `settings/default_settings.py`

**验收标准**：
- [ ] `exceptions.py` ≤ 50 行（纯 re-export）
- [ ] `interfaces.py` ≤ 100 行（纯 re-export）
- [ ] 每个领域异常文件 ≤ 150 行
- [ ] 旧路径 import 仍可用（带 DeprecationWarning）
- [ ] `test_public_api_signatures.py` 全通过

---

### Step 9.5：commands↔scheduling 依赖反转 + v2.0 删除清单归档（2.5 天，P2，v2.0）

**问题 #7**：`scheduling/daemon/scheduler.py`（业务层）直接 import `commands/job_executor.py`（适配层），违反整洁架构 The Dependency Rule——业务层不应依赖 CLI 适配层。

**问题 #8**：ApplicationContext 36 条 `@property` 委托是 Phase 8 的兼容层，v2.0 须一次性删除，但当前无归档清单。

#### 9.5.1 JobExecutor 下沉到 runtime 层（1.5 天）

1. 新建 `crawlo/runtime/job_executor.py`，从 [commands/job_executor.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/job_executor.py) 搬运 `JobExecutor` 类
2. `commands/job_executor.py` 改为 re-export facade + DeprecationWarning（与 Phase 7 做法一致）
3. [scheduling/daemon/scheduler.py#L14](file:///Users/oscar/projects/Crawlo/crawlo/scheduling/daemon/scheduler.py#L14) 改为 `from crawlo.runtime.job_executor import JobExecutor`
4. 新建 `crawlo/runtime/__init__.py`（如果不存在），导出 `JobExecutor`
5. 更新 import-linter 契约：
   - `scheduling.daemon.scheduler → runtime.job_executor`（L4→L3 合法）
   - `commands.job_executor → runtime.job_executor`（L1→L3 合法 re-export）
   - 删除 `scheduling.daemon.scheduler → commands.job_executor` 白名单

#### 9.5.2 v2.0 删除清单归档（0.5 天）

在 `FRAMEWORK_REFACTOR_PLAN.md` 末尾新增「v2.0 Breaking Change 删除清单」章节，逐条列出：

| # | 待删除项 | 当前位置 | 过渡策略 | 验收断言 |
|---|---------|---------|---------|---------|
| 1 | `crawlo.crawler.__getattr__('CrawlerProcess')` | [crawler.py](file:///Users/oscar/projects/Crawlo/crawlo/crawler.py) | Phase 6 DeprecationWarning → v2.0 物理删除 | `from crawlo.crawler import CrawlerProcess` 抛 AttributeError |
| 2 | `scheduling.daemon.executor` re-export | [executor.py](file:///Users/oscar/projects/Crawlo/crawlo/scheduling/daemon/executor.py) | Phase 7 DeprecationWarning → v2.0 物理删除 | 旧路径 import 抛 ModuleNotFoundError |
| 3 | `commands.job_executor` re-export | [commands/job_executor.py](file:///Users/oscar/projects/Crawlo/crawlo/commands/job_executor.py) | Step 9.5.1 DeprecationWarning → v2.0 物理删除 | 旧路径 import 抛 ModuleNotFoundError |
| 4 | `core/scheduler.py` re-export | [core/scheduler.py](file:///Users/oscar/projects/Crawlo/crawlo/core/scheduler.py) | Step 9.2.2 DeprecationWarning → v2.0 物理删除 | 旧路径 import 抛 ModuleNotFoundError |
| 5 | `async_initialize_framework()` | [core/__init__.py#L30](file:///Users/oscar/projects/Crawlo/crawlo/core/__init__.py#L30) | Step 9.2.1 DeprecationWarning → v2.0 物理删除 | `from crawlo.core import async_initialize_framework` 抛 AttributeError |
| 6 | `bootstrap_framework()` | [core/__init__.py#L89](file:///Users/oscar/projects/Crawlo/crawlo/core/__init__.py#L89) | 同上 | 同上 |
| 7 | `get_bootstrap_manager()` | [core/__init__.py#L99](file:///Users/oscar/projects/Crawlo/crawlo/core/__init__.py#L99) | 同上 | 同上 |
| 8 | ApplicationContext 36 条 `@property` 委托 | [application.py](file:///Users/oscar/projects/Crawlo/crawlo/core/application.py) | Phase 8 兼容层 → v2.0 物理删除 | `ctx.dingtalk_channel` 抛 AttributeError，必须用 `ctx.notifications.dingtalk_channel` |
| 9 | `ApplicationContext.rebind_to_container()` | [application.py](file:///Users/oscar/projects/Crawlo/crawlo/core/application.py) | Phase 8.2 过渡 → v2.0 物理删除 | `ctx.rebind_to_container` 抛 AttributeError |
| 10 | `utils/encoding_detector.py` 等 7 个旧路径 re-export | utils/ 根目录 | Step 9.3.2 DeprecationWarning → v2.0 物理删除 | 旧路径 import 抛 ModuleNotFoundError |
| 11 | `exceptions.py` / `interfaces.py` 顶层 re-export | crawlo/ 根目录 | Step 9.4 DeprecationWarning → v2.0 物理删除 | 旧路径 import 抛 ModuleNotFoundError |
| 12 | `Scheduler.idle()` / `Processor.idle()` / `QueueManager.empty()` sync 版本 | 各模块 | Phase 1 DeprecationWarning → v2.0 物理删除 | 调用抛 AttributeError |
| 13 | `Scheduler.__len__` 对 Redis 返回 0 | [core/scheduler.py](file:///Users/oscar/projects/Crawlo/crawlo/core/scheduler.py) | Phase 1 → v2.0 抛 TypeError | `len(scheduler)` 抛 TypeError |

#### 9.5.3 v2.0 删除清单守护测试（0.5 天）

新建 `tests/arch/test_v2_deletion_checklist.py`，把上表每条写成可执行的断言（v2.0 分支执行时应该 pass，develop 分支执行时跳过或标记 xfail）。

**验收标准**：
- [ ] `grep -rn "from crawlo.commands.job_executor import" crawlo/scheduling/` = 0
- [ ] `grep -rn "from crawlo.runtime.job_executor import" crawlo/scheduling/` ≥ 1（已迁移）
- [ ] `FRAMEWORK_REFACTOR_PLAN.md` 包含「v2.0 Breaking Change 删除清单」章节，13 条逐条可执行
- [ ] `tests/arch/test_v2_deletion_checklist.py` 在 develop 分支 xfail，在 v2.0 分支 pass

---

### Phase 9 执行顺序与里程碑

```
develop 分支（v1.x）
 ├─ Step 9.1（立即）── P0，用户可见体验改善，0 风险
 ├─ Step 9.2（9.1 之后）── P1，公共 API 收窄 + 模块重命名
 ├─ Step 9.3（与 9.2 并行）── P1，utils 切块，纯文件移动 + facade
 ├─ Step 9.4（9.3 之后）── P2，顶层大文件拆分，改动面大但模式固定
 └─ Step 9.5.1–9.5.2（9.1–9.4 全部完成后）── P2，归档 + 依赖反转

v2.0 分支
 └─ Step 9.5.3 + 物理删除清单 13 条 ── 一次性执行
```

**优先级排序逻辑**：
1. **Step 9.1（P0）**：用户可直接感知（examples 跑得通、grep 不迷惑），收益/成本比最高
2. **Step 9.2（P1）**：公共 API 收窄是 v2.0 前置条件，越早做越早减少别名扩散
3. **Step 9.3（P1）**：utils 切块是纯机械迁移 + facade，风险低但体量大，可与 9.2 并行
4. **Step 9.4（P2）**：顶层文件拆分改动面大，等 9.3 的迁移模式验证后再做
5. **Step 9.5（P2）**：依赖反转 + 删除清单归档是 v2.0 前最后一步，须 9.1–9.4 全部稳定后执行

**风险与缓释**：

| 风险 | 影响 | 缓释 |
|------|------|------|
| utils/ 迁移后循环导入 | import 失败 | 每个子目录迁完后跑 22 模块 reload 验证（Phase 8.8 已建立的验证模式） |
| interfaces.py 拆分后签名基线变化 | 守护测试失败 | 仅拆 ≥ 200 行的大块，小接口留原处；改完后更新 `test_public_api_signatures.py` 基线 |
| JobExecutor 二次迁移（Phase 7 → 9.5.1） | 用户困惑「为什么又改路径」 | release notes 说明：Phase 7 是从 scheduling 上提到 commands，Step 9.5.1 是从 commands 下沉到 runtime，两次改动的动机不同（前者消除反向依赖，后者消除业务层依赖适配层） |
| v2.0 删除清单遗漏 | v2.0 发布时兼容性断裂 | Step 9.5.3 的守护测试在 develop 分支 xfail，每次 CI 跑都会提醒「这些 xfail 在 v2.0 必须 pass」 |
