# Crawlo 分布式系统 — 测试计划

> 目标：系统化验证 Phase 1-6 全部分布式功能，逐层递进，每个测试有明确的验收标准。

---

## 一、测试分层

```
┌──────────────────────────────────────┐
│  L4: 端到端（真实网站 + 多 Worker）    │  1-2 个场景
├──────────────────────────────────────┤
│  L3: 系统集成（框架启动 + Redis）      │  5-6 个场景
├──────────────────────────────────────┤
│  L2: 模块集成（组件间交互）            │  8-10 个场景
├──────────────────────────────────────┤
│  L1: 单元测试（单个模块）              │  20+ 个场景
└──────────────────────────────────────┘
```

---

## 二、L1 — 单元测试（每个模块独立验证）

### 2.1 RedisStreamQueue

**目标**：验证 Stream 队列的基本 CRUD + ACK/NACK + 故障恢复

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-Q1 | `put` 单个请求 | `XADD` 返回 True，`XLEN` 增加 1 |
| L1-Q2 | `put` 高/低优先级 | 高优先 XADD 到 high stream，低优先到 low stream |
| L1-Q3 | `get_with_receipt` 取回 | 返回 `(Request, message_id)`，meta 含 `__stream_message_id` 和 `__stream_retry_count=0` |
| L1-Q4 | 优先级出队顺序 | 先 put 低优先，再 put 高优先 → get 先拿到高优先 |
| L1-Q5 | `ack` 确认 | 调用后 XPENDING 对应消息消失 |
| L1-Q6 | `nack` + RETRY | 消息重新入队，`__stream_retry_count` 自增 1，原 message 被 XACK |
| L1-Q7 | `nack` + DEAD_LETTER | 重试 3 次后转入 `stream:failed`，原 message 被 XACK |
| L1-Q8 | `nack` + ACK（终态错误） | 直接 XACK，不重试 |
| L1-Q9 | 空队列 `get_with_receipt` | timeout 内无消息返回 None |
| L1-Q10 | `pending_info` | 有未 ACK 消息时 total > 0 |
| L1-Q11 | `size()` | 与 XLEN 一致 |
| L1-Q12 | `claim_pending`（故障恢复） | 超时消息可被其他 Consumer 回收 |
| L1-Q13 | 批量 100 条 put/get | 全部成功，无丢数据 |
| L1-Q14 | Consumer Group 重建 | 删除 Stream 后 `connect()` 自动重建 Group |

### 2.2 TaskTracker

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-T1 | `on_dispatched` | `processing_count` += 1 |
| L1-T2 | `on_completed` | `processing_count` -= 1，`completed` += 1 |
| L1-T3 | `on_failed(RETRY)` | `retried` += 1 |
| L1-T4 | `on_failed(DEAD_LETTER)` | `dead_letter` += 1 |
| L1-T5 | `classify_error(TimeoutError)` | 返回 `TaskResult.RETRY` |
| L1-T6 | `classify_error(ConnectionError)` | 返回 `TaskResult.RETRY` |
| L1-T7 | `classify_error(ValueError)` | 返回 `TaskResult.RETRY`（保守策略） |
| L1-T8 | `get_processing_tasks` | 列出当前所有处理中任务 |

### 2.3 WorkerRegistry

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-R1 | `register` | 返回 worker_id，Redis HASH + ZSET 各有一条记录 |
| L1-R2 | 2 个 Worker 注册 | `get_worker_count()` = 2 |
| L1-R3 | `heartbeat` | `last_heartbeat` 时间戳更新 |
| L1-R4 | `heartbeat` + extra | `tasks_completed` 等字段更新 |
| L1-R5 | `get_worker_info` | 返回完整的 Worker 信息字典 |
| L1-R6 | `update_status(suspect)` | status 变为 "suspect" |
| L1-R7 | `get_active_workers` | 只返回心跳未超时的 Worker，过期记录自动清理 |
| L1-R8 | `detect_dead_workers(timeout=0)` | 所有 Worker 被标记为 dead |
| L1-R9 | `detect_dead_workers(timeout=∞)` | 无 Worker 被标记为 dead |
| L1-R10 | `deregister` | HDEL + ZREM，`get_worker_info` 返回 None |
| L1-R11 | 注销不存在的 Worker | 无异常 |

