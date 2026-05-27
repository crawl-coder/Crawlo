# Crawlo 分布式系统开发计划

> 当前状态：多节点协作（共享队列 + 共享去重）
> 目标状态：真正的分布式系统（ACK、故障转移、节点协调）

---

## 一、现状分析

### 1.1 已有能力

| 能力 | 实现方式 | 位置 |
|------|---------|------|
| Redis 优先级队列 | ZSET + HASH + BZPOPMIN | `crawlo/queue/redis_priority_queue.py` |
| 分布式请求去重 | Redis SET + SISMEMBER | `crawlo/filters/aioredis_filter.py` |
| 数据项去重 | Redis SET | `crawlo/pipelines/dedup/redis_dedup.py` |
| Worker 阻塞等待 | BZPOPMIN + 空闲超时 | `crawlo/core/engine.py` |
| 连接池管理 | 全局共享 + 实例隔离 | `crawlo/utils/redis/pool.py` |
| Key 命名空间 | 统一前缀管理 | `crawlo/utils/redis/keys.py` |
| 集群模式支持 | Hash Tag + 自动检测 | `crawlo/queue/redis_priority_queue.py` |

### 1.2 关键缺失

| 缺失 | 影响 | 严重度 |
|------|------|--------|
| 无 ACK 机制 | Worker 崩溃后任务丢失，无法重分配 | 🔴 严重 |
| 无节点注册/心跳 | 无法感知在线节点，无法做负载均衡 | 🔴 严重 |
| 无任务状态流转 | 出队即视为"处理中"，无 processing/完成/失败状态 | 🔴 严重 |
| 无故障转移 | 节点崩溃后其任务永久丢失 | 🔴 严重 |
| 无进度聚合 | 无法查询全局爬取进度 | 🟡 中等 |
| 无分布式锁 | 多节点可能重复初始化/清理 | 🟡 中等 |
| 无节点间通信 | 无法协调速率限制、暂停/恢复等操作 | 🟡 中等 |
| 无 Master/Worker 角色 | 所有节点平等竞争，无协调者 | 🟢 低 |

---

## 二、技术选型：Redis Streams + Consumer Groups

### 2.1 为什么选择 Redis Streams

| 方案 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **当前 ZSET + BZPOPMIN** | 已实现、简单 | 无 ACK、无消费组、消息不可追踪 | ❌ 无法满足需求 |
| **Redis Streams** | 原生消费组、XACK、XPENDING、XAUTOCLAIM | Redis 6.2+（XAUTOCLAIM 需要 6.2，基础功能 5.0+） | ✅ **推荐** |
| **Redis List + LPUSH/RPOP** | 简单 | 无优先级、无消费组 | ❌ 退化方案 |
| **RabbitMQ/Kafka** | 功能强大 | 引入新依赖、运维复杂 | ❌ 过重 |
| **Celery** | 成熟 | 框架绑定、不符合 Crawlo 设计哲学 | ❌ 不适用 |

### 2.2 Redis Streams 核心特性

```text
XADD       → 入队（自动生成时间戳 ID）                            [所有版本]
XREADGROUP → 消费组读取（锁定消息给特定 Consumer）                  [5.0+]
XACK        → 确认消息处理完成                                    [5.0+]
XPENDING    → 查询未确认消息                                      [5.0+]
XCLAIM      → 转移消息所有权（需手动筛选超时消息）                   [5.0+]
XAUTOCLAIM  → 自动转移超时消息（一步完成筛选+转移）                  [6.2+]
XTRIM       → 修剪流长度（控制内存）                               [5.0+]
XINFO       → 查询流/消费组信息（监控）                            [5.0+]
```

> **Redis 版本策略**：Phase 1 使用 XCLAIM 手动实现故障转移（兼容 5.0+），
> Phase 3 引入 XAUTOCLAIM 作为可选优化（需要 6.2+）。
> 运行时检测 Redis 版本，低于 6.2 时自动降级到 XPENDING + XCLAIM 组合。

### 2.3 数据模型映射

```
当前 ZSET 模型：
┌─────────────────────────────┐
│ ZSET queue:requests         │  ← score=优先级
│   member: request_key       │
│                             │
│ HASH queue:requests:data    │  ← request_key → 序列化数据
└─────────────────────────────┘

目标 Streams 模型：
┌─────────────────────────────┐
│ STREAM queue:requests       │  ← 每条消息 = 一个 Request
│   field: priority (N)       │
│   field: data (序列化Request)│
│   field: meta (时间戳等)     │
│                             │
│ CG crawlo:{spider}:workers  │  ← Consumer Group
│   Consumer: worker-{id}     │  ← 每个 Worker 一个 Consumer
└─────────────────────────────┘
```

---

