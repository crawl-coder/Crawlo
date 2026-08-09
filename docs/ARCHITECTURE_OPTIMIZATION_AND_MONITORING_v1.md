# Crawlo 架构优化建议与生产监控方案 v1.0

> **文档版本**：v1.0
> **日期**：2026-08-09
> **适用阶段**：P0（主动 XCLAIM 回收）→ P1（Engine Composition 拆分）→ P2（三模式测绘）全部通过后，面向生产的下一步改进

---

## 目录

1. [执行摘要（1 分钟版）](#1-执行摘要1-分钟版)
2. [当前架构基线（基于 P0→P1→P2 实跑测绘）](#2-当前架构基线基于-p0p1p2-实跑测绘)
3. [问题分级清单：P0/P1/P2](#3-问题分级清单p0p1p2)
4. [架构优化方案（按阶段落地）](#4-架构优化方案按阶段落地)
   - 4.1 Phase P3：稳定性 & 可运维（1 周）
   - 4.2 Phase P4：性能 & 可观测（2 周）
   - 4.3 Phase P5：扩展性 & 结构治理（3 周）
5. [生产监控方案（Prometheus + Grafana + Alertmanager + 钉钉）](#5-生产监控方案prometheus--grafana--alertmanager--钉钉)
   - 5.1 指标分层与最小全集
   - 5.2 指标实现路径（基于现有 StatsCollector / PrometheusBackend）
   - 5.3 Grafana Dashboard 推荐布局
   - 5.4 告警规则（SLO 驱动）
   - 5.5 分布式模式下 Worker / Failover / 集群级监控
6. [健康检查与探活方案](#6-健康检查与探活方案)
7. [三模式配置一致性检查清单（上线前必查）](#7-三模式配置一致性检查清单上线前必查)
8. [风险与回滚策略](#8-风险与回滚策略)
9. [附录：关键代码引用](#9-附录关键代码引用)

---

## 1. 执行摘要（1 分钟版）

### 已完成的测绘基线（2026-08-09 实跑）

| 模式 | 队列/去重 | 典型耗时（2 列表页+42 详情页） | 关键验证点 |
|---|---|---|---|
| **Standalone** | Memory Queue + MemoryFilter | 10.3s | finished / 2 list + 42 item / 无外部依赖 |
| **Auto** | Redis ZSET + **AioRedisFilter**（刚修复） | R1=6.7s / **R2=1.4s** | R2 详情页 42/42 被 RedisFilter 过滤，idle 快速退出 |
| **Distributed** | Redis Stream (Consumer Group) + AioRedisFilter | 67.5s (单 Worker) | Stream / 种子锁 / Worker 注册 / XAUTOCLAIM / finished |
| **P0 XCLAIM 单元** | claim_stale_pending(5s,count=50) | 6s wait + <1s 回收 | **pending=5→0，回收 5/5** |

### 必须马上做的 3 件事（P3 本周）

1. **Auto 模式去重 Bug 已修**（[factories.py](file:///Users/oscar/projects/Crawlo/crawlo/core/config/factories.py#L87-L132) + [_old_factories.py](file:///Users/oscar/projects/Crawlo/crawlo/core/config/_old_factories.py#L90-L130)），请合并到主线 — 否则所有 `CrawloConfig.auto()` 用户在重跑/断点续爬时都会被"去重不生效"坑到。
2. **Persistent shutdown 状态保护**：Distributed 模式下 `control:state = shutdown` 一旦残留就会导致下次启动 **0 请求立即退出**（本次测绘中首次复现）。加一个 `CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START = True` 默认开关。
3. **Stats key 前缀统一**：当前 MemoryStatsBackend 把 key 存为 `crawlo:request_scheduler_count`，但文档和用户直觉是 `request_scheduler_count`。对外暴露 API 时做前缀兼容（`StatsCollector.__getitem__` 目前已支持，但 `get_stats()` 仍返回带前缀版本）。

### 中期目标（1 个月内）

- 所有指标经 PrometheusBackend 暴露 → Grafana Dashboard 统一视图
- 分布式 Worker / FailoverManager / XCLAIM 的三项 SLO 告警落到钉钉 / 飞书
- Engine 继续按 Composition 原则拆分：`engine.py` 从 ~860 行 → <500 行（把 `_dispatch_requests` / `_handle_distributed_idle` 再拆成 mixin）

---

## 2. 当前架构基线（基于 P0→P1→P2 实跑测绘）

### 2.1 三模式运行路径（简化）

```
CrawloConfig.standalone()  → MODE_CONFIG_MAP['standalone']
                            ├─ QUEUE_TYPE = memory
                            ├─ FILTER_CLASS = MemoryFilter
                            └─ DEDUP_PIPELINE = MemoryDedupPipeline

CrawloConfig.auto()        ┌─ Redis Ping OK ?
                            │  YES → QUEUE_TYPE = redis(ZSET)   ← QueueManager._determine_queue_type()
                            │        FILTER_CLASS = AioRedisFilter  ← P3 Bug 修复点
                            │        DEDUP_PIPELINE = RedisDedupPipeline
                            │  NO  → fallback 到 standalone 全套
                            └─ start_requests dont_filter=True 的种子在 R2 仍是新增

CrawloConfig.distributed() → QUEUE_TYPE = redis_stream (强制)
                            ├─ FILTER_CLASS = AioRedisFilter
                            ├─ DEDUP_PIPELINE = RedisDedupPipeline
                            ├─ ClusterMixin: Leader 选举 + 种子锁
                            ├─ FailoverManager: 心跳探测 → 清理死亡 Worker pending
                            └─ Engine._handle_distributed_idle: 主动 XCLAIM 扫描（P0 新增）
```

### 2.2 P0 主动 XCLAIM 回收双保险机制

| 层级 | 触发方 | 扫描对象 | 阈值 | 入口 |
|---|---|---|---|---|
| L1 被动 | **FailoverManager** 心跳线程 | 心跳过期的 Worker（deadline 之前） | `failover_interval`(30s 级) | [failover.py](file:///Users/oscar/projects/Crawlo/crawlo/cluster/failover.py#L30) `_try_recover_dead_workers()` |
| L2 主动 | Engine idle 循环 | 所有 pending idle > `min_idle_sec` 的消息 | `DISTRIBUTED_IDLE_XCLAIM_SCAN_INTERVAL`(默认 3s) | [engine.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine.py) `_handle_distributed_idle()` → `_try_claim_stale_pending()` → `RedisStreamQueue.claim_stale_pending()` |

P0 测绘结果（注入 5 条 stale pending）：
```
♻️ claim_stale_pending(min_idle=5s) → 回收 5 条
📋 pending_info: {total: 5} → {total: 0}
```

### 2.3 P1 Engine Composition 拆分现状

| 文件 | 职责 | 行数（约） |
|---|---|---|
| [engine.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine.py) | 主循环 + distributed idle + 状态机 + close_spider | ~860 |
| [engine_helpers.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine_helpers.py) | EngineBackpressureAdapter + resolve_start_requests + safe_queue_size | ~420 |
| [engine_generation.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine_generation.py) | RequestGenerationMixin（start_requests → 调度） | ~350 |

**评价**：方向正确（拆分 vs. 单一 2000 行巨兽），但仍有进一步拆分空间（见 4.3）。

---

## 3. 问题分级清单：P0/P1/P2

> P0=线上事故级，P1=生产稳定性，P2=可维护性/扩展性

| 编号 | 级别 | 问题 | 现象 | 影响面 | 建议修复阶段 |
|---|---|---|---|---|---|
| **B-01** | ~~P0~~ **已修复** | Auto 模式误用 MemoryFilter（已在 [factories.py `_make_auto`](file:///Users/oscar/projects/Crawlo/crawlo/core/config/factories.py#L87-L132) 修复） | R2 重跑仍然请求 44 条，无法断点续爬 | 所有 auto 模式用户 | P3 合并到主线 |
| **B-02** | P1 | Distributed `control:state = shutdown` 残留导致重启即退出 | 本次测绘中 distributed 首次复现（0 req / 2.6s exit） | 异常退出后手动重启的全部 Worker | P3 |
| **B-03** | P1 | `STREAM_CONSUMER_IDLE_TIMEOUT` 默认 60s 太长 vs XCLAIM min_idle 默认 600s 不匹配 | 崩溃 Worker 的任务最长 10 分钟才被动回收 | 线上 Worker OOM/Kill 场景 | P3 |
| **B-04** | P1 | Stats key 前缀不一致（`crawlo:x` vs 裸 key） | 用户 `stats.get_stats()` 返回带前缀，但文档/直觉无前缀 | 所有外部集成监控接入 | P3 |
| **B-05** | P2 | Engine 仍有 ~860 行，`_dispatch_requests` + idle 处理耦合 | 新功能加入时容易回归 | 维护者学习曲线 | P4 |
| **B-06** | P2 | 单 Worker distributed idle timeout 默认 300s 太长 | 队列空了 5 分钟才退出（本次单 W1 用 67.5s 是因为所有请求处理完后走的 finished 路径，非 idle 退出） | 资源浪费 / 弹性伸缩 | P4 |
| **B-07** | P2 | `close_spider → StatsCollector.close()` 后 `get_stats()` 返回可用，但 `_closed=True` 后外部无法再 inc_value | 集成测试/后处理统计受限 | 测试 & 二次开发 | P5 |
| **B-08** | P2 | 三模式 QueueManager 日志缺少 `dedup_class` / `dedup_pipeline` 打印 | 切换模式后不清楚到底用的是什么去重 | 线上排查成本 | P3（低复杂度） |

---

## 4. 架构优化方案（按阶段落地）

### 4.1 Phase P3：稳定性 & 可运维（1 周）

#### 4.1.1 分布式 Shutdown 状态保护（B-02）

**问题**：`DynamicConfig.shutdown_cluster()` 把 `{ns}:control:state` 持久化设为 `shutdown`，`_cleanup_run_data()` 失败或被跳过时，下次启动所有 Worker `_check_control_state()` 读到此值立即退出。

**方案**（3 选 1，推荐方案 B）：

| 方案 | 实现 | 优点 | 缺点 |
|---|---|---|---|
| A. TTL 化 `control:state` | `SET control:state shutdown EX 600` | 自动恢复，10 分钟后自愈 | 长停机场景可能误自愈 |
| B. 启动自动清除 + 告警 | 新增 `CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START=True`，第 1 个注册的 Worker 若看到 `state=shutdown` 且 `registry` 为空 → DELETE key 并 WARN 日志 + 通知 | 安全（空集群才清）、显式 | 略多代码 |
| C. CLI 子命令 `crawlo cluster reset` | 强制 `DEL control:state` + `DEL leader` | 运维可控 | 需要人记得执行 |

**推荐组合**：B（默认）+ C（兜底）。

#### 4.1.2 Stream XCLAIM 超时参数默认值对齐（B-03）

当前默认值：
```python
STREAM_CONSUMER_IDLE_TIMEOUT = 60_000        # 60s (Redis 认为 consumer 可回收)
DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE = 600       # 600s (主动扫描阈值)
DISTRIBUTED_WORKER_FAILOVER_INTERVAL = 30    # 30s (心跳扫描)
```
**不一致点**：任务真正超时 10 分钟才被主动 claim，但 Redis 侧 1 分钟就认为 consumer idle。

**建议**（默认即可，保留用户可调）：
```python
STREAM_CONSUMER_IDLE_TIMEOUT = 90_000              # 1.5 分钟，给慢请求留余量
DISTRIBUTED_IDLE_XCLAIM_MIN_IDLE = 120             # 2 分钟（= 1.5 * STREAM_CONSUMER_IDLE_TIMEOUT / 1000）
DISTRIBUTED_FAILOVER_INTERVAL = 15                 # 15s，死 Worker 更快被发现
STREAM_DELIVERY_COUNT_LIMIT = 5                    # 从 3→5，网络抖动时不要太快进死信
```

#### 4.1.3 QueueManager 启动日志补 dedup 信息（B-08）

在 [queue_manager.py](file:///Users/oscar/projects/Crawlo/crawlo/queue/queue_manager.py) 初始化完成处，追加打印：
```
[QueueManager] Queue type: redis (auto-detected, Redis available, ZSET queue)
[QueueManager] Dedup filter:  crawlo.filters.AioRedisFilter   (Redis-backed, persistence=ON)
[QueueManager] Dedup pipeline: crawlo.pipelines.RedisDedupPipeline
```
让排障时 2 行就能确认三模式配置实际生效了。

#### 4.1.4 Auto 模式单元测试加"去重生效"断言

把本次 test_3modes_p0p1.py 中 Auto R1/R2 的用例抽 1 个进 `tests/`，断言：
```python
assert r1['requests'] == 44
assert r2['requests'] == 2  # 仅 dont_filter=True 的 start_requests
assert r2['elapsed'] < r1['elapsed'] * 0.3
```

---

### 4.2 Phase P4：性能 & 可观测（2 周）

#### 4.2.1 Engine 进一步拆分

Engine.py 当前 ~860 行，继续拆分：

| 新文件 | 迁出内容 | 目标行数 |
|---|---|---|
| `engine_distributed.py` | `_check_control_state` / `_handle_distributed_idle` / `_try_claim_stale_pending` / Leader 选举相关 | ~280 |
| `engine_dispatch.py` | `_dispatch_requests` / 请求产生的派发循环 / `_background_tasks` 管理 | ~220 |
| `engine.py`（保留） | 主 `start_spider()` 状态机骨架 + 事件订阅 + close_spider | ~360 |

保持 Composition 方式：`Engine` 在 `__init__` 里组合持有 `_distributed` / `_dispatch`，不搞继承。

#### 4.2.2 性能指标补齐（目前 stats 缺的关键项）

当前 `request_scheduler_count / response_received_count / item_successful_count` 已存在，但以下关键指标缺失（需要在 StatsCollector 中补 inc_value 调用点）：

| 指标 key（建议） | 类型 | 语义 | 采集点 |
|---|---|---|---|
| `queue/backlog` | Gauge, per tick | 主队列积压深度 | `LogIntervalExtension.tick()` → `safe_queue_size(scheduler)` |
| `queue/xclaim/recovered_total` | Counter | 累计 XCLAIM 回收任务数 | `RedisStreamQueue.claim_stale_pending()` return 处 |
| `queue/xclaim/scan_runs` | Counter | 主动扫描执行次数 | `_handle_distributed_idle` 真的触发 claim 时 |
| `cluster/worker/heartbeat_lost` | Counter | Failover 判定心跳丢失的 Worker 数 | `FailoverManager._cleanup_expired_heartbeats()` |
| `filter/duplicate_rps` | Gauge | 最近 1m 重复请求速率 | HealthCheckExtension 计算滑窗 |
| `downloader/p99_response_ms` | Gauge | P99 响应时间（滑窗） | AioHttpDownloader 记录原始 RT，tick 时算分位 |
| `pipeline/item/p99_latency_ms` | Gauge | Pipeline P99 入库耗时 | MySQLPipeline / MongoPipeline 原始 RT |
| `resource/eventloop_lag_ms` | Gauge | 事件循环阻塞程度 | 后台 `call_later(0)` 对时 1/s |

> 注意：所有新 key 统一写入 StatsCollector，由 MemoryStatsBackend / RedisStatsBackend / **PrometheusBackend** 三者自动共享，无需在三个 backend 重复写。PrometheusBackend 已经把所有 key 映射成 gauge/counter，见 [prometheus_backend.py](file:///Users/oscar/projects/Crawlo/crawlo/stats/prometheus_backend.py#L200-L225)。

#### 4.2.3 事件循环 lag 监控（Python 异步系统的核心探针）

新建 `crawlo/extensions/eventloop_lag.py`，每 1s 做一次：
```python
t0 = loop.time()
loop.call_later(0, lambda: self._record(loop.time() - t0))
```
把 `max/avg lag` 记录到 stats，**这是判断"异步池被阻塞"的唯一可靠信号**，比 CPU% 还敏感。当 lag > 200ms 持续 3 个 tick 就告警。

---

### 4.3 Phase P5：扩展性 & 结构治理（3 周）

#### 4.3.1 `MODE_CONFIG_MAP` 增加 `auto` 条目（P2 结构性问题）

当前 [base.py](file:///Users/oscar/projects/Crawlo/crawlo/core/config/base.py#L33-L51) MODE_CONFIG_MAP 只有 standalone/distributed，导致 auto 必须"继承 standalone 再覆盖"，极易出现**继承了不该继承的东西**（比如这次 FILTER_CLASS=MemoryFilter 就是这个问题）。

```python
MODE_CONFIG_MAP = {
    'standalone':  { ... },
    'distributed': { ... },
    # P5 新增：auto 作为一等模式显式定义
    'auto': {
        'RUN_MODE': 'auto',
        'QUEUE_TYPE': 'auto',
        # Filter/Dedup 在 _make_auto 运行期按 Redis 可用性动态决定，
        # 这里放"运行期决定前"的中性默认：
        'FILTER_CLASS': None,            # None 表示由 factories.py 动态填
        'DEFAULT_DEDUP_PIPELINE': None,
    },
}
```

> 配套在 `SettingManager.update_attributes()` 中加规则：值为 None 的 key 跳过覆盖旧值。

#### 4.3.2 顶层包结构收敛（和 docs/RESTRUCTURE_PLAN.md 对齐）

现有 27 个子包，参考 RESTRUCTURE_PLAN.md Phase1~3。本项目目前最优先做两件"轻但收益大"的事：

1. **`extension/` 与 `extensions/` 二选一**（当前重复存在）。建议把 `crawlo/extension/` 作为 deprecated alias，所有内部 import 统一切到 `crawlo/extensions/`。
2. **`helpers/` 并入 `core/helpers.py` + `utils/` 分层**：helpers 目录 9 个文件 2336 行，和 utils 的边界彻底模糊。把"仅框架内部用"的全部收敛到 `core/_internals/`，对外 API 保留在 `utils/`。

#### 4.3.3 XCLAIM 指标/死信队列联动

P0 已实现的 `claim_stale_pending` 只有整体 `recovered` 计数，建议：
- 回收任务时把 `retry_count >= STREAM_DELIVERY_COUNT_LIMIT` 的任务显式写进 `stream:failed`（现在已有 `_failed_stream`，确认被喂满）
- 暴露 `queue/dead_letter/total` counter + `queue/dead_letter/backlog` gauge
- 告警：死信 15m 增量 > 10 条 **必告警**（说明系统性失败：站点改版 / 代理挂 / 下载器崩）

---

## 5. 生产监控方案（Prometheus + Grafana + Alertmanager + 钉钉）

> Crawlo **原生支持** Prometheus：仅需在 settings.py 中 `STATS_BACKEND = 'prometheus'` 即可启动指标端口。详细入门见 [prometheus-integration.md](file:///Users/oscar/projects/Crawlo/docs/guides/prometheus-integration.md)。

### 5.1 指标分层与最小全集

分层原则：**系统层**（主机/进程）→ **框架层**（调度/下载/队列）→ **业务层**（item 产出/错误）。

#### L1：主机 & 进程（由 Node Exporter / cAdvisor 出，Crawlo 只补进程内专用）

| 指标（Crawlo 侧补充） | 类型 | labels |
|---|---|---|
| `crawlo_process_cpu_percent` | Gauge | spider, worker_id |
| `crawlo_process_memory_rss_mb` | Gauge | spider, worker_id |
| `crawlo_eventloop_lag_ms_p99` | Gauge | spider, worker_id |
| `crawlo_open_connections`（aiohttp） | Gauge | spider, worker_id |

> 注：cpu/memory/open_conn 已在 [performance_monitor.py](file:///Users/oscar/projects/Crawlo/crawlo/extensions/monitor/performance_monitor.py#L28-L136) 里有完整实现，需要 bridge 进 PrometheusBackend（当前只打日志不进 stats，这是 P4 的 1 小时小任务）。

#### L2：框架层（队列 + 调度 + 下载 + 分布式协调）

| 指标 | 类型 | labels | 当前已有？ |
|---|---|---|---|
| `crawlo_request_scheduler_count_total` | Counter | spider, worker_id | ✅ stats key 已有 |
| `crawlo_response_received_count_total` | Counter | spider, worker_id, status_code | ✅ key 已有，label 需补 status 分拆 |
| `crawlo_queue_depth` | Gauge | spider, worker_id, stream(high/low/main) | ❌ P4 补 LogInterval tick |
| `crawlo_pending_total` | Gauge | spider, stream | ❌ P4，`RedisStreamQueue.pending_info()` → gauge |
| `crawlo_xclaim_recovered_total` | Counter | spider, worker_id, reason(heartbeat / idle-scan) | ❌ P4 双路触发 |
| `crawlo_download_p99_ms` | Gauge | spider, worker_id, domain | ❌ P4 补 AioHttpDownloader |
| `crawlo_download_timeout_total` | Counter | spider, worker_id, domain | ✅ RetryMiddleware 已有 stats key |
| `crawlo_cluster_alive_workers` | Gauge | spider | ❌ P4，WorkerRegistry.length |
| `crawlo_cluster_heartbeat_lost_total` | Counter | spider | ❌ P4，FailoverManager |
| `crawlo_filter_duplicate_total` | Counter | spider, worker_id | ✅ AioRedisFilter 已有分拆 key |

#### L3：业务层（产出 & 质量）

| 指标 | 类型 | labels |
|---|---|---|
| `crawlo_item_successful_count_total` | Counter | spider, worker_id, pipeline |
| `crawlo_item_failed_count_total` | Counter | spider, worker_id, pipeline, error_type |
| `crawlo_item_p99_latency_ms` | Gauge | spider, pipeline(MySQL/ES/Mongo) |
| `crawlo_dead_letter_total` | Counter | spider |
| `crawlo_dead_letter_backlog` | Gauge | spider |

### 5.2 指标实现路径

```
StatsCollector.inc_value(key, val)
    ├─  MemoryStatsBackend._stats[key] += val        （当前默认 ✓）
    ├─  RedisStatsBackend.hincrby(key, val)           （分布式模式 ✓）
    └─  PrometheusBackend
         ├─ Counter = crawlo_{snake(key)}_total       （已有自动映射 ✓）
         └─ Gauge   = crawlo_{snake(key)}              （已有自动映射 ✓）
```

**最小改造清单（P4 1~2 天）**：

1. 在 `LogIntervalExtension.tick()` 中把 `safe_queue_size(self.crawler.engine.scheduler)` 写入 stats，key = `queue/backlog`
2. `RedisStreamQueue.put / XADD` 时顺手更新 `stream:xlen` gauge（用 tick 的近似值也行，成本更低）
3. FailoverManager 把 heartbeat lost 数 → `cluster/heartbeat_lost_total` inc
4. Engine._handle_distributed_idle claim 成功时 → `cluster/xclaim/recovered_total{reason=idle_scan}` inc
5. FailoverManager._try_recover_dead_workers claim 成功时 → `cluster/xclaim/recovered_total{reason=heartbeat_failover}` inc
6. `extensions/monitor/performance_monitor.py` 的 `get_system_metrics()` 返回值 loop 内塞一份进 StatsCollector.set_value

### 5.3 Grafana Dashboard 推荐布局（单页 5 行）

**Row 1 - 全局总览（Site Reliability 视角）**
- 存活 Worker 数（单值面板）：cluster_alive_workers
- **SLO 1 - 产出速率（item/min）**：TimeSeries `rate(item_successful_count_total[1m]) * 60`
- **SLO 2 - 页面成功率**：Gauge `sum(rate(response_status_2xx)) / sum(rate(response_received))`，阈值绿 ≥0.98 黄 0.95 红 <0.9

**Row 2 - 请求与队列**
- 入队 QPS vs. 响应 QPS（对比图，看是否背压或堵塞）
- 队列深度（按 stream 分色：main / high priority）
- Pending 消息数（Stream 特有，>200 时要注意）

**Row 3 - 下载器健康**
- P50 / P95 / P99 响应时间（3 条线）
- 超时率 / 重试率（堆叠面积图）
- aiohttp 连接池使用率（已开连接 / 上限）

**Row 4 - 分布式 & 故障恢复**
- XCLAIM 回收速率（按 reason 分色：心跳 vs idle 扫描）
- 心跳丢失 Worker 事件（bars + annotation）
- 死信增量 / 积压

**Row 5 - 资源 & 框架健康**
- 每 Worker RSS 内存（lines，>1.5GB 要考虑内存泄漏）
- 事件循环 lag P99（阈值线：200ms）
- MySQL Pipeline P99 入库耗时

> **Grafana 变量**：`$spider (All / specific)`、`$worker_id (All / specific)`、`$run_mode (standalone / auto / distributed)`、`$queue_depth_threshold (default 200)`。

### 5.4 告警规则（SLO 驱动，最小必需 9 条）

> Alertmanager 路由：`severity=critical → 钉钉 @ 值班人`，`warning → 钉钉群消息`，`info → IM / 邮件`。

| 告警 ID | 级别 | 表达式（PromQL） | 持续 | 处理 Runbook |
|---|---|---|---|---|
| CRAWL-01 | P0 Critical | `sum(rate(crawlo_item_successful_count_total[5m])) == 0` AND `crawlo_cluster_alive_workers > 0` | 5m | 零产出：看下载器 error、站点可达性、队列 depth=0？ |
| CRAWL-02 | Critical | `1 - (sum(rate(crawlo_response_status_2xx[5m])) / sum(rate(crawlo_response_received_count_total[5m]))) > 0.1` | 5m | 成功率 < 90%：检查代理、Cloudflare、验证码 |
| CRAWL-03 | Critical | `crawlo_cluster_alive_workers < 1` AND `crawlo_queue_depth > 0` | 2m | 有积压但 0 Worker，拉起 Worker K8s deployment |
| CRAWL-04 | Warning | `crawlo_eventloop_lag_ms_p99 > 200` | 3m | 事件循环被阻塞：查 CPU / 同步 IO / 大 Pipeline 批量 |
| CRAWL-05 | Warning | `crawlo_queue_depth > 10000` | 5m | 队列积压超阈值：扩容 Worker / 检查下游消费 |
| CRAWL-06 | Warning | `rate(crawlo_xclaim_recovered_total[15m]) > 0` AND `cluster_heartbeat_lost > 0` | 1m | Worker 真的挂了：翻对应 Worker stderr / dmesg OOM |
| CRAWL-07 | Warning | `rate(crawlo_dead_letter_total[15m]) > 10` | 1m | 死信潮：站点改版 / 解析器崩溃，抽样读 `stream:failed` payload |
| CRAWL-08 | Warning | `crawlo_process_memory_rss_mb > 3072`（可配置） | 10m | 疑似内存泄漏：heap profile / 检查 Request meta 是否无限膨胀 |
| CRAWL-09 | Info | `reason = finished`（spider 维度 gauge） | 0m | 爬虫正常结束：通知"X 任务完成，N 条数据入库" |

> **钉钉 Webhook 接入**：框架已原生支持 [notification-guide.md](file:///Users/oscar/projects/Crawlo/docs/guides/notification-guide.md) + DingtalkChannel。Alertmanager webhook → 钉钉 / 飞书只要写 1 个 50 行转发服务（或直接用 prometheus-webhook-dingtalk 开源组件）。

### 5.5 分布式模式下专项监控

#### 5.5.1 Worker 级别（每实例）

```
┌─────────────────────────────────────────────────┐
│ Worker 级监控面板（1 面板 × N Worker 下拉）       │
│  ├─ 本机 P99 RT / 超时率 / 重试率                │
│  ├─ 认领 pending（按 XPENDING 本 consumer）       │
│  ├─ Leader? 是 / 否（种子锁 gauge）               │
│  ├─ 最近一次 claim_stale_pending 扫描结果          │
│  └─ 最近 100 条日志 ERROR（Loki 关联）            │
└─────────────────────────────────────────────────┘
```

#### 5.5.2 FailoverManager 专项

FailoverManager 内部循环 tick 时暴露：
- `failover/last_scan_at`（timestamp gauge）— 用于判定"Failover 线程挂了吗"，**如果 last_scan_at 距今 > 5min → Critical CRAWL-10**
- `failover/dead_workers_seen`（counter）— 单次扫描发现几个死亡 Worker

#### 5.5.3 集群级

- `cluster:seed_count` gauge（初始种子 URL 数，`{ns}:config:seed_urls` 长度）
- `cluster:progress/items_vs_expected` 用 Redis 集合做"预期 URL 数"对比时给出完成百分比 gauge

---

## 6. 健康检查与探活方案

框架已有 [HealthCheckExtension](file:///Users/oscar/projects/Crawlo/crawlo/extensions/health_check.py#L15-L50)（默认开启）。建议加 2 个 HTTP 探活端点：

### 6.1 端点规范（Prometheus 同一端口复用）

| 端点 | 语义 | HTTP 200 条件 | HTTP 503 条件 |
|---|---|---|---|
| `GET /healthz/liveness` | 进程活着 & 事件循环没卡死 | `eventloop_lag_p99 < 1000ms` 且 `stats.crawlo:start_time != None` | 事件循环卡死 / stats 从未初始化 |
| `GET /healthz/readiness` | 可接收任务（Distributed：已入组） | 队列已连接 & filter/pipeline 已连接 & Stream 已 join group | Redis 断连 / MySQL 断连 / 不在 Consumer Group |
| `GET /healthz/detail` | 详细 JSON 诊断 | 永远 200，返回结构化状态 | N/A |

detail 返回 JSON 推荐字段：
```json
{
  "spider": "ofweek_2page",
  "worker_id": "W1_map",
  "run_mode": "distributed",
  "uptime_s": 48.3,
  "queue": {"backend": "redis_stream", "depth": 0, "pending": 0},
  "filter": {"class": "AioRedisFilter", "dup_last_min": 0},
  "dedup_pipeline": "RedisDedupPipeline",
  "downloader": {"open_conns": 4, "p99_ms": 412},
  "cluster": {"alive_workers": 1, "is_leader": true, "control_state": "running"},
  "stats_latest": {"req_ps": 3.1, "resp_ps": 3.0, "item_ps": 2.9, "err_ps": 0.0}
}
```

### 6.2 K8s/K8s-less 探针

- K8s Deployment：`livenessProbe` → `/healthz/liveness`，`readinessProbe` → `/healthz/readiness`
- systemd/supervisord：cron 每 15s curl 一次 `/healthz/readiness`，非 200 重启进程 + 发钉钉

---

## 7. 三模式配置一致性检查清单（上线前必查）

每次上线新 Spider 之前，对照打勾：

### 通用（必做）

- [ ] `STATS_BACKEND='prometheus'` & `PROMETHEUS_METRICS_PORT` 已设置
- [ ] `NOTIFICATION_ENABLED=True` + 钉钉机器人关键词/签名正确
- [ ] 日志轮转：`LOG_FILE` 使用带时间戳路径（已有默认），磁盘占用监控接入 Node Exporter
- [ ] 超时：`DOWNLOAD_TIMEOUT=30` / `MAX_RETRY_TIMES=3` / 代理健康检查（如用代理）

### Standalone 模式

- [ ] FILTER=MemoryFilter / PIPELINE=MemoryDedupPipeline 日志已确认
- [ ] 如需断点续爬：`CHECKPOINT_ENABLED=True`（与模式无关，standalone 也能用）

### Auto 模式（Redis ZSET + Redis 去重）

- [ ] 日志中确认 `Queue type: redis (auto-detected, Redis available, ZSET queue)`
- [ ] 日志中确认 `enabled filters: crawlo.filters.AioRedisFilter`（**B-01 修复前这里会是 MemoryFilter 坑**）
- [ ] 日志中确认 `RedisDedupPipeline initialized`
- [ ] R2 模拟重跑一次：`dedup/new_count ≈ dont_filter 种子数`，不要等于总请求数

### Distributed 模式（Stream + Consumer Group）

- [ ] 至少启 2 个 Worker 做一次种子竞争演练（验证只有 1 个 Worker 塞种子）
- [ ] 杀一个 Worker（`kill -9`），观察 Failover/主动 XCLAIM 在 <5min 内回收其 pending（测绘本次 5/5 成功）
- [ ] 控制信号：`crawlo cluster pause / resume` 命令验证通过
- [ ] `CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START=True`（B-02 修复后默认）已配置
- [ ] 死信 `stream:failed` 有配套消费 & 告警脚本

---

## 8. 风险与回滚策略

| 变更 | 风险等级 | 回滚方法 |
|---|---|---|
| B-01 Auto 去重 FILTER 切换到 Redis | 低（功能增强） | settings.py 手动 `FILTER_CLASS=MemoryFilter` 覆盖即可 |
| B-02 Auto-clear shutdown 状态 | 中 | 配 `CLUSTER_AUTO_CLEAR_SHUTDOWN_ON_START=False` 回到旧行为 |
| XCLAIM min_idle 从 600s → 120s | 中 | 慢请求会被误判 stale，必要时加大 `STREAM_DELIVERY_COUNT_LIMIT` 到 5 |
| PrometheusBackend 默认启用 | 低（opt-in） | 只要 STATS_BACKEND 不改成 prometheus 就不生效 |
| Engine 继续 Composition 拆分 | 中（结构改动） | 每次拆一个 mixin 就跑一次 `test_3modes_p0p1.py` 全量测绘（本项目已有） |
| 顶层包结构收敛 | 高（import 路径） | 全部用 `deprecated alias` 过渡，旧路径 6 个月内不删 |

**测绘兜底承诺**：任何涉及 Engine / Queue / Cluster 的改动，上线前**必须**通过 `test_3modes_p0p1.py` 9/9 断言（standalone/auto_R1/auto_R2/distributed/P0_XCLAIM 全部通过）。

---

## 9. 附录：关键代码引用

- Auto 模式去重 Bug 修复：
  - [factories.py `_make_auto()`](file:///Users/oscar/projects/Crawlo/crawlo/core/config/factories.py#L87-L132) — Redis 探测 + 动态切 AioRedisFilter / RedisDedupPipeline
  - [_old_factories.py `_make_auto()`](file:///Users/oscar/projects/Crawlo/crawlo/core/config/_old_factories.py#L90-L130) — 旧工厂同步修复
- 三模式配置映射基址：[base.py MODE_CONFIG_MAP](file:///Users/oscar/projects/Crawlo/crawlo/core/config/base.py#L33-L51)
- P0 主动 XCLAIM 扫描核心：
  - [redis_stream.py `claim_stale_pending()`](file:///Users/oscar/projects/Crawlo/crawlo/queue/backends/redis_stream.py) — claim → XACK+XDEL+XADD 重新入队
  - [engine.py `_handle_distributed_idle()`](file:///Users/oscar/projects/Crawlo/crawlo/core/engine.py) — idle counter 触发 L2 主动扫描
- P0 被动心跳 Failover：[failover.py FailoverManager](file:///Users/oscar/projects/Crawlo/crawlo/cluster/failover.py#L30-L210) — 心跳过期 → 清理死亡 Worker pending
- 持久化 shutdown 控制信号：[config.py `DynamicConfig.get_control_state`](file:///Users/oscar/projects/Crawlo/crawlo/cluster/config.py#L100-L112)
- P1 Engine Composition 拆分：
  - [engine.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine.py)（保留主状态机 & 分布式 idle）
  - [engine_helpers.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine_helpers.py)（背压适配器 + start_requests 解析 + safe_queue_size）
  - [engine_generation.py](file:///Users/oscar/projects/Crawlo/crawlo/core/engine_generation.py)（RequestGenerationMixin）
- 监控基础设施：
  - [prometheus_backend.py](file:///Users/oscar/projects/Crawlo/crawlo/stats/prometheus_backend.py#L200-L225)（自动把所有 stats key 映射成 Prometheus 指标）
  - [performance_monitor.py](file:///Users/oscar/projects/Crawlo/crawlo/extensions/monitor/performance_monitor.py#L28-L136)（CPU / Memory / 网络 / 磁盘系统指标采集）
  - [health_check.py](file:///Users/oscar/projects/Crawlo/crawlo/extensions/health_check.py#L15-L50)（HealthCheck 基础扩展）
  - [prometheus-integration.md](file:///Users/oscar/projects/Crawlo/docs/guides/prometheus-integration.md)（Prometheus/Grafana 集成指南）
  - [notification-guide.md](file:///Users/oscar/projects/Crawlo/docs/guides/notification-guide.md)（钉钉/飞书/邮件通知接入）
- 三模式完整测绘脚本（含 9 项断言）：
  - [test_3modes_p0p1.py](file:///Users/oscar/projects/Crawlo/examples/test_3modes_p0p1.py)