### 2.4 HeartbeatDaemon

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-H1 | `start` | 返回 asyncio.Task |
| L1-H2 | 运行 2 个周期 | Redis ZSET 时间戳更新 ≥ 2 次 |
| L1-H3 | `stop` | 任务取消，无异常 |
| L1-H4 | jitter 范围 | 实际间隔在 `interval * (1 ± 0.2)` 范围内 |

### 2.5 DistributedLock

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-L1 | `acquire` | 返回 holder_id |
| L1-L2 | 竞争锁 | 第二个 `acquire` 返回 None |
| L1-L3 | `release` | 释放后 `is_locked()` 返回 False |
| L1-L4 | 错误 holder 释放 | 不能释放他人持有的锁 |
| L1-L5 | 释放后重获取 | 后续 `acquire` 成功 |
| L1-L6 | `extend` 续期 | 返回 True，锁未释放 |
| L1-L7 | 5 个并发竞争 | 全部最终获得锁（顺序执行） |

### 2.6 FailoverManager

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-F1 | `check_and_recover`（无死 Worker） | 统计全 0 |
| L1-F2 | 初次检测超时 | 标记为 suspect，不回收 |
| L1-F3 | suspect > 30s 二次确认 | 回收 pending 消息，注销 Worker |
| L1-F4 | `claim_worker_tasks` | 返回回收消息数 |
| L1-F5 | `escalate_to_dead_letter` | 消息进入死信 Stream |

### 2.7 ProgressAggregator

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-P1 | 单 Worker 上报 | `total_completed` 正确 |
| L1-P2 | 多 Worker 上报 | HINCRBY 累加正确 |
| L1-P3 | `get_worker_stats` | 返回 Worker 累计统计 |
| L1-P4 | `estimate_completion` | 基于速率外推 ETA |
| L1-P5 | `reset` | 所有统计归零 |

### 2.8 DistributedRateLimiter

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-RL1 | 桶容量 burst | 连续 N 次 `acquire` 全部通过 |
| L1-RL2 | burst 溢出 | 第 N+1 次被拒绝 |
| L1-RL3 | `wait_and_acquire` | 等待后获取令牌 |
| L1-RL4 | rate=0（不限） | 永远返回 True |
| L1-RL5 | `enabled=False` | 永远返回 True |
| L1-RL6 | `set_rate` 动态调整 | 新 rate 立即生效 |
| L1-RL7 | `remove_rate` | 恢复默认 |

### 2.9 ClusterMonitor

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-M1 | `status` | 返回 workers/queue/progress/dead_letter 四部分 |
| L1-M2 | `workers` | 列出所有活跃 Worker |
| L1-M3 | `queue_info` | 含 pending/processing/failed |
| L1-M4 | `diagnose` | 含 healthy + issues 字段 |

### 2.10 ClusterMessenger

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-MS1 | Pub/Sub 订阅 | 发布后 subscriber 收到消息 |
| L1-MS2 | `get_control_state` | 默认返回 "running" |
| L1-MS3 | 多频道 | control/config/events/alerts 互不干扰 |

### 2.11 DynamicConfig

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L1-D1 | `pause_spider` | control:state = "paused" |
| L1-D2 | `resume_spider` | control:state = "running" |
| L1-D3 | `shutdown_cluster` | control:state = "shutdown" |
| L1-D4 | `set_rate_limit` | rate_limits HASH 写入 |
| L1-D5 | `remove_rate_limit` | HASH 删除对应域名 |
| L1-D6 | `add_seed_urls` / `pop_seed_urls` | RPUSH + LPOP 正确 |
| L1-D7 | 空 seed URLs pop | 返回空列表 |

