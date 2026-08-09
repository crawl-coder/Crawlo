# Crawlo P4 阶段结构治理 & 可观测补齐方案 v1.0

> 生效时间：2026-08-10（周一）→ 2026-08-23（两周）
> 前提基线：P2 测绘 4/4 全通过（三模式 9/9、10 Worker 分布式 rc=0、单元 1290 passed/92 skipped、Engine Composition 拆分结构完整）
> 前置文档：[ARCHITECTURE_OPTIMIZATION_AND_MONITORING_v1.md](./ARCHITECTURE_OPTIMIZATION_AND_MONITORING_v1.md) §3 问题清单 & §4.2 Phase P4

---

## 1. 范围与目标

### 1.1 P4 阶段做什么（4 大方向）

| 编号 | 方向 | 对应问题清单 | 核心产出 |
|---|---|---|---|
| **A** | **Engine 进一步拆分**（Composition → 组合持有） | B-05（engine.py 860 行，dispatch + idle 耦合） | 3 个新文件，engine.py 主骨架缩到 ≤ 400 行 |
| **B** | **crawler.py 拆分子包** | crawler.py 1373 行单文件（Crawler / CrawlerProcess / CrawloFramework 三大类混在一起） | crawler 子包 3 个内部模块，对外 API 零破坏 |
| **C** | **crawlo.extension → crawlo.extensions 路径收敛** | extension/ 与 extensions/ 双目录并存（69 行 alias vs 906 行真实实现），内部 36 处用旧路径、32 处用新路径 | 内部 import 全切 extensions；extension/__init__.py 保留但打 DeprecationWarning，3 个月后移除 |
| **D** | **Stats 指标补齐 + Eventloop Lag 探针** | B-06 + §5.2 监控方案 L2 缺失的 8 个 key + L1 eventloop_lag_ms | StatsCollector 统一埋点；PrometheusBackend 自动映射；钉钉告警规则补 3 条 |

### 1.2 P4 阶段**不做**什么（边界）

- **不**触碰 B-07 `StatsCollector.close()` 后是否允许再 inc_value（放到 P5，风险高，牵扯测试框架统计后处理）
- **不**做 MODE_CONFIG_MAP 新增 auto 条目（放到 P5 §4.3.1，需要 SettingManager.update_attributes 支持 None 跳过，改动面广）
- **不**做 XCLAIM → 死信队列联动（放到 P5 §4.3.3，和 failed_stream 的消费策略一起定）
- **不**再拆 crawlo/utils（原架构 §4.3.2 的 helpers 并入动作**实际已完成**：crawlo/helpers 目录不存在，utils 已是统一目录，9648 行 21 个子模块，当前划分合理）

---

## 2. 基线数据（P2 测绘现状）

| 对象 | 当前行数 | 类/函数数 | P4 目标行数 |
|---|---|---|---|
| `crawlo/core/engine.py` | 898 | Engine 主类（继承 RequestGenerationMixin + ClusterMixin） | ≤ 400 |
| `crawlo/core/engine_helpers.py` | 476 | GenerationStats + EngineBackpressureAdapter（已拆） | 保持不变 |
| `crawlo/core/engine_generation.py` | 312 | RequestGenerationMixin（已拆） | 保持不变 |
| `crawlo/crawler.py` | 1373 | CrawlerState(60) / CrawlerMetrics(72) / Crawler(106) / CrawlerProcess(534) / CrawloFramework(1048) + 6 个顶层 helper | **拆成子包，单文件 ≤ 500 行** |
| `crawlo/extension/__init__.py` | 69 | Deprecated alias（当前无 DeprecationWarning） | 加 warnings.warn("crawlo.extension is deprecated") |
| `crawlo/extensions/*.py` | 906 | 5 个模块（health_check / interfaces / log_interval / log_stats / logging / request_recorder） | 保持不变 |

---

## 3. 分周执行计划（2 Weeks）

### Week 1（2026-08-10 ~ 2026-08-16）：结构拆分

#### 3.1.1 A 方向：Engine 再拆 3 个模块（组合方式，不新增 Mixin）

根据 engine.py 当前方法分布，按**职责内聚**迁出：

