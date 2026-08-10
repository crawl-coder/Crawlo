# 分布式消息可靠性与故障恢复

> 从 `distributed_architecture.md` 拆分而来：消息 ACK 语义、故障恢复、网络分区与脑裂处理。

## 6. 消息可靠投递（Lua 原子化 ACK/NACK/重试）

### 6.1 ACK / NACK 机制

ACK 使用 Lua 脚本在 Redis 服务端原子执行 XACK + XDEL，消除进程崩溃窗口：

```python
async def _ack_message(request, engine, success, error=None):
 if not engine._cluster_worker_id:
 return # 非分布式模式，跳过

 message_id = request.meta['__stream_message_id']

 if success:
 # Lua 脚本原子执行 XACK + XDEL
 # → 消除了 XACK 和 XDEL 之间的崩溃窗口（幽灵消息问题）
 await engine.scheduler.ack_request(message_id)
 else:
 result = engine._task_tracker.classify_error(error)
 # → RETRY / DEAD_LETTER / ACK
 # 重试路径同样使用 Lua 脚本原子执行：XRANGE + XACK + XDEL + XADD
 await engine.scheduler.nack_request(message_id, result=result)
```

**原子 ACK Lua 脚本**：
```lua
local acked = redis.call('XACK', KEYS[1], ARGV[1], ARGV[2])
if acked > 0 then
 redis.call('XDEL', KEYS[1], ARGV[2])
end
return tostring(acked)
```

**原子重试 Lua 脚本**（XRANGE → 转 hash 表 → XACK+XDEL → XADD 重新入队，全程原子）：
```lua
local msgs = redis.call('XRANGE', KEYS[1], ARGV[1], ARGV[1], 'COUNT', 1)
local flat = msgs[1][2]
local fields = {}
for i = 1, #flat, 2 do fields[flat[i]] = flat[i + 1] end
-- 注意：XRANGE 返回的 fields 是平铺数组 [k1,v1,k2,v2,...]，需先转 hash 表
local retry_count = 1
if fields['retry_count'] then retry_count = tonumber(fields['retry_count']) + 1 end
if retry_count >= tonumber(ARGV[5]) then
 redis.call('XACK', KEYS[1], ARGV[2], ARGV[1])
 redis.call('XDEL', KEYS[1], ARGV[1])
 return {0, retry_count} -- 超限进死信
end
redis.call('XACK', KEYS[1], ARGV[2], ARGV[1])
redis.call('XDEL', KEYS[1], ARGV[1])
fields['retry_count'] = tostring(retry_count)
-- unpack(fields) 重新入队
local nf = {}
for k, v in pairs(fields) do nf[#nf + 1] = k; nf[#nf + 1] = v end
redis.call('XADD', KEYS[1], 'MAXLEN', '~', tonumber(ARGV[6]), '*', unpack(nf))
return {1, retry_count}
```

> **双 Stream ACK 路由**：`_message_stream` 字典记录每个 `message_id` 的来源 Stream
> （high/normal）。ACK/NACK/重试/死信升级均通过此映射路由到正确的 Stream，确保
> `high_stream` 的消息不会被错误 ACK 到 `stream`。

### 6.2 重试与死信

```
投递次数 动作
─────────────────────────────────
第1次 (retry=0) → 正常处理
第2次 (retry=1) → NACK(RETRY) → XRANGE 读字段 → XACK+XDEL → XADD (重新入队)
第3次 (retry=2) → NACK(RETRY) → XRANGE 读字段 → XACK+XDEL → XADD (重新入队)
第4次 (retry=3) → 超限 → XADD stream:failed (死信)
 dead_fields: {original_message_id, dead_at, dead_reason, retry_count}
```

### 6.3 序列化策略

| 策略 | 配置 | 效果 |
|---|---|---|
| 紧凑序列化 | `STREAM_COMPACT=True` | 跳过 None/空容器/空字符串/默认值字段 |
| JSON 格式 | `STREAM_SERIALIZATION_FORMAT='json'` | redis-cli 可读，跨语言兼容 |

