# Queue Module Code Review

## Overview

**Module**: `crawlo/queue`  
**Files Reviewed**: 13 files  
**Purpose**: 队列管理模块，支持内存/Redis/磁盘三种队列类型，内置背压控制和优先级调度

---

## P1 Issues (Critical)

### 1. DiskQueue 优先级语义不一致

**Location**: `disk_queue.py:252-260, 388-393`

**Problem**:
```python
# put 方法注释：数值越大优先级越高
async def put(self, item: Any, priority: int = 0) -> bool:
    """优先级，数值越大优先级越高"""

# SQL 查询：ORDER BY priority DESC（数值大的先出队）
SELECT id, priority, data, created_at
FROM queue_items
WHERE processed = 0
ORDER BY priority DESC, created_at ASC
```

**Impact**: 与框架统一的优先级语义冲突（数值越小越优先）

**Fix**:
```python
# 修改为：数值越小优先级越高
ORDER BY priority ASC, created_at ASC
```

---

### 2. QueueManager.put() 中信号量释放逻辑错误

**Location**: `queue_manager.py:251-255`

**Problem**:
```python
except Exception as e:
    self.logger.error(f"Failed to enqueue request: {e}")
    if self._queue_semaphore:
        self._queue_semaphore.release()  # ❌ 错误：未获取就释放
    return False
```

如果入队在获取信号量之前失败（如序列化失败），会释放未获取的信号量，导致信号量计数异常。

**Fix**:
```python
# 跟踪是否已获取信号量
semaphore_acquired = False

# ... 获取信号量后
if self._queue_semaphore:
    await self._queue_semaphore.acquire()
    semaphore_acquired = True

# ... 异常处理
except Exception as e:
    self.logger.error(f"Failed to enqueue request: {e}")
    if semaphore_acquired and self._queue_semaphore:
        self._queue_semaphore.release()
    return False
```

---

### 3. RedisPriorityQueue.get() 中的时间计算错误

**Location**: `redis_priority_queue.py:326, 370`

**Problem**:
```python
start_time = asyncio.get_event_loop().time()  # ❌ Python 3.10+ 已弃用

# ...
if asyncio.get_event_loop().time() - start_time > timeout:
    return None
```

**Fix**:
```python
import asyncio

start_time = asyncio.get_event_loop().time()  # 或 time.time()

# 使用更现代的 API
try:
    async with asyncio.timeout(timeout):
        while True:
            # ... 获取逻辑
except asyncio.TimeoutError:
    return None
```

---

## P2 Issues (Important)

### 4. config.py 中背压配置重复逻辑

**Location**: `config.py:86-118`

**Problem**: Redis/Memory/Auto 三种模式的背压配置读取逻辑完全重复，违反 DRY 原则。

**Fix**: 提取通用方法
```python
def _get_backpressure_config(self, settings, prefix: str, defaults: dict) -> dict:
    """Extract backpressure config with prefix"""
    return {
        'max_queue_size': safe_get_config(
            settings, f'{prefix}_SCHEDULER_MAX_QUEUE_SIZE',
            safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', defaults['max_size']), int
        ),
        'backpressure_ratio': safe_get_config(
            settings, f'{prefix}_BACKPRESSURE_RATIO',
            safe_get_config(settings, 'BACKPRESSURE_RATIO', defaults['ratio'])
        ),
        # ... 其他配置
    }
```

---

### 5. memory_queue.py 中智能背压组件导入失败处理不完善

**Location**: `memory_queue.py:20-26`

**Problem**:
```python
try:
    from crawlo.backpressure.metrics_collector import BackpressureMetricsCollector
    # ...
    INTELLIGENT_BP_AVAILABLE = True
except ImportError:
    INTELLIGENT_BP_AVAILABLE = False
```

导入失败时静默降级，用户不知情。

**Fix**:
```python
except ImportError:
    INTELLIGENT_BP_AVAILABLE = False
    logger.debug("Intelligent backpressure not available: crawlo.backpressure module not found")
```

---

### 6. queue_helper.py 中硬编码配置值

**Location**: `queue_helper.py:112-136`