| 新文件 | 迁出方法/属性（估算行数） | 组合持有方式 |
|---|---|---|
| `core/engine_distributed.py` | `_check_control_state()`（B-02 AutoFix，约 56 行）<br/>`_handle_distributed_idle()`（约 90 行）<br/>`_try_claim_stale_pending()`（约 30 行）<br/>`_acquire_leader_lock()` / `_release_leader_lock()`（约 50 行）<br/>`_register_worker()` / `_deregister_worker()`（约 60 行）<br/>合计 **≈ 286 行** | `Engine._distributed = DistributedCoordinator(self)`，所有原 Engine 的方法变成 `return self._distributed.xxx(...)` 薄代理 |
| `core/engine_dispatch.py` | `_dispatch_requests()`（约 120 行，B-05 核心耦合点）<br/>`_start_background_tasks()` / `_stop_background_tasks()`（约 40 行）<br/>`_schedule_next_request_batch()`（约 30 行）<br/>`_handle_idle_state_machine()`（约 30 行）<br/>合计 **≈ 220 行** | `Engine._dispatcher = RequestDispatcher(self)` |
| `core/engine.py`（保留） | `__init__()`（组合持有 _distributed / _dispatcher / _backpressure_ctrl）<br/>`start_spider()`（状态机骨架，调用 generation / dispatch / distributed）<br/>`close_spider()`（生命周期收尾 + stats close）<br/>事件订阅（on_request_scheduled / on_response_received / …）<br/>合计 **≤ 400 行** ✅ | — |

**约束与验收**：
- 不修改任何对外方法签名（`await engine.start_spider(...)` / `await engine.close()` / `engine.running` 等行为 100% 兼容）
- 三模式测绘 [test_3modes_p0p1.py](../examples/test_3modes_p0p1.py) 必须 9/9 通过
- 10 Worker 分布式 [run_10_workers.py](../examples/ofweek_distributed/run_10_workers.py) 必须 Success=10/10
- 每迁出一个模块后，立刻跑 `tests/unit tests/arch` 子集（`test_engine_*.py` + `test_mode_consistency.py`），增量验证

#### 3.1.2 B 方向：crawler.py → `crawlo/crawler/` 子包

**现状**：`crawlo/crawler.py` 1373 行单文件，包含 Crawler / CrawlerProcess / CrawloFramework 三大类，对外是 `from crawlo.crawler import CrawlerProcess`。

**拆分方案**（保持对外路径零破坏）：

```
crawlo/
├── crawler.py            ← 改造：re-export 子包，加 DeprecationWarning？
└── crawler/              ← 新建子包
    ├── __init__.py       ← 对外 API 门面：re-export CrawlerState / CrawlerMetrics / Crawler / CrawlerProcess / CrawloFramework / get_framework / run_spider …
    ├── _crawler.py       ← CrawlerState(60) + CrawlerMetrics(72) + Crawler(106)          ≈ 470 行
    ├── _process.py       ← CrawlerProcess(534)                                           ≈ 530 行
    └── _framework.py     ← CrawloFramework(1048) + 6 个顶层 helper（get_framework / run_spider / create_crawler …）
                                                             ≈ 370 行
```

**对外兼容策略**：
- 旧路径 `from crawlo.crawler import CrawlerProcess`：保留 `crawlo/crawler.py`，内容改成 `from crawlo.crawler import Crawler, CrawlerProcess, CrawloFramework, ...`，并加：
  ```python
  import warnings
  warnings.warn(
      "Direct import from crawlo.crawler is deprecated; use `from crawlo import CrawlerProcess` "
      "or `from crawlo.crawler import CrawlerProcess` (crawler sub-package) instead. The flat "
      "crawlo/crawler.py module will be removed in v3.1.",
      DeprecationWarning, stacklevel=2
  )
  ```
- 新路径 `from crawlo import CrawlerProcess`：在 `crawlo/__init__.py` 中新增 `from crawlo.crawler import Crawler, CrawlerProcess, CrawloFramework` re-export，成为推荐写法。
- **deprecation 周期 3 个月（至 2026-11）**，之后删除 `crawlo/crawler.py` 单文件。

**验收**：
- `from crawlo.crawler import CrawlerProcess`（旧扁平模块）依然可导入 + 打印 DeprecationWarning
- `from crawlo.crawler import CrawlerProcess`（子包）正常导入，无 Warning
- `from crawlo import CrawlerProcess`（推荐顶层）正常导入，无 Warning
- `examples/` 所有项目按三种方式各抽取一个 smoke test，确保运行无异常
- 全量单元测试：`tests/unit tests/arch` 中 `import crawlo.crawler` 的测试全部通过