## 三、架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────┐
│                    Redis Cluster                      │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Streams    │  │   Registry   │  │   Locks     │ │
│  │  (任务队列)   │  │  (节点注册)   │  │ (分布式锁)   │ │
│  └─────────────┘  └──────────────┘  └─────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Filters   │  │   Progress   │  │   Config    │ │
│  │  (去重SET)   │  │  (进度聚合)   │  │ (动态配置)   │ │
│  └─────────────┘  └──────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────┘
         ▲              ▲              ▲
         │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ Worker1 │    │ Worker2 │    │ Worker3 │
    │(Consumer)│   │(Consumer)│   │(Consumer)│
    └─────────┘    └─────────┘    └─────────┘
```

### 3.2 节点角色

| 角色 | 职责 | 数量 |
|------|------|------|
| **Worker** | 从 Stream 消费请求、执行爬取、XACK 完成 | 1~N |
| **Coordinator** | 节点注册、心跳检测、故障转移、进度聚合 | 嵌入每个 Worker（去中心化） |

> 不采用 Master/Worker 分离模式，避免单点故障。每个 Worker 内嵌 Coordinator 逻辑，
> 通过 Redis 原子操作实现协调，无需中央节点。

### 3.3 任务状态流转

```
                  XADD
  [新请求] ──────────────► PENDING (Stream 中等待消费)
                              │
                    XREADGROUP │ (分配给 Consumer)
                              ▼
                          PROCESSING (Consumer 持有，有 lease)
                         ╱          ╲
                   XACK ╱            ╲ 超时/崩溃
                       ▼              ▼
                    DONE          XCLAIM/XAUTOCLAIM
                   (完成)           转移给其他 Consumer
                                      │
                                      ▼
                                  PROCESSING (新 Consumer)
                                 ╱          ╲
                           XACK ╱            ╲ 重试次数耗尽
                               ▼              ▼
                            DONE          FAILED QUEUE
                           (完成)         (死信队列)
```

---

## 四、Redis Key 设计

### 4.1 任务队列

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:stream:requests` | Stream | 请求队列 |
| `crawlo:{project}:{spider}:stream:high` | Stream | 高优先级队列 |
| `crawlo:{project}:{spider}:stream:low` | Stream | 低优先级队列 |
| `crawlo:{project}:{spider}:stream:failed` | Stream/List | 死信队列 |

### 4.2 消费组

| Key | 类型 | 说明 |
|-----|------|------|
| `CG: crawlo:{project}:{spider}:group:workers` | Consumer Group | Worker 消费组 |

### 4.3 节点注册

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:registry:workers` | HASH | Worker 注册表 |
| `crawlo:{project}:{spider}:registry:heartbeats` | ZSET | Worker 心跳（score=时间戳，需周期性 `ZREMRANGEBYSCORE` 清理过期记录） |

**Worker 注册表结构**：
```
HASH field: worker:{id}
  {
    "id": "worker-abc123",
    "host": "192.168.1.10",
    "pid": 12345,
    "started_at": "2026-05-27T10:00:00",
    "status": "running",         # running / idle / stopping
    "tasks_completed": 1000,
    "tasks_processing": 5,
    "last_heartbeat": "2026-05-27T10:48:00"
  }
```

### 4.4 进度聚合

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:progress:stats` | HASH | 全局统计 |
| `crawlo:{project}:{spider}:progress:items` | HASH | 各 Worker 产出统计 |

### 4.5 分布式锁

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:lock:init` | String + TTL | 爬虫初始化锁 |
| `crawlo:{project}:{spider}:lock:cleanup` | String + TTL | 清理锁 |
| `crawlo:{project}:{spider}:lock:failover` | String + TTL | 故障检测锁（避免多节点同时检测） |

### 4.6 分布式限流

| Key | 类型 | 说明 |
|-----|------|------|
| `crawlo:{project}:{spider}:rate:{domain}` | String（令牌桶） | 域名级令牌计数 |
| `crawlo:{project}:{spider}:rate:{domain}:ts` | String | 上次补充令牌的时间戳 |

限流通过 Lua 脚本实现原子令牌桶，所有 Worker 共享同一域名配额：

```lua
-- 令牌桶 Lua 脚本（原子操作）
local key = KEYS[1]          -- 令牌计数 Key
local ts_key = KEYS[2]       -- 时间戳 Key
local rate = tonumber(ARGV[1])     -- 每秒补充令牌数
local capacity = tonumber(ARGV[2]) -- 桶容量
local now = tonumber(ARGV[3])      -- 当前时间

local tokens = tonumber(redis.call('GET', key)) or capacity
local last_ts = tonumber(redis.call('GET', ts_key)) or now

-- 按时间差补充令牌
local elapsed = now - last_ts
tokens = math.min(capacity, tokens + elapsed * rate)