---

## 三、L2 — 模块集成测试（组件间交互）

| # | 测试场景 | 涉及组件 | 验收标准 |
|---|---------|---------|---------|
| L2-1 | **注册→心跳→注销 完整流程** | Registry + HeartbeatDaemon | Worker 注册后心跳 ZSET 持续更新，注销后数据清除 |
| L2-2 | **锁 + 故障转移** | Lock + FailoverManager | 故障检测加锁，回收任务，释放锁 |
| L2-3 | **Stream 队列 + ACK/NACK + TaskTracker** | StreamQueue + TaskTracker + Scheduler | 任务流完整：put→get→process→ack/nack→tracker 计数一致 |
| L2-4 | **进度上报 + 监控查询** | ProgressAggregator + ClusterMonitor | Worker 上报后 monitor.status() 显示正确数据 |
| L2-5 | **Pub/Sub 控制 + 引擎响应** | Messenger + DynamicConfig + Engine | 暂停信号→引擎停止消费，恢复→继续 |
| L2-6 | **限流器 + 引擎拦截** | RateLimiter + Engine | 超过令牌桶的请求被引擎拒绝等待 |
| L2-7 | **种子 URL 动态注入** | DynamicConfig + Scheduler | 发布种子 URL → Worker 拉取并入队 |
| L2-8 | **崩溃恢复端到端** | StreamQueue + Registry + Failover | Worker 注册→取任务→"崩溃"→其他 Worker 检测到→回收任务 |
| L2-9 | **多 Worker 消费竞争** | 2 个 StreamQueue Consumer | 同一 Stream，2 Consumer 各自取不同消息，无重复 |
| L2-10 | **配置一致性** | Config + Engine + Scheduler | `CrawloConfig.distributed()` → 正确初始化所有组件 |

---

## 四、L3 — 系统集成测试（框架启动 + Redis）

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| L3-1 | **单 Worker 冷启动** | CrawlerProcess 启动 → 所有 9 个 cluster 组件初始化 → Worker 注册到 Redis → 心跳开始 |
| L3-2 | **单 Worker 完整爬取 + 关闭** | 爬取少量页面 → 全部 ACK → 关闭时 deregister + 停止心跳 |
| L3-3 | **双 Worker 协同（同机两个终端）** | Worker1 启动处理 50% → Worker2 加入处理剩余 50%，无重复 |
| L3-4 | **Worker 意外崩溃恢复** | Worker1 处理中 → kill -9 → Worker2 检测到崩溃 → 回收任务继续处理 |
| L3-5 | **Redis 重启恢复** | Redis 重启 → Worker 自动重连 → Consumer Group 重建 → 继续消费 |
| L3-6 | **优雅关闭** | SIGTERM → 停止消费 → 完成当前任务 → deregister → 关闭 |

### L3 验收数据

| 指标 | 期望值 |
|------|--------|
| 任务重复率 | 0%（每消息仅一个 Worker 处理） |
| 任务丢失率 | 0%（所有 XADD 的消息最终被 ACK 或进死信） |
| 崩溃恢复延迟 | < 60s（suspect 30s + claim 操作） |
| Worker 启动到就绪 | < 3s |

---

## 五、L4 — 端到端测试（真实网站 + 多 Worker）

### L4-1: ofweek 分布式爬取（5 页 × 10 文章 = 50 任务）

**环境**：3 个 Worker 终端

```
终端 1: python run.py  (先启动，创建 Consumer Group)
终端 2: python run.py  (加入 Consumer Group)
终端 3: python run.py  (加入 Consumer Group)
```

**验收标准**：
- [ ] 3 Worker 均成功注册到 Redis
- [ ] 50 个列表页 + 约 300 个详情页 = 350 个任务全部处理
- [ ] 无重复爬取（去重过滤器确认）
- [ ] 每个 Worker 按比例分担任务
- [ ] 爬取完成后所有 Worker 正常退出

### L4-2: 崩溃恢复测试