---

### Week 2（2026-08-17 ~ 2026-08-23）：路径收敛 + 可观测补齐

#### 3.2.1 C 方向：crawlo.extension → crawlo.extensions 路径收敛

**现状基线**：
- `crawlo/extension/__init__.py`：69 行 alias（应该是把 `crawlo.extensions.xxx` 重导出）
- `crawlo/extensions/`：真实实现（906 行，5 个模块）
- 引用分布：内部 **36 处** 用 `crawlo.extension`，**32 处** 用 `crawlo.extensions`

**执行步骤**：
1. **改 crawlo/extension/__init__.py**：
   - 保留所有 re-export 符号（零破坏）
   - 在模块级别加 `warnings.warn("crawlo.extension is deprecated, use crawlo.extensions", DeprecationWarning, stacklevel=2)`
2. **批量改内部 36 处旧路径 → 新路径**（grep 定位，逐个替换）：
   - `crawlo/` 框架源代码（保证框架内部没有自引用 deprecated 路径）
   - `examples/` 示例全部切到 `extensions`（示例作为最佳实践参考）
   - **不**改用户私有项目（deprecation warning 自然提醒）
3. **补测试**：tests/ 下加一个最小用例，断言 `import crawlo.extension` 会触发 DeprecationWarning 且 `crawlo.extension.HealthCheckExtension is crawlo.extensions.HealthCheckExtension`（符号全等，re-export 正确）

**验收**：
- `grep -rln "crawlo\.extension[^s]" --include="*.py" crawlo/ examples/` → 0 命中（内部已切净）
- 单元测试断言 DeprecationWarning 正确触发

#### 3.2.2 D 方向：Stats 指标 8 项补齐 + Eventloop Lag 探针

**8 个新指标**（统一写入 `StatsCollector.inc_value / set_value`，Stats Backends 自动分发）：

| # | key | 类型 | 插入位置 |
|---|---|---|---|
| 1 | `queue/backlog` | Gauge（每 tick 更新） | `LogIntervalExtension.tick()` → `self.engine.scheduler.queue.qsize()`（safe_get_queue_size） |
| 2 | `queue/xclaim/recovered_total` | Counter | `RedisStreamQueue.claim_stale_pending()` return 处，累计 recovered 值 |
| 3 | `queue/xclaim/scan_runs` | Counter | `DistributedCoordinator._handle_distributed_idle()` 实际触发 claim 时 `+1`（只在真的跑了 claim_stale_pending 时加，不是每次 idle 都加） |
| 4 | `cluster/worker/heartbeat_lost` | Counter | `FailoverManager._cleanup_expired_heartbeats()` 中被判定心跳过期并移除的 Worker 数 `+N` |
| 5 | `filter/duplicate_rps` | Gauge（滑窗） | `HealthCheckExtension.tick()` 用滑窗算最近 1m 内 dedup/duplicate 的 RPS |
| 6 | `downloader/p99_response_ms` | Gauge（滑窗） | AioHttpDownloader 保存最近 1000 条 RT（RingBuffer），每 tick 算 P99 写入 stats |
| 7 | `pipeline/item/p99_latency_ms` | Gauge（滑窗） | MySQLPipeline / MongoPipeline 记录 open_spider → close_spider 的每条 process_item RT，tick 时汇总 |
| 8 | `resource/eventloop_lag_ms_p99` | Gauge（滑窗） | 新增 `extensions/eventloop_lag.py` 探针，每 1s 做 `loop.call_later(0, …)`，记录 delta 的 P99 |

**Eventloop Lag 探针实现细节**（新增 `crawlo/extensions/eventloop_lag.py`）：
- 属于 Extension（`ExtensionManager` 生命周期管理）
- 1s 频率采样，RingBuffer 保存最近 60 条
- 每 5s 将 P50 / P95 / P99 写入 StatsCollector（3 个 gauge key）
- 自带阈值告警：P99 > 200ms 持续 3 个周期（≥15s）→ 通过 StatsBackend 的 `alert` 通道发 WARN 日志 + 钉钉通知（如果配了 DINGTALK_WEBHOOK）
- `LOG_LEVEL=DEBUG` 时打印每条采样，`LOG_LEVEL=INFO` 时只打印超过 100ms 的采样