if tokens >= 1 then
    redis.call('SET', key, tokens - 1)
    redis.call('SET', ts_key, now)
    return 1  -- 允许
else
    redis.call('SET', key, tokens)
    redis.call('SET', ts_key, now)
    return 0  -- 拒绝（需等待）
end
```

---

## 五、开发阶段划分

### Phase 1：核心基础设施（3 周）

> 目标：搭建 Redis Streams 队列 + Consumer Group + ACK 机制

#### 5.1.1 Redis Streams 队列实现

**文件**：`crawlo/queue/redis_stream_queue.py`（新建）

```python
class RedisStreamQueue:
    """基于 Redis Streams 的分布式队列"""

    async def put(self, request, priority=0):
        """XADD 入队，支持多优先级 Stream"""

    async def get(self, consumer_name, count=1, block=5000):
        """XREADGROUP 消费"""

    async def ack(self, message_id, consumer_name):
        """XACK 确认"""

    async def nack(self, message_id, consumer_name):
        """NACK → 重新入队或转入死信"""

    async def claim_pending(self, min_idle_time=60000, count=10):
        """XAUTOCLAIM 回收超时任务"""

    async def pending_info(self):
        """XPENDING 查询未确认消息"""

    async def create_consumer_group(self):
        """XGROUP CREATE 初始化消费组"""
```

**关键设计决策**：
- 优先级方案：使用 2 个 Stream（`high` + `low`），高优先级先消费
- 消费者命名：`worker-{hostname}-{pid}-{uuid[:8]}`
- 消息格式：`{data: serialized_request, priority: N, enqueued_at: timestamp}`
- Stream 最大长度：`MAXLEN ~ 100000`（近似修剪，性能优先）

**双 Stream 读取策略**（`XREADGROUP` 一次只能读一个 Stream）：

```python
async def get(self, consumer_name, block=5000):
    """先非阻塞读高优先级，无消息时阻塞读低优先级"""
    # 1. 非阻塞尝试高优先级队列
    msgs = await redis.xreadgroup(
        group, consumer_name,
        {high_stream: ">"}, count=1, block=0  # block=0 = 非阻塞
    )
    if msgs:
        return msgs

    # 2. 高优先级无消息，阻塞等待低优先级队列
    msgs = await redis.xreadgroup(
        group, consumer_name,
        {low_stream: ">"}, count=1, block=block
    )
    return msgs
```

> **取舍说明**：这种方案在高优先级持续有新消息时效果完美。但若高优先级突发空窗
> 后又来消息，当前轮次可能错过（已进入低优先级阻塞）。实际场景中爬虫优先级调度
> 粒度较粗，这个取舍可接受。如需精确优先级，改用单 Stream + 消费后本地排序的方案。

**Consumer Group 创建时的竞态处理**：

```python
async def create_consumer_group(self):
    """XGROUP CREATE 初始化消费组（需处理并发场景）"""
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        # 组已被其他 Worker 创建，直接加入即可

#### 5.1.2 任务生命周期管理

**文件**：`crawlo/queue/task_tracker.py`（新建）

```python
class TaskResult(Enum):
    """任务处理结果分类"""
    ACK = "ack"           # 彻底完成（包括 HTTP 4xx/5xx 等终态错误）
    RETRY = "retry"       # 可重试（网络超时、连接拒绝等瞬态错误）
    DEAD_LETTER = "dead"   # 超过重试次数，转入死信

class TaskTracker:
    """任务生命周期追踪"""

    async def on_dispatched(self, request, consumer):
        """任务分配给 Consumer"""

    async def on_completed(self, request, consumer):
        """任务完成 → XACK"""

    async def on_failed(self, request, consumer, error):
        """任务失败 → 根据错误类型决定 RETRY 或 DEAD_LETTER"""
        # 区分错误类型：
        # - 网络错误（TimeoutError, ConnectionError）→ RETRY（重新入队）
        # - HTTP 403/429 → RETRY（可能需要等待或切换策略）
        # - HTTP 500 → ACK（服务端错误，重试无意义，终态处理）
        # - 解析错误 → ACK（非可恢复错误）

    async def on_timeout(self, message_id):
        """任务超时被 XCLAIM 回收"""

    async def get_pending_tasks(self, min_idle_ms=None):
        """查询处理中任务"""
```

#### 5.1.3 Scheduler 适配

**文件**：`crawlo/core/scheduler.py`（修改）

```python
# 新增方法
async def open(self):
    # 根据 QUEUE_TYPE 选择队列实现
    # 'redis_stream' → RedisStreamQueue
    # 'redis' → RedisPriorityQueue（现有）
    # 'memory' → MemoryQueue（现有）

async def next_request_with_ack(self):
    """带 ACK 语义的出队，返回 (request, receipt)"""
    # receipt 用于后续 ack/nack

async def ack_request(self, receipt):
    """确认请求处理完成"""

async def nack_request(self, receipt, reason='failed'):
    """NACK，重新入队或转入死信"""
```

