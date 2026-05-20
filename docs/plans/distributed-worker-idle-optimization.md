# 分布式 Worker 空闲等待优化计划

## 问题

当分布式 Worker 启动时 Redis 队列为空，或运行期间队列消费完毕后，Worker 会**立即退出**。
这导致以下场景失效：

| 场景 | 后果 |
|------|------|
| Worker 启动早于种子入队 | 取到 0 个任务直接退出 |
| 运行中动态新增任务到队列 | 无人消费，所有 Worker 已退出 |
| 任务分阶段产生（列表页 → 详情页） | 后续阶段的 URL 不会被处理 |

**根因**：`_request_available` 是进程内 `asyncio.Event`，Worker A 入队新请求只唤醒本进程，
其他 Worker 完全无感知。队列为空 → `_should_exit()` 返回 True → 退出。

---

## 方案：BZPOPMIN 阻塞等待 + 空闲超时

### 核心思路

- 队列空时不退出，而是用 Redis `BZPOPMIN` **阻塞等待**新任务
- `BZPOPMIN` 在 Redis 服务端阻塞，任务到达即唤醒，零延迟、零 CPU 开销
- 连续空闲超过阈值后才退出（可配置，0 = 永不退出）

### 为什么选 BZPOPMIN 而非轮询

| 对比项 | 指数退避轮询 | BZPOPMIN |
|--------|-------------|----------|
| 响应延迟 | 最差 30s | **0s**（任务到即醒） |
| CPU/网络开销 | 持续空轮询 | **零**（服务端阻塞） |
| 代码复杂度 | 退避状态机 + 间隔计算 | **一行阻塞调用** |
| Redis 版本要求 | 任意 | ≥5.0（2018 年发布，已普及） |

---

## 改动清单

### 1. `crawlo/queue/redis_priority_queue.py` — 新增 `get_blocking()`

**位置**：`RedisPriorityQueue` 类，L449 之后新增方法

```python
async def get_blocking(self, timeout: float = 30.0) -> Optional['Request']:
    """
    阻塞式获取请求（使用 BZPOPMIN）
    
    与 get() 的区别：
    - get(): 非阻塞，空则立即返回 None（向后兼容）
    - get_blocking(): BZPOPMIN 阻塞等待，timeout 秒内无数据返回 None
    
    Args:
        timeout: 阻塞等待超时（秒），0 = 非阻塞，None = 永久阻塞
    
    Returns:
        Optional[Request]: 请求对象或 None（超时）
    """
    try:
        await self._ensure_connection()
        if not self._redis:
            return None

        # ── 集群模式：与 get() 一致的 hash tag 处理 ──
        if self._is_cluster_mode():
            hash_tag = "{queue}"
            queue_name_with_tag = f"{self.queue_name}{hash_tag}"
            result = await self._redis.bzpopmin(queue_name_with_tag, timeout=timeout)
        else:
            result = await self._redis.bzpopmin(self.queue_name, timeout=timeout)

        if not result:
            return None

        _, key, score = result
        data_key = self.key_manager.get_requests_data_key()
        if self._is_cluster_mode():
            hash_tag = "{queue}"
            data_key = self.key_manager.get_requests_data_key() + hash_tag

        serialized = await self._redis.hget(data_key, key)
        if not serialized:
            # 脏数据：ZSET 有 key 但 hash 无数据 → 委托 _deserialize_request 统一清理
            return await self._deserialize_request(None, key, data_key,
                                                   queue_name=queue_name_with_tag if self._is_cluster_mode() else self.queue_name)

        # 复用现有的反序列化逻辑（提取为 _deserialize_request 内部方法）
        return await self._deserialize_request(serialized, key, data_key)

    except redis.ResponseError as e:
        # Redis < 5.0 不支持 BZPOPMIN → fallback 到轮询
        if "unknown command" in str(e).lower():
            # 用标志位缓存，避免每秒重复 warning
            if not getattr(self, '_bzpopmin_unsupported', False):
                self._bzpopmin_unsupported = True
                logger.warning(
                    f"BZPOPMIN not supported (Redis < 5.0), "
                    f"falling back to polling for project {self.key_manager.project_name}"
                )
            # 不额外 sleep，由 engine 层 remaining 控制节奏
            return None
        # 其他 Redis 错误同等处理
        ErrorHandler(__name__).handle_error(e, context=ErrorContext(
            context=f"阻塞获取队列任务失败 (Project: {self.key_manager.project_name})"
        ), raise_error=False)
        return None
    except Exception as e:
        # 连接断开等异常，返回 None 让上层重试
        ErrorHandler(__name__).handle_error(e, context=ErrorContext(
            context=f"阻塞获取队列任务失败 (Project: {self.key_manager.project_name})"
        ), raise_error=False)
        return None
```