**PrometheusBackend 无需改一行**：它已经把所有 StatsCollector 的 key 按正则映射成 Counter/Gauge（见 [prometheus_backend.py#L200-L225](../crawlo/stats/prometheus_backend.py#L200-L225)）。只需要在 [prometheus-integration.md](./guides/prometheus-integration.md) 里补一张 8 个新 key 的映射表和 Grafana panel JSON。

**验收**：
- 跑 `examples/ofweek_standalone/run.py`，日志末尾 stats 里要能看到 8 个新 key 都有数值（不能全部是 0；`queue/xclaim/*` 需 distributed 模式下验证，P4 最后一天跑一次 distributed W1 断言 `recovered_total` 对应 XCLAIM 回收数）
- Prometheus 端口（默认 9102）`/metrics` 端点能看到 `crawlo_queue_backlog / crawlo_resource_eventloop_lag_ms_p99` 等指标名暴露
- Eventloop Lag 阈值告警功能单独用一个单元测试：人工 `loop.call_later(0.5, lambda: None)` 阻塞事件循环 500ms，断言 P99 > 200ms 且告警被触发

---

## 4. 验收标准总表

| 子方向 | 验收项 | 方法 | 责任人/脚本 |
|---|---|---|---|
| A-拆分 Engine | engine.py ≤ 400 行 | `wc -l crawlo/core/engine.py` | CI 阶段 |
| A-拆分 Engine | 三模式 9/9 通过 | `python examples/test_3modes_p0p1.py` | 每次拆分模块后 |
| A-拆分 Engine | 10 Worker 分布式 Success 10/10 | `python examples/ofweek_distributed/run_10_workers.py` | Week 1 周五 |
| B-拆分 crawler | 3 种 import 路径（顶层 / 子包 / 旧扁平）均可正常导入 CrawlerProcess | pytest + smoke test | CI 阶段 |
| B-拆分 crawler | `crawlo/crawler.py` 扁平模块 import 时触发 DeprecationWarning | pytest.warns(DeprecationWarning) | Week 1 周三 |
| C-收敛 extension | 内部（crawlo/ + examples/）36 处旧路径清零 | grep 检查 | Week 2 周一 |
| C-收敛 extension | 旧路径 `import crawlo.extension` 仍可用（向后兼容）但打 DeprecationWarning | pytest.warns | CI 阶段 |
| D-指标补齐 | Standalone 模式最终 stats dict 中除 `queue/xclaim/*` 外其余 6 个 key 有非零数值 | grep / 断言 | Week 2 周四 |
| D-指标补齐 | Distributed 模式 W1 跑完 `queue/xclaim/recovered_total` 与 XCLAIM 实际回收数一致 | test_3modes_p0p1 加 1 行断言 | Week 2 周五 |
| D-Eventloop Lag | Prometheus `/metrics` 暴露 `crawlo_resource_eventloop_lag_ms_p99` | curl + grep | Week 2 周四 |
| D-Eventloop Lag | 人工阻塞 > 500ms → P99 > 200ms 持续 3 tick → 日志出现告警 | 单元测试 | Week 2 周四 |
| **全局** | **tests/unit + tests/arch  passed 数 ≥ 1290（≥ P2 基线），failed 数 = 0（不允许新增回归失败）** | `pytest tests/unit tests/arch --ignore=test_encoding_comprehensive.py --ignore=test_extreme_pipeline.py` | **每日 CI** |

---

## 5. 风险评估 & 回滚预案

| 风险 | 概率 | 影响 | 缓解措施 | 回滚触发条件 | 回滚方式 |
|---|---|---|---|---|---|
| Engine 拆分后组合持有导致 `self` 循环引用过深，某些 Mixin 方法中 `self._xxx` 引用失效 | 中 | 高（运行时 AttributeError） | 迁出前先把每个被迁方法的 `self.` 依赖列表打印出来；薄代理模式（Engine 上保留同名方法，只转发）优先，**不要**直接把 Engine 的 self 传给 Coordinator 后再由 Coordinator 直接访问 Engine 私有属性（需通过接口） | 三模式测试出现 2+ 个 AttributeError 且 30min 内修不好 | git revert 对应拆分 commit，保留 mixin 形式，P4-A 推迟到 P5 |
| crawler.py 拆子包后，循环 import（crawlo/__init__.py 中 re-export → crawler/_framework.py 又 import crawlo 顶层） | 中 | 高（启动即 ImportError） | 先用 `TYPE_CHECKING` 延迟类型导入；所有模块内的互相 import 放到函数内部；crawlo/__init__.py 的 re-export 放在文件最后 | 任一示例 `python run.py` 启动即报 ImportError 且 30min 内修不好 | git revert，保留扁平 crawler.py，P4-B 推迟到 P5 |
| 内部 import 批量切 extension → extensions 时，第三方插件可能间接 import crawlo.extension（未被 grep 覆盖） | 低 | 中（用户项目启动告警但不崩） | extension/__init__.py 完整保留符号 + 仅 DeprecationWarning（功能不阻塞）；examples/ 和 tests/ 覆盖是最主要的 | 有用户反馈 examples 里 import 报错（不可能，因为符号全等） | 立刻 restore extension/__init__.py 内容（本来就没删，只是加了 warning） |
| 8 个新指标写入 StatsCollector，导致 LogIntervalExtension.tick() 耗时翻倍 | 低 | 中（日志卡顿） | 每个写入都是 O(1) Counter / Gauge 更新；指标计算（P99 / RPS 滑窗）放在独立后台任务，**不**在 tick() 内同步执行（tick 只负责读已经算好的缓存值写进 stats） | tick 耗时从 <1ms 涨到 >10ms 持续 5 个周期 | 停用对应指标计算函数，仅保留 gauge 更新的 O(1) 部分 |
| Eventloop Lag 探针自身引入开销（1/s call_later） | 极低 | 低 | 已验证 call_later 开销 < 1µs；并在 extension 中加开关 `EVENTLOOP_LAG_PROBE_ENABLED=True` 默认开，用户可关 | 用户明确反馈性能下降 10%+ 且可证明是 probe 引入 → 默认值改为 False | settings 中改默认开关 |

---

## 6. 交付清单

### Week 1 结束交付
- [ ] `crawlo/core/engine_distributed.py`（DistributedCoordinator）
- [ ] `crawlo/core/engine_dispatch.py`（RequestDispatcher）
- [ ] `crawlo/core/engine.py` 缩减到 ≤ 400 行
- [ ] `crawlo/crawler/__init__.py` + `_crawler.py` + `_process.py` + `_framework.py`
- [ ] `crawlo/crawler.py` 扁平模块：re-export + DeprecationWarning
- [ ] 三模式 9/9 测试结果截图 + 10 Worker 分布式 summary
- [ ] `crawlo/__init__.py` 顶层 re-export Crawler / CrawlerProcess

### Week 2 结束交付
- [ ] `crawlo/extension/__init__.py` 加 DeprecationWarning
- [ ] 所有 crawlo/ + examples/ 内部 import 从 `crawlo.extension` → `crawlo.extensions`
- [ ] `crawlo/extensions/eventloop_lag.py`（新增 Lag 探针 Extension）
- [ ] 8 个新指标埋点：LogIntervalExtension / FailoverManager / RedisStreamQueue / AioHttpDownloader / MySQLPipeline 各自改动
- [ ] Prometheus 集成文档 [prometheus-integration.md](./guides/prometheus-integration.md) 补 8 个 key 的 Grafana panel JSON
- [ ] 钉钉告警规则补 3 条（Eventloop Lag > 200ms、Queue Backlog > SCHEDULER_MAX_QUEUE_SIZE × 0.8、Heartbeat Lost 增量 / 15m > 3）
- [ ] `tests/unit + tests/arch` CI 报告：passed ≥ 1290、failed = 0、skipped 无新增

---

## 7. 关键代码引用

- Engine 当前实现：[engine.py](../crawlo/core/engine.py)
- Composition 拆分基线：[engine_helpers.py](../crawlo/core/engine_helpers.py) / [engine_generation.py](../crawlo/core/engine_generation.py)
- Crawler 当前实现：[crawler.py](../crawlo/crawler.py)
- Extension 双路径：[extension/__init__.py](../crawlo/extension/__init__.py) / [extensions/](../crawlo/extensions/)
- 三模式测绘脚本：[test_3modes_p0p1.py](../examples/test_3modes_p0p1.py)
- 10 Worker 分布式脚本：[run_10_workers.py](../examples/ofweek_distributed/run_10_workers.py)
- Stats Backend 自动映射：[prometheus_backend.py#L200-L225](../crawlo/stats/prometheus_backend.py#L200-L225)