**配置新增**：
```python
QUEUE_TYPE = 'auto'  # memory | redis | redis_stream | auto
STREAM_MAX_LENGTH = 100000
STREAM_CONSUMER_IDLE_TIMEOUT = 60000  # ms，超时未 ACK 的任务可被回收
STREAM_DELIVERY_COUNT_LIMIT = 3        # 最大投递次数
```

---

### Phase 2：节点注册与心跳（1 周）

> 目标：Worker 可注册、可被发现、崩溃可检测

#### 5.2.1 节点注册中心

**文件**：`crawlo/cluster/registry.py`（新建）

```python
class WorkerRegistry:
    """Worker 注册中心"""

    async def register(self, worker_info: dict) -> str:
        """注册 Worker，返回 worker_id"""
        # HSET registry:workers worker:{id} {info}
        # ZADD registry:heartbeats worker:{id} {timestamp}

    async def heartbeat(self, worker_id: str):
        """发送心跳"""
        # ZADD registry:heartbeats worker:{id} {timestamp}
        # HSET registry:workers worker:{id} last_heartbeat {ts}

    async def deregister(self, worker_id: str):
        """正常下线"""
        # HDEL + ZREM

    async def get_active_workers(self) -> list:
        """获取活跃 Worker 列表（心跳未超时）"""

    async def get_worker_info(self, worker_id: str) -> dict:
        """获取 Worker 详细信息"""

    async def detect_dead_workers(self, timeout=90) -> list:
        """检测崩溃 Worker（心跳超时）"""
        # ZRANGEBYSCORE heartbeats -inf {now-timeout}
```

#### 5.2.2 心跳守护协程

**文件**：`crawlo/cluster/heartbeat.py`（新建）

```python
class HeartbeatDaemon:
    """心跳守护"""

    async def start(self, worker_id, interval=15):
        """启动心跳循环"""
        # 每 interval 秒调用 registry.heartbeat()
        # 同时更新本节点状态（tasks_processing, tasks_completed 等）

    async def stop(self):
        """停止心跳"""
```

**配置新增**：
```python
CLUSTER_HEARTBEAT_INTERVAL = 15     # 心跳间隔（秒）
CLUSTER_WORKER_TIMEOUT = 90         # Worker 超时（秒）
CLUSTER_AUTO_DEREGISTER = True      # 崩溃后自动注销
```

---

### Phase 3：故障转移（2 周）

> 目标：Worker 崩溃后，其未完成任务自动回收和重新分配

#### 5.3.1 故障检测与转移

**文件**：`crawlo/cluster/failover.py`（新建）

```python
class FailoverManager:
    """故障转移管理"""

    async def check_and_recover(self):
        """检查并回收崩溃 Worker 的任务"""
        # 1. 清理过期心跳（ZREMRANGEBYSCORE 删除超时记录）
        # 2. 检测崩溃 Worker（心跳超时）
        # 3. 标记为 suspect 状态，等待二次确认
        # 4. 二次确认后 XCLAIM 其 pending 消息

    async def claim_worker_tasks(self, dead_worker_id):
        """认领崩溃 Worker 的所有 pending 任务"""
        # XPENDING - 获取 dead_worker 的 pending 列表
        # XCLAIM / XAUTOCLAIM - 转移到当前 Consumer

    async def handle_orphaned_tasks(self):
        """处理孤儿任务（Consumer 不存在但消息未 ACK）"""
        # XINFO CONSUMERS - 获取消费组状态
        # 对比注册表，找出不存在的 Consumer

    async def escalate_to_dead_letter(self, message_id, reason):
        """升级到死信队列"""
        # 投递次数超限 → XADD stream:failed
```

**故障检测安全冗余**（防止网络抖动的误判）：

```python
async def check_and_recover(self):
    # 1. 清理过期心跳
    await redis.zremrangebyscore("heartbeats", 0, now - worker_timeout)

    # 2. 找出心跳超时的 Worker（初次检测）
    dead = await self.registry.detect_dead_workers(timeout=90)

    for worker_id in dead:
        info = await self.registry.get_worker_info(worker_id)
        if info.get("status") == "suspect":
            # 二次确认：已标记 suspect > 30 秒，正式回收
            if now - info.get("suspect_since", now) > 30:
                await self.claim_worker_tasks(worker_id)
                await self.registry.deregister(worker_id)
        else:
            # 初次检测到超时 → 标记 suspect，不立即回收
            await self.registry.update_status(worker_id, "suspect",
                suspect_since=now)
```