```
完整 fields (14):
 url, method, callback, meta, headers, cookies, body, encoding,
 priority, dont_filter, allow_redirects, verify, use_dynamic_loader, errback

紧凑后 fields (通常只存 ~5):
 url, callback, meta(非空), body(非空), encoding(非None)
```

---


## 7. 故障恢复

### 7.1 孤儿 Pending 回收 (启动时)

**场景**：上一轮所有 Worker 已退出，留下已读但未 ACK 的消息。

```python
RedisStreamQueue.connect()
 └─ _ensure_consumer_groups() # 创建 Consumer Group
 └─ self._connected = True # 必须先标记（claim_pending 需要）
 └─ _recover_orphan_pending() # 回收孤儿消息
 ├─ 并发启动检查（防误回收）:
 │ └─ XINFO CONSUMERS 检查两个 Stream（high + normal）
 │ 若存在 idle < 30s 的活跃 Consumer → 跳过回收
 │ （说明有其他 Worker 正在处理，不是孤儿场景）
 └─ 无活跃 Consumer → 执行回收:
 └─ XPENDING 查 pending 数量
 └─ 对两个 Stream（high + normal）分别:
 while True:
 claim_pending(min_idle_ms=1, count=100)
 └─ XAUTOCLAIM / XPENDING+XCLAIM 原子 claim
 └─ 逐条:
 XRANGE 读原始字段
 XACK + XDEL 原消息
 XADD 重新入队 (retry_count+1)
 超限 → XADD stream:failed (死信)
```

> **防误触发机制**：`_orphan_idle_threshold_ms` 可配置（默认 30000ms）。
> 并发启动时，各 Worker 的 Consumer 均在 Group 中且 idle 极短，检查会跳过回收，仅留待 Failover 机制处理。

### 7.2 Failover 任务回收 (运行时)

**场景**：某 Worker 心跳超时被判定为崩溃，其 pending 任务需回收。

```python
FailoverManager.check_and_recover()
 └─ detect_dead_workers(90s)
 └─ 两阶段检测:
 Phase 1: 首次发现 → 检查 status
 ├─ STATUS_STOPPING → 跳过（优雅退出中，不回收）
 └─ 其他 → mark suspect, suspect_since=now (不回收)
 Phase 2: suspect > 30s → acquire lock → _claim_worker_tasks()
 └─ 回收两个 Stream 的 pending（high + normal）
 └─ 循环 claim_pending(min_idle=60s, count=100)
 └─ XRANGE → XACK+XDEL → XADD (retry+1, failover_from=worker_id)
 └─ deregister()
```

### 7.3 恢复对比

| 维度 | 孤儿回收 (`_recover_orphan_pending`) | Failover 回收 (`_claim_worker_tasks`) |
|---|---|---|
| 触发时机 | Worker 启动时 | 心跳超时 + 30s confirm |
| idle 阈值 | 1ms (立即) | 60s (consumer_idle_timeout) |
| Stream 范围 | high + normal 两个 Stream | high + normal 两个 Stream |
| 活跃检查 | XINFO CONSUMERS: idle < 30s → 跳过 | 两阶段检测 + STATUS_STOPPING 豁免 |
| 锁保护 | 无 (各 Worker 并发回收) | DistributedLock (互斥) |
| 互斥性 | XAUTOCLAIM 原子 claim | 同一任务只被一个 Worker claim |

---

## 投递语义：at-least-once（至少一次）

### 语义定义

Crawlo 分布式队列的投递语义为 **at-least-once（至少一次）**：

- 每条消息**至少被处理一次**（可能被处理多次）；
- 不会丢消息（Worker 崩溃后由 XCLAIM 回收重投）；
- 但**不保证恰好一次**——重复处理是可能发生的，需由业务侧幂等兜底。