**重构**：将现有 `get()` 中 L488-L552 的反序列化逻辑提取为 `_deserialize_request()` 内部方法，
`get()` 和 `get_blocking()` 共用。`_deserialize_request()` 统一处理脏数据清理：

```python
async def _deserialize_request(self, serialized, key, data_key, queue_name=None):
    """反序列化请求，含脏数据清理"""
    if not serialized:
        # 脏数据：ZSET 有 key 但 hash 无数据 → 清理
        await self._redis.hdel(data_key, key)
        if queue_name:
            await self._redis.zrem(queue_name, key)
        return None
    
    # ... 现有反序列化逻辑（从 get() L488-L552 移入）...
```

> 这样 `get()` 中原来的 `if not serialized: continue` 也会自动带上清理逻辑。

**关键补丁**（与初版对比）：
1. ✅ 添加集群模式 hash tag 处理（`{queue}`）
2. ✅ 脏数据清理统一到 `_deserialize_request()`，`get()` 和 `get_blocking()` 共享
3. ✅ 捕获 `ResponseError("unknown command")` 做 Redis < 5.0 fallback
4. ✅ `_bzpopmin_unsupported` 标志位缓存，避免每秒重复 warning 日志

---

### 2. `crawlo/queue/queue_manager.py` — 新增 `get_blocking()`

**位置**：`QueueManager` 类，L247 `get()` 方法之后

```python
async def get_blocking(self, timeout: float = 30.0) -> Optional["Request"]:
    """阻塞式获取（仅 Redis 队列支持，内存队列 fallback 到普通 get）"""
    if not self._queue:
        raise RuntimeError("队列未初始化")

    if self._queue_type == QueueType.REDIS and hasattr(self._queue, 'get_blocking'):
        result = await self._queue.get_blocking(timeout=timeout)
        if result and hasattr(result, 'url'):
            return result
        return None

    # 内存队列 fallback
    return await self.get()
```

---

### 3. `crawlo/core/scheduler.py` — 新增 `next_request_blocking()`

**位置**：`Scheduler` 类，L302 `next_request()` 方法之后

```python
async def next_request_blocking(self, timeout: float = 30.0):
    """阻塞式获取下一个请求（分布式模式专用）"""
    if not self.queue_manager:
        return None
    try:
        request = await self.queue_manager.get_blocking(timeout=timeout)
        if request:
            async with self._queue_not_full:
                self._queue_not_full.notify_all()
        return request
    except Exception as e:
        self.error_handler.handle_error(
            e, context=ErrorContext(context="阻塞获取请求失败"), raise_error=False
        )
        return None
```

---

### 4. `crawlo/core/engine.py` — 核心逻辑改造

**位置**：`_get_next_request()` 方法（L468）+ 主循环（L236-L306）

#### 4.1 新增实例变量

```python
# __init__ 中新增
self._idle_since: Optional[float] = None   # 空闲起始时间（使用 time.monotonic()）
```
> 使用 `time.monotonic()` 而非 `time.time()`：单调时钟不受系统时间调整（NTP 对时）影响。

#### 4.2 新增配置读取

```python
# _init_configs() 中新增
self._worker_idle_timeout = self._get_setting('DISTRIBUTED_WORKER_IDLE_TIMEOUT', 300)
```

#### 4.3 主循环改造