> **为什么需要二次确认**：Worker 可能只是网络抖动（实际仍在运行），
> 直接 XCLAIM 会导致同一任务被两个 Worker 同时处理。
> 即使有去重过滤器兜底，也应该在设计层面减少重复投递。

#### 5.3.2 引擎集成

**文件**：`crawlo/core/engine.py`（修改）

```python
# 在 distributed 模式下的改动：

async def _failover_loop(self):
    """周期性故障检测（每个 Worker 都运行）"""
    # 使用分布式锁确保同一时间只有一个 Worker 执行故障检测
    # lock = await self.distributed_lock.acquire('failover_check', timeout=30)
    # if lock.acquired:
    #     await self.failover_manager.check_and_recover()

async def crawl(self):
    # ... 现有逻辑 ...
    # 新增：启动心跳 + 故障检测协程
    if self.settings.get('RUN_MODE') == 'distributed':
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.failover_task = asyncio.create_task(self._failover_loop())
```

---

### Phase 4：进度聚合、限流与监控（1.5 周）

> 目标：全局可观测性 + 跨节点速率控制

#### 5.4.1 进度聚合器

**文件**：`crawlo/cluster/progress.py`（新建）

```python
class ProgressAggregator:
    """进度聚合"""

    async def report(self, worker_id, stats: dict):
        """Worker 上报进度"""
        # HSET progress:stats total_enqueued {n}
        # HSET progress:stats total_completed {n}
        # HSET progress:stats total_failed {n}
        # HSET progress:items worker:{id} {stats}

    async def get_global_stats(self) -> dict:
        """获取全局统计"""
        # HGETALL progress:stats
        # + 计算速率、预估剩余时间等

    async def get_worker_stats(self, worker_id) -> dict:
        """获取 Worker 级统计"""

    async def estimate_completion(self) -> dict:
        """预估完成时间"""
        # 基于历史速率外推
```

#### 5.4.2 监控命令

**文件**：`crawlo/cluster/monitor.py`（新建）

```python
class ClusterMonitor:
    """集群监控"""

    async def status(self) -> dict:
        """集群状态总览"""
        return {
            "workers": {"active": N, "idle": M, "total": K},
            "queue": {"pending": X, "processing": Y, "failed": Z},
            "progress": {"completed": A, "items_per_sec": B},
            "eta": "2026-05-27T15:30:00"
        }

    async def workers(self) -> list:
        """Worker 列表"""

    async def queue_info(self) -> dict:
        """队列详情"""
        # XINFO STREAM + XINFO GROUPS + XINFO CONSUMERS

    async def pending_tasks(self) -> list:
        """未确认任务列表"""
```

#### 5.4.3 分布式限流器

**文件**：`crawlo/cluster/rate_limiter.py`（新建）

```python
class DistributedRateLimiter:
    """跨节点的分布式限流（基于 Redis 令牌桶）"""

    async def acquire(self, domain: str, rate: float, capacity: int = 10):
        """申请令牌，返回 True（允许）或 False（需等待）"""
        # 执行 Lua 脚本（见 4.6 节），原子操作令牌桶

    async def wait_and_acquire(self, domain: str, rate: float, timeout=30):
        """阻塞等待直到获取令牌，超时返回 False"""

    async def set_rate(self, domain: str, rate: float):
        """动态调整速率（需通知所有节点）"""
        # PUBLISH + 持久化 Key 双通道通知
```

**与现有限流器的关系**：
- 现有的 `AutoThrottle` / `DelayThrottle` 继续用于单机模式
- 分布式模式下，`DistributedRateLimiter` 在下载器前拦截，替换单机限流
- 优先级：分布式限流 > Spider 级 `download_delay` > 单机 AutoThrottle

> **核心价值**：解决多 Worker 打到同一域名的速率叠加问题。
> 例如：单 Worker 限速 1 req/s，3 Worker = 3 req/s。
> 分布式令牌桶确保无论多少 Worker，该域名总计不超过设定速率。

---

### Phase 5：分布式锁与协调（0.5 周）

> 目标：防止多节点重复操作

#### 5.5.1 分布式锁

**文件**：`crawlo/cluster/lock.py`（新建）

```python
class DistributedLock:
    """基于 Redis 的分布式锁（Redlock 简化版）"""

    async def acquire(self, name, timeout=30, retry=3, retry_delay=0.5):
        """获取锁"""
        # SET lock:{name} {holder_id} NX PX {timeout_ms}

    async def release(self, name, holder_id):
        """释放锁（Lua 原子操作，防误删）"""
        # if redis.get(key) == holder_id: redis.delete(key)

    async def extend(self, name, holder_id, additional_time=10):
        """续期"""

    async def is_locked(self, name) -> bool:
        """查询锁状态"""
```