> 这与多数消息队列（Kafka / Redis Stream / RabbitMQ 默认）一致。
> 恰好一次（exactly-once）需要分布式事务或幂等写入配合，框架层不提供。

### 重复投递的场景

| 场景 | 发生原因 | 结果 |
|---|---|---|
| **ACK 前崩溃** | Worker 处理完但未执行 ACK 就退出 | XCLAIM 回收 → 任务被重投 → 重复处理 |
| **网络分区** | Worker 与 Redis 短暂断开，任务被判定 stale | 其他 Worker XAUTOCLAIM 领取 → 原 Worker 恢复后可能仍在处理 |
| **重试** | NACK(RETRY) 重新入队 | 同一 URL 被处理多次（retry_count 递增） |
| **孤儿回收竞态** | 启动时回收与运行中回收并发 | 依赖 XAUTOCLAIM 原子性，同一任务只被一个 Worker claim，但处理后仍可能重复 |

### 幂等保障建议

业务侧按以下优先级组合使用：

1. **框架去重管道**（推荐）：

```python
PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 1,   # 基于 URL/指纹去重
    'my_project.pipelines.MyPipeline': 300,
}
```

2. **数据库唯一键约束**（强兜底）：

```python
# MySQL 管道配合唯一键
MYSQL_UPDATE_COLUMNS = ('url',)      # 或业务唯一键
MYSQL_INSERT_IGNORE = True
```

3. **自定义管道幂等写入**（最可靠）：

```python
class IdempotentPipeline(BasePipeline):
    async def process_item(self, item, spider):
        # 以业务唯一键（如 url + sku）做 upsert，而非盲目 insert
        await self._upsert_by_key(dict(item))
        return item
```

### 判断要点

- 只读抓取 + 覆盖式存储 → 天然幂等，无需额外处理；
- 追加式存储（日志/计数）→ 必须用唯一键或去重管道；
- 强一致场景（支付/订单）→ 爬虫不适用，需业务侧幂等 + 对账。

---

## 附录 D：网络分区与脑裂处理

### 网络分区场景

当网络分区导致部分 Worker 无法连接 Redis 时：

```
 ┌─── Redis ───┐
 │ │
 ┌────┴────┐ ┌────┴────┐
 │ Worker A │ │ Worker B │
 │ (可达) │ │ (不可达) │
 └─────────┘ └─────────┘
 正常运行 心跳超时 → 被 Failover 标记为 suspect
```

### 脑裂风险

Crawlo 的分布式设计中，**不存在真正的脑裂问题**，因为：

1. **Redis 是唯一的真理来源**：所有状态（任务、心跳、锁、配置）都存储在 Redis 中。Worker 之间不直接通信，不持有独立状态。

2. **Leader 选举基于 Redis SETNX**：分区后的 Worker 无法执行 `SETNX`，不会产生两个 Leader。

3. **任务消费基于 Consumer Groups**：即使分区导致 Worker B 无法 ACK，其 PENDING 任务会被 XAUTOCLAIM 回收并重新分配给可达的 Worker A。不会出现同一任务被两个 Worker 同时处理的情况。

### 分区恢复后

Worker B 网络恢复后：

1. 重新连接 Redis
2. 发现心跳已超时 → 自己已被标记为 dead
3. **不会**继续处理旧任务（已被 XCLAIM 走）
4. 重新注册为新 Worker，从 Stream 消费新任务

### 风险点

| 场景 | 风险 | 缓解措施 |
|------|------|---------|
| Worker B 分区时正在处理任务 | 任务被 XCLAIM 后重复执行 | Pipeline 层做幂等处理（RedisDedupPipeline） |
| 分区期间 Leader 不可达 | 无法协调退出 | 等待分区恢复，或手动 `redis-cli SET control:state shutdown` |
| Redis 自身分区 | 全集群暂停 | Sentinel 自动故障转移 |

---