**环境**：2 Worker，Worker1 处理中强制 kill

```
终端 1: python run.py  → 处理到一半时 Ctrl+C 或 kill
终端 2: python run.py  → 检测到 Worker1 崩溃，回收其 pending 任务
```

**验收标准**：
- [ ] Worker2 在 90s 内检测到 Worker1 心跳超时
- [ ] Worker2 回收 Worker1 的未完成任务
- [ ] Worker1 的 pending 任务全部被处理
- [ ] Worker1 被自动注销

---

## 六、边界与异常测试

| # | 测试场景 | 验收标准 |
|---|---------|---------|
| E1 | Redis 不可用启动 | 抛 RuntimeError，不静默降级 |
| E2 | 队列满 | 新请求被拒绝，不丢老数据 |
| E3 | 消息体超长（>1MB Request） | 正常序列化/反序列化，不截断 |
| E4 | 同一 Consumer 重复 XACK | 无异常（幂等） |
| E5 | 心跳网络抖动（短暂断连 30s） | 不触发故障转移（suspect 二次确认） |
| E6 | 锁持有者崩溃 | 锁自动过期，其他 Worker 可获取 |
| E7 | Pub/Sub 断连恢复 | Worker 重连后通过持久化 Key 同步控制状态 |
| E8 | 大量 Worker 同时启动（10+） | 无 Consumer Group 创建冲突，任务分配均匀 |
| E9 | Stream MAXLEN 修剪 | 旧消息被清理，队列大小不超过 MAXLEN |
| E10 | 空队列长时间闲置 | Worker 空闲超时后退出（DISTRIBUTED_WORKER_IDLE_TIMEOUT） |

---

## 七、性能基准

| 指标 | 单 Worker | 3 Worker | 5 Worker |
|------|-----------|----------|----------|
| 吞吐量（msg/s） | ≥ 50 | ≥ 120 | ≥ 180 |
| put 延迟（P99） | < 10ms | — | — |
| get+ack 延迟（P99） | < 15ms | — | — |
| claim_pending（100 条） | — | < 500ms | — |
| Worker 注册延迟 | < 100ms | — | — |

---

## 八、测试执行顺序

```
Step 1: L1 全部单元测试（20+ 场景）          ← 开发期间持续运行
Step 2: L2 模块集成测试（10 场景）           ← 每个 Phase 完成时运行
Step 3: L3 系统集成测试（6 场景）            ← 全部 Phase 完成后
Step 4: E1-E10 边界测试                      ← L3 通过后
Step 5: L4 端到端测试（2 场景）              ← 边界测试通过后
Step 6: 性能基准测试                          ← L4 通过后
```

---

## 九、测试文件结构

```
tests/
├── test_distributed_l1_queue.py       # L1: RedisStreamQueue (14 cases)
├── test_distributed_l1_tracker.py     # L1: TaskTracker (8 cases)
├── test_distributed_l1_registry.py    # L1: WorkerRegistry + HeartbeatDaemon (15 cases)
├── test_distributed_l1_lock.py        # L1: DistributedLock (7 cases)
├── test_distributed_l1_failover.py    # L1: FailoverManager (5 cases)
├── test_distributed_l1_progress.py    # L1: ProgressAggregator (5 cases)
├── test_distributed_l1_rate.py        # L1: DistributedRateLimiter (7 cases)
├── test_distributed_l1_monitor.py     # L1: ClusterMonitor (4 cases)
├── test_distributed_l1_messaging.py   # L1: Messenger + DynamicConfig (10 cases)
│
├── test_distributed_l2_integration.py # L2: 10 个集成场景
├── test_distributed_l3_system.py      # L3: 6 个系统场景
├── test_distributed_edge.py           # E1-E10 边界测试
├── test_distributed_l4_e2e.py         # L4: 端到端（手动/半自动）
│
├── conftest.py                        # 共享 fixtures（Redis 连接、清理等）
└── test_distributed_perf.py           # 性能基准（可选）
```