**使用场景**：
- 爬虫初始化（创建 Consumer Group、设置初始种子 URL）
- 故障检测（避免多节点同时检测）
- 定时清理（过期 Key 清理）
- 周期性任务（Feed 导出、统计写入）

---

### Phase 6：动态配置与节点间通信（1.5 周）

> 目标：运行时可调控，支持分布式限流的跨节点通知

#### 5.6.1 动态配置

**文件**：`crawlo/cluster/config.py`（新建）

```python
class DynamicConfig:
    """分布式动态配置"""

    async def set_rate_limit(self, domain, rate):
        """设置域名级速率限制（双通道通知）"""
        # 1. HSET config:rate_limits {domain} {rate}  ← 持久化
        # 2. PUBLISH channel:config {action: rate_limit, domain, rate}  ← 即时通知

    async def pause_spider(self, spider_name=None):
        """暂停爬虫（双通道通知）"""
        # 1. SET crawlo:{project}:control:state "paused"  ← 持久化，断连重连后可恢复
        # 2. PUBLISH channel:control {action: pause}       ← 即时通知

    async def resume_spider(self, spider_name=None):
        """恢复爬虫"""
        # SET ... "running" + PUBLISH

    async def shutdown_cluster(self):
        """通知所有 Worker 停止（双通道）"""
        # SET ... "shutdown" + PUBLISH

    async def add_seed_urls(self, urls):
        """动态添加种子 URL"""

    async def set_concurrency(self, worker_id, concurrency):
        """调整 Worker 并发度"""
```

#### 5.6.2 Pub/Sub 通信 + 持久化状态兜底

**文件**：`crawlo/cluster/messaging.py`（新建）

```python
class ClusterMessenger:
    """节点间消息通信（Redis Pub/Sub + 持久化 Key 兜底）"""

    async def publish(self, channel, message):
        """广播消息（即时通知）"""

    async def subscribe(self, channel, handler):
        """订阅消息"""

    async def get_control_state(self) -> str:
        """读取持久化控制状态（兜底）"""
        # 定期检查（如每次请求前），弥补 Pub/Sub 断连期间的消息丢失
        return await redis.get(f"crawlo:{project}:control:state")

    # 预定义频道：
    # crawlo:{project}:control     — 控制指令（暂停/恢复/停止）
    # crawlo:{project}:events      — 事件通知（新 Worker 加入/退出）
    # crawlo:{project}:alerts      — 告警（速率限制触发、封禁检测）
    # crawlo:{project}:config      — 配置变更（限速调整等）
```

> **双通道设计原因**：Redis Pub/Sub 是 fire-and-forget，没有持久化。
> Worker 断连期间发布的消息会丢失。持久化 Key 作为兜底，Worker 每次处理请求前
> 检查 `control:state`，确保不会错过暂停/停止等关键指令。

---

## 六、引擎改造方案

### 6.1 Engine 分布式模式改造

**文件**：`crawlo/core/engine.py`

```python
class Engine:
    async def crawl(self):
        if run_mode == 'distributed':
            await self._distributed_crawl()
        else:
            await self._standalone_crawl()

    async def _distributed_crawl(self):
        """分布式爬取主循环"""
        # 1. 注册 Worker
        self.worker_id = await self.registry.register(worker_info)

        # 2. 启动心跳
        self.heartbeat_task = create_task(self._heartbeat_loop())

        # 3. 启动故障检测（带分布式锁）
        self.failover_task = create_task(self._failover_loop())

        # 4. 启动 Pub/Sub 监听
        self.messaging_task = create_task(self._messaging_loop())

        # 5. 主循环：XREADGROUP + 检查控制状态 + 限流 + 处理 + XACK
        while self._running:
            # 检查控制状态（持久化 Key 兜底）
            if await self.messenger.get_control_state() == "paused":
                await asyncio.sleep(1)
                continue

            request, receipt = await self.scheduler.next_request_with_ack()
            if request is None:
                await asyncio.sleep(0.5)
                continue
            try:
                # 分布式限流检查
                if self.rate_limiter:
                    await self.rate_limiter.wait_and_acquire(
                        request.meta.get('download_slot'), self.rate
                    )
                await self._process_request(request)
                await self.scheduler.ack_request(receipt)
                await self.progress.report(self.worker_id, {'completed': 1})
            except Exception as e:
                result = classify_error(e)  # TaskResult.ACK / RETRY / DEAD_LETTER
                await self.scheduler.nack_request(receipt, reason=str(e), result=result)

        # 6. 优雅关闭
        await self._graceful_shutdown()
```

**种子 URL 多节点入队**：

> 多个 Worker 启动时各自调用 `start_requests()` 并入队种子 URL。
> 去重过滤器（Redis SET）保证相同 URL 只入队一次，无需额外的分布式协调。
> 这是一个自然幂等的设计——第一个 Worker 的请求通过去重，后续 Worker 的请求被过滤。