**Problem**:
```python
PRODUCTION = QueueHelper.use_redis_queue(
    host="127.0.0.1",  # ❌ 硬编码
    port=6379,
    queue_name="crawlo:production",
    # ...
)

HIGH_PERFORMANCE = QueueHelper.use_redis_queue(
    host="redis-cluster.example.com",  # ❌ 硬编码示例域名
    # ...
)
```

**Fix**: 移除或改为文档注释，不提供可直接使用的硬编码配置。

---

### 7. priority_calculator.py 中 _evict_oldest_urls 效率问题

**Location**: `priority_calculator.py:142-146`

**Problem**:
```python
def _evict_oldest_urls(self, count: int) -> None:
    """淘汰指定数量的 URL 记录（FIFO 策略）"""
    keys_to_remove = list(self.url_stats.keys())[:count]  # ❌ O(n) 转换
    for key in keys_to_remove:
        self.url_stats.pop(key, None)
```

字典在 Python 3.7+ 保持插入顺序，但 `list(keys())` 会创建完整副本。

**Fix**:
```python
def _evict_oldest_urls(self, count: int) -> None:
    """淘汰指定数量的 URL 记录（FIFO 策略）"""
    keys_iterator = iter(self.url_stats.keys())
    for _ in range(count):
        key = next(keys_iterator, None)
        if key is None:
            break
        self.url_stats.pop(key, None)
```

---

### 8. queue_status.py 中同步方法调用异步函数

**Location**: `queue_status.py:52-66`

**Problem**:
```python
def get_queue_stats(self) -> Dict[str, Any]:
    # ...
    if asyncio.iscoroutinefunction(self._queue.qsize):
        # 异步获取队列大小
        async def get_size():
            return await self._queue.qsize()
        # ❌ 注释说"不能直接调用异步函数"，但返回了占位符
        stats['current_queue_size'] = 'async_required'
```

**Fix**: 改为异步方法或移除该统计项
```python
async def get_queue_stats(self) -> Dict[str, Any]:
    # ...
    if asyncio.iscoroutinefunction(self._queue.qsize):
        stats['current_queue_size'] = await self._queue.qsize()
```

---

## P3 Issues (Minor)

### 9. DiskQueueConfig 命名不一致

**Location**: `disk_queue.py:53`

**Problem**: `WAL_mode` 应为 `wal_mode`（PEP 8 命名规范）

---

### 10. redis_priority_queue.py 中重复的 Project/Spider 日志

**Location**: `redis_priority_queue.py` 多处

**Problem**:
```python
logger.debug(f"Request enqueued with {self.serialization_format} serialization (Project: {self.key_manager.project_name}, Spider: {self.key_manager.spider_name}): {request.url}")
```

每条日志都包含 Project/Spider，日志冗长。建议在 logger 初始化时设置 extra 字段。

---

### 11. interfaces.py 中 clear() 效率低

**Location**: `interfaces.py:137-144`

**Problem**:
```python
async def clear(self) -> None:
    while not await self.empty():
        await self.get(timeout=0.01)  # ❌ 逐个出队清空
```

**Fix**: 子类应重写为批量操作（如 SQLite 的 `DELETE FROM`）

---

### 12. queue_manager.py 中多余的 type: ignore

**Location**: `queue_manager.py` 多处

**Problem**: 大量 `# type: ignore` 注释，说明类型注解不完善。

---

### 13. DiskQueue 中 processed 字段设计问题

**Location**: `disk_queue.py:212, 392-414`

**Problem**: 出队时标记 `processed=1` 而非删除记录，导致表持续增长。虽然有 TTL 清理，但会增加数据库大小。

**Fix**: 出队后直接 `DELETE` 或定期批量清理

---

## Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| **P1** | 3 | 优先级语义不一致、信号量释放错误、时间计算废弃 API |
| **P2** | 4 | 配置重复逻辑、导入失败无提示、硬编码配置、淘汰效率低 |
| **P3** | 6 | 命名规范、日志冗长、清空效率低、类型注解缺失 |

**Recommendation**: 
1. 优先修复 P1 #1（优先级语义），影响所有使用 DiskQueue 的项目
2. 修复 P1 #2（信号量释放），可能导致并发问题
3. 重构 P2 #4（背压配置），提升代码可维护性