```python
# 主循环中，idle_count 判断逻辑替换为：

else:
    # 队列为空
    idle_count += 1

    # ── 关键：仅 distributed 模式阻塞等待 ──
    # auto 模式即使用了 Redis，队列空也要退出（auto 是自动检测模式，不是常驻模式）
    if self.run_mode == 'distributed' and self._start_requests_source is None:
        # ── distributed 模式：BZPOPMIN 阻塞等待 ──

        # 计算剩余空闲配额（_worker_idle_timeout=0 表示永不退出）
        if self._worker_idle_timeout > 0:
            if self._idle_since is not None:
                remaining = self._worker_idle_timeout - (
                    time.monotonic() - self._idle_since
                )
            else:
                remaining = self._worker_idle_timeout  # 首次空闲，全配额
            if remaining <= 0:
                self.logger.info(
                    f"Worker idle for {self._worker_idle_timeout}s, exiting"
                )
                break
        else:
            remaining = 30.0  # 永不退出，每次 BZPOPMIN 等 30s

        request = await self.scheduler.next_request_blocking(
            timeout=min(30.0, max(1.0, remaining))
        )
        if request:
            idle_count = 0
            self._idle_since = None
            # 处理请求 → 回到循环顶部批量派发...
            continue
        else:
            # BZPOPMIN 超时（30s 内无新任务）
            if self._idle_since is None:
                self._idle_since = time.monotonic()
            if self._worker_idle_timeout > 0:
                elapsed = time.monotonic() - self._idle_since
                if elapsed >= self._worker_idle_timeout:
                    self.logger.info(
                        f"Distributed worker idle for {elapsed:.0f}s "
                        f"(timeout={self._worker_idle_timeout}s), exiting"
                    )
                    break
            # ── 超时但未达总配额：不执行 _request_available Event 等待 ──
            # BZPOPMIN 已阻塞 30s，再等 Event 纯属浪费
            continue
    else:
        # ── standalone / auto 模式：现有行为不变 ──
        # 注意：auto 模式即使用了 Redis，队列空也走正常退出逻辑
        if idle_count == 1:
            should_exit, last_component_states = await self._should_exit(last_component_states)
            if should_exit:
                await asyncio.sleep(0.001)
                # ... 现有退出逻辑
```

**注意**：distributed 模式 BZPOPMIN 超时后调用 `continue` 直接进入下一轮循环，
跳过主循环底部的 `_request_available` Event 等待（该 Event 是进程内的，在分布式模式下无意义）。

#### 4.4 `_should_exit()` 改造

```python
async def _should_exit(self, last_component_states=None) -> tuple[bool, tuple]:
    """仅 distributed 模式下跳过"队列空+组件空闲"的退出判断
    
    standalone / auto 模式：队列空 + 所有组件空闲 → 正常退出
    distributed 模式：不因队列空退出，由 BZPOPMIN 超时 + idle_timeout 决定
    
    注意：auto 模式即使检测到 Redis 并切换为 Redis 队列，
         仍然按单机逻辑退出（auto 只是根据环境自动选队列类型，不是常驻 Worker）
    """
    if self.run_mode == 'distributed':
        # 分布式模式不因"组件空闲"退出，但保留未来扩展其他退出条件的空间
        # 如果将来 _should_exit 增加致命错误等退出条件，这里不应跳过
        return False, None

    # standalone / auto 模式：现有逻辑不变
    ...
```

> **设计说明**：当前 `_should_exit()` 只检查"所有组件空闲"，所以 `return False` 暂时安全。
> 但如果未来新增退出条件（如致命错误、外部关闭信号），需要在此处细化判断，
> 仅跳过"队列空"相关条件，而非全部。

---

### 5. `crawlo/config.py` — 新增配置项

**位置**：`MODE_CONFIG_MAP['distributed']` 字典（L71）

```python
'distributed': {
    'RUN_MODE': 'distributed',
    'QUEUE_TYPE': 'redis',
    'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
    'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
    # 新增 ↓
    'DISTRIBUTED_WORKER_IDLE_TIMEOUT': 300,   # 连续空闲 N 秒后退出（0 = 永不退出）
},
```

---

### 6. `crawlo/settings/default_settings.py` — 默认配置

```python
# 分布式 Worker 配置
DISTRIBUTED_WORKER_IDLE_TIMEOUT = 300   # 连续空闲 N 秒后退出（0 = 永不退出）
```

---

## 执行流程对比

### 现有行为（所有模式共用）

```
队列空 → _get_next_request() → None
  → idle_count++
  → _should_exit() → 所有组件空闲 → True
  → break → close_spider()
```

### 优化后

```
队列空 → _get_next_request() → None
  → idle_count++
  → run_mode == 'distributed' ?
     ├─ Yes → BZPOPMIN(timeout=30s)
     │        ├─ 有数据 → 重置 idle_since → 继续消费
     │        └─ 超时 → idle_since 计时
     │             └─ 空闲 > IDLE_TIMEOUT → 退出
     └─ No (standalone / auto) → 现有行为不变（队列空即退出）
         注：auto 模式即使用了 Redis 队列，也走此分支
```

---

## 向后兼容性