### 6.2 优雅关闭

```python
async def _graceful_shutdown(self):
    """优雅关闭"""
    # 1. 停止接受新任务
    self._running = False

    # 2. 等待当前任务完成（最多 N 秒）
    await asyncio.wait_for(self._drain_processing(), timeout=30)

    # 3. XACK 所有已完成任务
    # 4. 注销 Worker
    await self.registry.deregister(self.worker_id)

    # 5. 停止心跳和故障检测
    self.heartbeat_task.cancel()
    self.failover_task.cancel()
```

---

## 七、兼容性策略

### 7.1 向后兼容

| 场景 | 策略 |
|------|------|
| 旧配置 `QUEUE_TYPE='redis'` | 继续使用 ZSET 队列，不强制迁移 |
| `QUEUE_TYPE='auto'` | 单机→Memory，多机→自动选择 `redis_stream` |
| `RUN_MODE='standalone'` | 不注册、不心跳、不故障检测 |
| Redis < 5.0 | 自动降级到 ZSET 队列 + 打印警告（Streams 不可用） |
| Redis 5.0 ~ 6.1 | 使用 Streams 基础功能，XAUTOCLAIM 降级为 XPENDING + XCLAIM |
| Redis 6.2+ | 全部功能可用，包括 XAUTOCLAIM 自动故障转移 |

### 7.2 迁移路径

```
v0.x（当前）:  ZSET + BZPOPMIN（多节点协作）
     ↓
v1.0:         Redis Streams + Consumer Groups（可选，QUEUE_TYPE='redis_stream'）
     ↓
v1.1:         + 节点注册/心跳/故障转移
     ↓
v1.2:         + 进度聚合/监控/动态配置
     ↓
v2.0:         redis_stream 成为默认分布式方案，redis_zset 标记 deprecated
```

---

## 八、新增配置项汇总

```python
# ===== 分布式系统配置 =====

# 队列类型（新增 redis_stream）
QUEUE_TYPE = 'auto'  # memory | redis | redis_stream | auto

# Stream 配置
STREAM_MAX_LENGTH = 100000           # Stream 最大长度
STREAM_CONSUMER_IDLE_TIMEOUT = 60000 # ms，任务超时未 ACK 可被回收
STREAM_DELIVERY_COUNT_LIMIT = 3       # 最大投递次数（超过进死信）
STREAM_BLOCK_TIMEOUT = 5000          # ms，XREADGROUP 阻塞超时

# 集群配置
CLUSTER_ENABLED = False              # 是否启用集群功能
CLUSTER_HEARTBEAT_INTERVAL = 15      # 心跳间隔（秒）
CLUSTER_WORKER_TIMEOUT = 90          # Worker 超时（秒）
CLUSTER_AUTO_DEREGISTER = True       # 崩溃后自动注销
CLUSTER_FAILOVER_CHECK_INTERVAL = 30 # 故障检测间隔（秒）
CLUSTER_FAILOVER_LOCK_TIMEOUT = 30   # 故障检测锁超时（秒）

# 分布式锁
DISTRIBUTED_LOCK_TIMEOUT = 30        # 默认锁超时（秒）
DISTRIBUTED_LOCK_RETRY = 3           # 获取锁重试次数
DISTRIBUTED_LOCK_RETRY_DELAY = 0.5   # 重试间隔（秒）

# 进度聚合
PROGRESS_REPORT_INTERVAL = 10        # 进度上报间隔（秒）

# 动态配置
DYNAMIC_CONFIG_ENABLED = True        # 是否启用动态配置

# 分布式限流
DISTRIBUTED_RATE_LIMIT_ENABLED = False  # 是否启用分布式限流
DISTRIBUTED_RATE_LIMIT_DEFAULT_RATE = 0 # 默认速率（0=不限，单位：req/s）
DISTRIBUTED_RATE_LIMIT_CAPACITY = 10    # 令牌桶容量（允许突发）
```

---

## 九、新增文件清单

```
crawlo/
├── cluster/                    # 新建模块
│   ├── __init__.py
│   ├── registry.py            # Worker 注册中心
│   ├── heartbeat.py           # 心跳守护
│   ├── failover.py            # 故障转移
│   ├── progress.py            # 进度聚合
│   ├── monitor.py             # 集群监控
│   ├── lock.py                # 分布式锁
│   ├── config.py              # 动态配置
│   ├── messaging.py           # 节点间通信
│   └── rate_limiter.py        # 分布式限流（令牌桶）
├── queue/
│   └── redis_stream_queue.py  # 新建：Redis Streams 队列
└── utils/
    └── redis/
        └── stream_utils.py    # 新建：Stream 工具函数
```

---

## 十、测试计划

### 10.1 单元测试

| 模块 | 测试内容 | 优先级 |
|------|---------|--------|
| `RedisStreamQueue` | 入队/出队/ACK/NACK/claim/消费组竞态 | P0 |
| `WorkerRegistry` | 注册/心跳/注销/超时检测/suspect 状态 | P0 |
| `FailoverManager` | 崩溃检测/二次确认/任务回收/死信升级 | P0 |
| `DistributedRateLimiter` | 令牌桶/多节点速率聚合/Lua 原子性 | P0 |
| `DistributedLock` | 加锁/解锁/续期/防误删 | P1 |
| `ProgressAggregator` | 上报/聚合/预估 | P1 |
| `DynamicConfig` | 动态限速/暂停恢复/双通道通知 | P2 |

### 10.2 集成测试

| 场景 | 测试内容 | 优先级 |
|------|---------|--------|
| 双 Worker 竞争消费 | 同一 Stream，2 Worker，任务不重复 | P0 |
| Worker 崩溃恢复 | Worker1 处理中崩溃 → suspect → Worker2 回收任务 | P0 |
| 网络抖动误判 | Worker 短暂断连 → 不应触发回收 → 重连后继续 | P0 |
| 优雅关闭 | Worker 收到 SIGTERM → 完成当前任务 → 注销 | P0 |
| 分布式限流 | 3 Worker 限速总计 1 req/s，实际不超过 1 req/s | P0 |
| 3 Worker 弹性伸缩 | 动态启停 Worker，任务自动均衡 | P1 |
| 消费组重建 | 删除 Consumer Group 后重启自动重建 | P1 |
| Pub/Sub 断连恢复 | Worker 断连期间发布暂停 → 重连后检查 Key 感知 | P1 |

### 10.3 混沌测试

| 场景 | 测试内容 | 优先级 |
|------|---------|--------|
| Redis 重启 | 任务不丢失，Worker 自动重连 | P1 |
| 网络分区 | 部分节点断连后恢复 | P2 |
| Worker OOM Kill | 任务被其他 Worker 回收 | P1 |
| Redis 内存满 | XADD 失败时的降级策略 | P2 |

---

## 十一、里程碑时间表

```
Week 1-3:  Phase 1 — Redis Streams 队列 + ACK + Scheduler 适配
Week 4:    Phase 2 — 节点注册 + 心跳
Week 5-6:  Phase 3 — 故障转移 + 引擎集成
Week 7:    Phase 5 — 分布式锁（可在 Phase 4 前完成）
Week 8-9:  Phase 4 — 进度聚合 + 分布式限流 + 监控
Week 10:   Phase 6 — 动态配置 + Pub/Sub 双通道
Week 11:   集成测试 + 混沌测试 + 文档
Week 12:   Bug 修复 + 性能优化 + 发布 v1.0

总计：约 12 周（3 个月）
```

---

## 十二、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Redis Streams 内存膨胀 | 中 | 高 | XTRIM 定期修剪 + MAXLEN 限制 + 监控告警 |
| 故障转移误判（网络抖动） | 中 | 高 | 心跳超时保守（90s）+ suspect 二次确认（30s）+ 去重过滤器 + 幂等性兜底 |
| 分布式锁死锁 | 低 | 高 | 锁自动过期 + 持有者标识 Lua 原子防误删 |
| 单节点性能回归（Stream vs ZSET） | 中 | 中 | Phase 1 完成时做基准测试对比，Stream 开销主要在 XADD/XACK 三次网络往返，目标 < 5% 劣化 |
| XCLAIM 消息重复投递 | 低 | 中 | suspect 二次确认降低误判；即使重复，去重过滤器兜底 + 下载幂等设计 |
| 心跳风暴（大量 Worker 同时心跳） | 低 | 低 | 随机化心跳间隔（±20% jitter） |
| Redis < 5.0 | 低 | 中 | 运行时检测 + 自动降级到 ZSET |
| Redis 5.0-6.1（无 XAUTOCLAIM） | 中 | 低 | XPENDING + XCLAIM 手动 fallback，功能等价，只是多 1 次 Redis 调用 |

---

## 十三、与现有推广文章的口径

开发完成后，推广文章中的术语更新：

| 当前表述 | 更新为 | 条件 |
|---------|--------|------|
| 多节点协作 | 分布式系统 | Phase 1-3 完成后 |
| 共享队列 + 共享去重 | 基于消费者组的分布式调度 | Phase 1 完成后 |
| 无 ACK / 无故障转移 | 自动故障转移 + 任务确认机制 | Phase 3 完成后 |

> **注意**：在全部 Phase 完成并经过充分测试前，对外仍使用"多节点协作"表述，避免过度承诺。