| 组件 | 影响 | 兼容处理 |
|------|------|---------|
| `RedisPriorityQueue.get()` | 不变 | 非阻塞行为保留 |
| `RedisPriorityQueue.get_blocking()` | **新增** | 新方法，不破坏现有代码 |
| `QueueManager.get()` | 不变 | 非阻塞行为保留 |
| `QueueManager.get_blocking()` | **新增** | 内存队列 fallback 到 `get()` |
| `Scheduler.next_request()` | 不变 | 非阻塞行为保留 |
| `Scheduler.next_request_blocking()` | **新增** | 透传到 `queue_manager` |
| `Engine._should_exit()` | 修改 | **仅 `run_mode='distributed'`** 跳过队列空退出判断 |
| 单机模式 | **零影响** | `run_mode='standalone'` 走原逻辑 |
| auto 模式 | **零影响** | `run_mode='auto'` 即使检测到 Redis 也走原逻辑，队列空即退出 |

---

## 容错设计

| 场景 | 处理 |
|------|------|
| Redis 连接断开 | `get_blocking()` catch 异常 → 返回 None → 主循环下轮重连重试 |
| Redis < 5.0 (无 BZPOPMIN) | 捕获 `ResponseError("unknown command")` → 首次 warning + `_bzpopmin_unsupported` 标志位 → 不额外 sleep，由 engine remaining 控制节奏 |
| Ctrl+C 中断 | BZPOPMIN 最多阻塞 30s → asyncio.CancelledError 正常传播 |
| 永久空队列 | `IDLE_TIMEOUT > 0` 时正常退出；`IDLE_TIMEOUT = 0` 时永不退出 |
| `IDLE_TIMEOUT=0` | 永不退出，持续 BZPOPMIN 等待（适合常驻 Worker） |
| 集群模式 | `BZPOPMIN` + hash tag `{queue}` 支持 Redis Cluster |
| ZSET 脏数据 (key 在 zset 但 hash 无数据) | `hget` 失败后自动 `hdel` + `zrem` 清理 |
| NTP 对时 / 系统时间回退 | 使用 `time.monotonic()` 单调时钟，不受系统时间调整影响 |

---

## 测试计划

### 单元测试

| 测试项 | 文件 | 验证点 |
|--------|------|--------|
| `get_blocking()` 正常获取 | `tests/test_redis_queue.py` | BZPOPMIN 返回正确数据 |
| `get_blocking()` 超时返回 None | 同上 | 空队列 + timeout=1s → 返回 None |
| `get_blocking()` Redis 断连 | 同上 | 异常时不抛出，返回 None |
| `get_blocking()` 集群模式 hash tag | 同上 | 集群模式下使用正确 key |
| `get_blocking()` hget 失败脏数据清理 | 同上 | 清理后 ZSET 中无残留 |
| `get_blocking()` Redis < 5.0 fallback | 同上 | 首次 warning，后续静默，不额外 sleep |
| 内存队列 `get_blocking()` fallback | 同上 | 调用 `get()` 而非报错 |
| `_should_exit()` 分布式返回 False | `tests/test_engine.py` | run_mode=distributed 时不退出 |
| `IDLE_TIMEOUT=0` 永不退出 | 同上 | 连续空转 3 轮仍不 break |
| `IDLE_TIMEOUT=10` 超时退出 | 同上 | 空闲 10s 后正常退出 |

### 集成测试

```bash
# 1. 启动空队列 Worker（应等待不退出）
redis-cli FLUSHDB
python run.py  # Worker 应持续等待，不退出

# 2. 另一终端入队任务（Worker 应立即消费）
redis-cli ZADD crawlo:xxx:queue:requests 1 "test_request"
# → Worker 日志显示消费了新任务

# 3. 空闲超时退出测试
# 设置 DISTRIBUTED_WORKER_IDLE_TIMEOUT=10
# Worker 空等 10s 后自动退出

# 4. 多 Worker 争抢
python test_distributed.py  # 5 Worker
# → 任务均匀分布，无重复
```

---

## 实施步骤

| 步骤 | 文件 | 预估改动量 |
|------|------|-----------|
| 1. 提取 `_deserialize_request()` 重构 | `redis_priority_queue.py` | ~30 行移动 |
| 2. 新增 `get_blocking()`（含集群/脏清理/Redis<5.0 fallback） | `redis_priority_queue.py` | ~75 行新增 |
| 3. 新增 `get_blocking()` | `queue_manager.py` | ~15 行新增 |
| 4. 新增 `next_request_blocking()` | `scheduler.py` | ~15 行新增 |
| 5. 新增配置项 | `config.py` + `default_settings.py` | ~5 行 |
| 6. Engine 主循环改造（含 `time.monotonic()` / `_request_available` 跳过） | `engine.py` | ~55 行改动 |
| 7. 单元测试 | `tests/` | ~120 行新增 |
| 8. 集成测试验证 | `examples/ofweek_distributed/` | 复用现有 |

**总计**：~315 行改动/新增，预计 2-3 小时完成。
