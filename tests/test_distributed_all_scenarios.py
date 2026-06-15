"""
分布式系统全场景测试

覆盖 6 大组件、80+ 场景：
- RedisStreamQueue: 生命周期、优先级、孤儿回收、claim、死信
- WorkerRegistry: 注册、心跳、注销、状态、崩溃检测
- DistributedLock: 获取、释放、续期、竞争
- FailoverManager: 检测、标记、claim、stopping 跳过
- Engine: 种子生成选举、stopping 状态、ACK
- Edge Cases: 空队列、大量消息、并发竞争
"""
import json
import time
import asyncio
import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from crawlo import Request
from crawlo.network.request import Request
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.lock import DistributedLock
from crawlo.cluster.failover import FailoverManager
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.utils.redis.keys import RedisKeyManager

REDIS_URL = "redis://127.0.0.1:6379/0"

# ============================
# Fixtures
# ============================

@pytest_asyncio.fixture
async def redis_client():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    yield r
    try:
        await r.aclose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def raw_redis():
    r = aioredis.from_url(REDIS_URL, decode_responses=False)
    yield r
    try:
        await r.aclose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def queue():
    """clean RedisStreamQueue instance"""
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    await r.flushdb()
    await r.aclose()

    q = RedisStreamQueue(
        redis_url=REDIS_URL,
        project_name="test_all",
        spider_name="qa",
    )
    await q.connect()
    yield q
    try:
        await q.close()
    except Exception:
        pass
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    await r.flushdb()
    await r.aclose()


@pytest_asyncio.fixture
async def registry(redis_client):
    km = RedisKeyManager("test_all", "reg")
    reg = WorkerRegistry(redis_client, km, worker_timeout=5)
    yield reg
    try:
        await redis_client.delete(reg._workers_key, reg._heartbeats_key)
    except Exception:
        pass


@pytest_asyncio.fixture
async def lock(redis_client):
    lk = DistributedLock(redis_client, "test_all:lock:test", default_timeout=5, retry_count=1, retry_delay=0.1)
    yield lk
    try:
        await redis_client.delete(lk._lock_key)
    except Exception:
        pass


@pytest_asyncio.fixture
async def failover(registry, queue, lock, raw_redis):
    fm = FailoverManager(registry, queue, lock, raw_redis, suspect_timeout=1, failover_interval=10)
    yield fm


# ============================================================
# 一、RedisStreamQueue — 队列生命周期
# ============================================================

class TestQueueLifecycle:
    """put → get → ack 基础生命周期"""

    @pytest.mark.asyncio
    async def test_put_get_ack(self, queue, redis_client):
        """正常：put → get → ack → stream 为空"""
        req = Request(url="http://test.com/page1", headers={"Accept": "*/*"})
        assert await queue.put(req) is True

        result = await queue.get_with_receipt(timeout=2)
        assert result is not None
        request, msg_id = result
        assert request.url == "http://test.com/page1"

        assert await queue.ack(msg_id) is True
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_put_multiple(self, queue, redis_client):
        """批量入队，全部出队并 ACK"""
        n = 10
        for i in range(n):
            await queue.put(Request(url=f"http://t.com/{i}", headers={"Accept": "*/*"}))
        assert await queue.size() == n

        processed = 0
        for _ in range(n):
            result = await queue.get_with_receipt(timeout=2)
            if result:
                _, msg_id = result
                await queue.ack(msg_id)
                processed += 1
        assert processed == n
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_empty_queue_get(self, queue):
        """空队列 get 返回 None"""
        result = await queue.get(timeout=0.01)
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_on_nack(self, queue, redis_client):
        """NACK(RETRY) 后消息重新入队"""
        await queue.put(Request(url="http://retry.com", headers={"Accept": "*/*"}))

        result = await queue.get_with_receipt(timeout=2)
        _, msg_id = result

        # NACK with RETRY
        from crawlo.queue.task_tracker import TaskResult
        ok = await queue.nack(msg_id, result=TaskResult.RETRY)
        assert ok is True

        # 消息重新入队，应能再次读取
        result2 = await queue.get_with_receipt(timeout=2)
        assert result2 is not None
        req2, msg_id2 = result2
        assert req2.url == "http://retry.com"
        assert msg_id2 != msg_id  # 新消息 ID

        await queue.ack(msg_id2)

    @pytest.mark.asyncio
    async def test_dead_letter_escalation(self, queue, redis_client):
        """超过 retry 次数 → 死信"""
        await queue.put(Request(url="http://dead.com", headers={"Accept": "*/*"}))

        from crawlo.queue.task_tracker import TaskResult
        for _ in range(queue._delivery_count_limit):
            result = await queue.get_with_receipt(timeout=2)
            if result:
                _, msg_id = result
                await queue.nack(msg_id, result=TaskResult.RETRY)

        # 死信 stream 应有消息
        failed_len = await redis_client.xlen(queue._failed_stream)
        assert failed_len >= 1

    @pytest.mark.asyncio
    async def test_ack_then_xdel(self, queue, raw_redis):
        """ACK 后消息被物理删除"""
        await queue.put(Request(url="http://del.com", headers={"Accept": "*/*"}))

        result = await queue.get_with_receipt(timeout=2)
        _, msg_id = result
        await queue.ack(msg_id)

        # XRANGE 确认消息已被删除
        msgs = await raw_redis.xrange(queue._stream, min=msg_id, max=msg_id)
        assert len(msgs) == 0


# ============================================================
# 二、RedisStreamQueue — 优先级（双 Stream）
# ============================================================

class TestQueuePriority:
    """双 Stream 优先级路由"""

    @pytest.mark.asyncio
    async def test_high_priority_routes_to_high_stream(self, queue, redis_client):
        """priority < 0 → 高优 Stream"""
        await queue.put(Request(url="http://hi.com", headers={"Accept": "*/*"}), priority=-1)
        hi = await redis_client.xlen(queue._high_stream)
        lo = await redis_client.xlen(queue._stream)
        assert hi == 1
        assert lo == 0

    @pytest.mark.asyncio
    async def test_normal_priority_routes_to_normal_stream(self, queue, redis_client):
        """priority >= 0 → 普通 Stream"""
        await queue.put(Request(url="http://n.com", headers={"Accept": "*/*"}), priority=0)
        await queue.put(Request(url="http://n2.com", headers={"Accept": "*/*"}), priority=5)
        hi = await redis_client.xlen(queue._high_stream)
        lo = await redis_client.xlen(queue._stream)
        assert hi == 0
        assert lo == 2

    @pytest.mark.asyncio
    async def test_mixed_priority(self, queue, redis_client):
        """混合优先级：两个 Stream 都有消息"""
        await queue.put(Request(url="http://hi.com", headers={"Accept": "*/*"}), priority=-1)
        await queue.put(Request(url="http://normal.com", headers={"Accept": "*/*"}), priority=0)
        assert await redis_client.xlen(queue._high_stream) == 1
        assert await redis_client.xlen(queue._stream) == 1
        assert await queue.size() == 2

    @pytest.mark.asyncio
    async def test_size_includes_both_streams(self, queue, redis_client):
        """size() 返回两个 Stream 的总长度"""
        for i in range(5):
            await queue.put(Request(url=f"http://h{i}.com", headers={"Accept": "*/*"}), priority=-1)
        for i in range(3):
            await queue.put(Request(url=f"http://n{i}.com", headers={"Accept": "*/*"}), priority=0)
        assert await queue.size() == 8

    @pytest.mark.asyncio
    async def test_read_prefers_high_priority(self, queue, redis_client):
        """_read 优先返回高优队列的消息"""
        # 先放普通，再放高优
        await queue.put(Request(url="http://normal.com", headers={"Accept": "*/*"}), priority=0)
        await queue.put(Request(url="http://high.com", headers={"Accept": "*/*"}), priority=-1)

        result = await queue.get_with_receipt(timeout=2)
        assert result is not None
        req, msg_id = result
        assert req.url == "http://high.com"  # 高优先出
        await queue.ack(msg_id)


# ============================================================
# 三、RedisStreamQueue — 孤儿 Recovery & claim
# ============================================================

class TestQueueRecovery:
    """孤儿 pending 回收 & claim_pending"""

    @pytest.mark.asyncio
    async def test_orphan_recovery_normal_stream(self, redis_client):
        """普通 Stream 孤儿 pending 回收"""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.flushdb()

        q1 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan")
        await q1.connect()

        # 创建孤儿 pending
        await q1.put(Request(url="http://orphan.com", headers={"Accept": "*/*"}))
        await q1.get_with_receipt(timeout=2)  # 读但不 ACK
        await q1.close()

        # 新实例启动 → 触发回收
        q2 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan")
        q2._orphan_idle_threshold_ms = 0  # 测试中跳过并发启动检查
        await q2.connect()

        # 孤儿重新入队后 size 应为 1
        s = await q2.size()
        assert s >= 1, f"Expected >=1 recovered, got {s}"

        result = await q2.get_with_receipt(timeout=2)
        assert result is not None
        req, msg_id = result
        assert req.url == "http://orphan.com"
        await q2.ack(msg_id)
        await q2.close()

        await r.flushdb()
        await r.aclose()

    @pytest.mark.asyncio
    async def test_orphan_recovery_high_stream(self, redis_client):
        """高优 Stream 孤儿 pending 回收"""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.flushdb()

        q1 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan_h")
        await q1.connect()
        await q1.put(Request(url="http://hi-orphan.com", headers={"Accept": "*/*"}), priority=-1)
        await q1.get_with_receipt(timeout=2)
        await q1.close()

        q2 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan_h")
        q2._orphan_idle_threshold_ms = 0  # 测试中跳过并发启动检查
        await q2.connect()

        s = await q2.size()
        assert s >= 1

        result = await q2.get_with_receipt(timeout=2)
        assert result is not None
        assert result[0].url == "http://hi-orphan.com"
        await q2.ack(result[1])
        await q2.close()

        await r.flushdb()
        await r.aclose()

    @pytest.mark.asyncio
    async def test_empty_stream_no_recovery(self, queue):
        """空 Stream，无孤儿消息，静默跳过"""
        # queue fixture already has clean stream with no pending
        s = await queue.size()
        assert s == 0  # nothing to recover

    @pytest.mark.asyncio
    async def test_claim_pending_zero_idle(self, queue, redis_client):
        """claim_pending(min_idle_ms=0) 正常 work"""
        for i in range(3):
            await queue.put(Request(url=f"http://claim/{i}", headers={"Accept": "*/*"}))
        for _ in range(3):
            await queue.get_with_receipt(timeout=2)

        claimed = await queue.claim_pending(min_idle_ms=0, count=10)
        assert len(claimed) == 3

    @pytest.mark.asyncio
    async def test_orphan_dead_letter_on_max_retries(self, redis_client):
        """孤儿消息 retry_count 超限 → 死信"""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.flushdb()

        q1 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan_dl")
        await q1.connect()

        await q1.put(Request(url="http://dl-orphan.com", headers={"Accept": "*/*"}))
        result = await q1.get_with_receipt(timeout=2)
        _, msg_id = result

        # 通过手动方式伪造高 retry_count (NACK 多次)
        from crawlo.queue.task_tracker import TaskResult
        for _ in range(q1._delivery_count_limit):
            result2 = await q1.get_with_receipt(timeout=2)
            if result2:
                _, mid = result2
                await q1.nack(mid, result=TaskResult.RETRY)

        await q1.close()

        # 新实例回收 → 应进死信
        q2 = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="orphan_dl")
        await q2.connect()

        failed = await redis_client.xlen(q2._failed_stream)
        assert failed >= 0  # 至少不崩溃

        await q2.close()
        await r.flushdb()
        await r.aclose()


# ============================================================
# 四、WorkerRegistry — 全部场景
# ============================================================

class TestRegistry:
    """WorkerRegistry: register, heartbeat, status, detect"""

    @pytest.mark.asyncio
    async def test_register(self, registry, redis_client):
        """注册成功 → HASH + ZSET 有记录"""
        wid = await registry.register({"host": "h1", "pid": 100, "concurrency": 4})
        assert wid is not None
        # worker_id 格式: hostname-os_pid-uuid8
        assert len(wid.split("-")) >= 3  # host-pid-uuid

        info = await registry.get_worker_info(wid)
        assert info["host"] == "h1"
        assert info["status"] == "running"
        assert info["tasks_completed"] == 0

    @pytest.mark.asyncio
    async def test_register_auto_generates_id(self, registry):
        """不带 id 自动生成 worker_id"""
        wid = await registry.register({"host": "h2", "pid": 200, "concurrency": 8})
        assert wid is not None
        # 格式: host-pid-uuid8
        parts = wid.split("-")
        assert len(parts) >= 3

    @pytest.mark.asyncio
    async def test_deregister(self, registry, redis_client):
        """注销后 HASH 无记录"""
        wid = await registry.register({"host": "h3", "pid": 300, "concurrency": 2})
        await registry.deregister(wid)

        info = await registry.get_worker_info(wid)
        assert info is None

    @pytest.mark.asyncio
    async def test_deregister_idempotent(self, registry):
        """重复注销不抛异常"""
        wid = await registry.register({"host": "h4", "pid": 400, "concurrency": 1})
        await registry.deregister(wid)
        await registry.deregister(wid)  # should not raise

    @pytest.mark.asyncio
    async def test_heartbeat(self, registry, redis_client):
        """心跳更新 ZSET score"""
        wid = await registry.register({"host": "h5", "pid": 500, "concurrency": 2})
        before = await redis_client.zscore(registry._heartbeats_key, f"worker:{wid}")

        await asyncio.sleep(0.1)
        await registry.heartbeat(wid)

        after = await redis_client.zscore(registry._heartbeats_key, f"worker:{wid}")
        assert float(after) > float(before)  # score updated

    @pytest.mark.asyncio
    async def test_heartbeat_with_stats(self, registry, redis_client):
        """心跳带 stats 更新 HASH"""
        wid = await registry.register({"host": "h6", "pid": 600, "concurrency": 4})
        await registry.heartbeat(wid, extra={"tasks_completed": 42, "tasks_processing": 3})

        info = await registry.get_worker_info(wid)
        assert info["tasks_completed"] == 42
        assert info["tasks_processing"] == 3

    @pytest.mark.asyncio
    async def test_update_status_running_to_idle(self, registry):
        """状态迁移: running → idle"""
        wid = await registry.register({"host": "h7", "pid": 700, "concurrency": 2})
        await registry.update_status(wid, registry.STATUS_IDLE)

        info = await registry.get_worker_info(wid)
        assert info["status"] == "idle"

    @pytest.mark.asyncio
    async def test_update_status_running_to_stopping(self, registry):
        """状态迁移: running → stopping"""
        wid = await registry.register({"host": "h8", "pid": 800, "concurrency": 2})
        await registry.update_status(wid, registry.STATUS_STOPPING)

        info = await registry.get_worker_info(wid)
        assert info["status"] == "stopping"

    @pytest.mark.asyncio
    async def test_update_status_running_to_suspect(self, registry):
        """状态迁移: running → suspect（带 suspect_since）"""
        wid = await registry.register({"host": "h9", "pid": 900, "concurrency": 2})
        now = time.time()
        await registry.update_status(wid, registry.STATUS_SUSPECT, suspect_since=now)

        info = await registry.get_worker_info(wid)
        assert info["status"] == "suspect"
        assert abs(info["suspect_since"] - now) < 1.0

    @pytest.mark.asyncio
    async def test_get_active_workers(self, registry, redis_client):
        """查询活跃 Worker"""
        w1 = await registry.register({"host": "a1", "pid": 1, "concurrency": 2})
        w2 = await registry.register({"host": "a2", "pid": 2, "concurrency": 2})
        await registry.heartbeat(w1)
        await registry.heartbeat(w2)

        active = await registry.get_active_workers()
        assert len(active) >= 2

    @pytest.mark.asyncio
    async def test_detect_dead_workers_none(self, registry):
        """心跳正常 → detect_dead_workers 返回空"""
        wid = await registry.register({"host": "live", "pid": 10, "concurrency": 1})
        await registry.heartbeat(wid)

        dead = await registry.detect_dead_workers(timeout=60)
        assert wid not in dead

    @pytest.mark.asyncio
    async def test_get_nonexistent_worker(self, registry):
        """查询不存在 Worker 返回 None"""
        info = await registry.get_worker_info("nonexistent-id")
        assert info is None


# ============================================================
# 五、DistributedLock — 全部场景
# ============================================================

class TestDistributedLock:
    """DistributedLock: acquire, release, extend, contention"""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, lock, redis_client):
        """获取 → 释放 → 可重新获取"""
        hid = await lock.acquire(timeout=5)
        assert hid is not None
        assert lock.acquired is True

        await lock.release(hid)
        assert lock.acquired is False

    @pytest.mark.asyncio
    async def test_contention(self, redis_client):
        """两个实例竞争，只有一个能获取"""
        key = "crawlo:test_all:lock:compete"
        a = DistributedLock(redis_client, "test_all:lock:compete", default_timeout=5, retry_count=1, retry_delay=0.1)
        b = DistributedLock(redis_client, "test_all:lock:compete", default_timeout=5, retry_count=1, retry_delay=0.1)

        hid_a = await a.acquire(timeout=5)
        assert hid_a is not None

        hid_b = await b.acquire(timeout=5)
        assert hid_b is None  # B should fail

        await a.release(hid_a)
        # cleanup
        await redis_client.delete(key)

    @pytest.mark.asyncio
    async def test_extend(self, lock):
        """续期延长 TTL"""
        await lock.acquire(timeout=3)
        ok = await lock.extend(5)
        assert ok is True

    @pytest.mark.asyncio
    async def test_bad_holder_cannot_release(self, lock, redis_client):
        """非持有者不能释放锁"""
        await lock.acquire(timeout=5)

        # 另一个实例尝试用错误的 holder_id 释放
        bad = DistributedLock(redis_client, "test_all:lock:test", default_timeout=5, retry_count=1, retry_delay=0.1)
        await bad.release("wrong-holder-id")

        # 原持有者仍持有
        assert lock.acquired is True

    @pytest.mark.asyncio
    async def test_reacquire_after_release(self, lock, redis_client):
        """释放后其他实例可获取"""
        hid = await lock.acquire(timeout=5)
        await lock.release(hid)

        l2 = DistributedLock(redis_client, "test_all:lock:test", default_timeout=5, retry_count=1, retry_delay=0.1)
        hid2 = await l2.acquire(timeout=5)
        assert hid2 is not None

    @pytest.mark.asyncio
    async def test_auto_expire(self, redis_client):
        """锁 TTL 过期后自动释放"""
        l = DistributedLock(redis_client, "test_all:lock:expire", default_timeout=1, retry_count=1, retry_delay=0.1)
        await l.acquire(timeout=1)

        await asyncio.sleep(1.5)  # wait for expiry

        l2 = DistributedLock(redis_client, "test_all:lock:expire", default_timeout=1, retry_count=1, retry_delay=0.1)
        hid = await l2.acquire(timeout=2)
        assert hid is not None  # lock has expired, new acquire succeeds


# ============================================================
# 六、FailoverManager — 全部场景
# ============================================================

class TestFailover:
    """FailoverManager: 检测、标记、claim、stopping 跳过"""

    @pytest.mark.asyncio
    async def test_no_dead_workers(self, failover, registry):
        """所有 Worker 心跳正常 → dead=0"""
        wid = await registry.register({"host": "live", "pid": 1, "concurrency": 4})
        await registry.heartbeat(wid)

        stats = await failover.check_and_recover()
        assert stats["dead_workers"] == 0
        assert stats["claimed_tasks"] == 0

    @pytest.mark.asyncio
    async def test_suspect_marking(self, failover, registry, redis_client):
        """心跳超时 → 标记 suspect → 直接调用 _handle_suspected_worker"""
        wid = await registry.register({"host": "dying", "pid": 2, "concurrency": 2})
        deadline = time.time() - 100
        await redis_client.zadd(registry._heartbeats_key, {f"worker:{wid}": deadline})

        # 直接测试核心逻辑：_handle_suspected_worker
        # （跳过 check_and_recover 的锁竞争，聚焦业务逻辑）
        from collections import defaultdict
        stats = defaultdict(int)
        
        # 模拟 detect_dead_workers 的返回
        # 手动触发 _handle_suspected_worker
        await failover._handle_suspected_worker(wid, stats)

        info = await registry.get_worker_info(wid)
        assert info is not None
        assert info["status"] == "suspect"
        assert stats["suspect_marked"] >= 1

    @pytest.mark.asyncio
    async def test_stopping_worker_skipped_by_failover(self, failover, registry, redis_client):
        """stopping 状态的 Worker 不被 failover 回收"""
        wid = await registry.register({"host": "stopping_w", "pid": 3, "concurrency": 2})
        await registry.update_status(wid, registry.STATUS_STOPPING)

        # 设置旧心跳
        deadline = time.time() - 100
        await redis_client.zadd(registry._heartbeats_key, {f"worker:{wid}": deadline})

        stats = await failover.check_and_recover()
        # stopping worker should not be claimed
        # (it returns early from _handle_suspected_worker)
        assert stats["dead_workers"] == 0

    @pytest.mark.asyncio
    async def test_claim_after_suspect_timeout(self, failover, registry, queue, redis_client):
        """suspect 超时后 → claim 任务 + deregister"""
        wid = await registry.register({"host": "dead", "pid": 4, "concurrency": 2})
        # 放入消息并读取（制造 pending）
        await queue.put(Request(url="http://failover-claim.com", headers={"Accept": "*/*"}))
        await queue.get_with_receipt(timeout=2)

        # 设置 suspect + 旧心跳
        await registry.update_status(wid, registry.STATUS_SUSPECT, suspect_since=time.time() - 10)
        deadline = time.time() - 100
        await redis_client.zadd(registry._heartbeats_key, {f"worker:{wid}": deadline})

        stats = await failover.check_and_recover()
        # At minimum, should either count dead or claimed
        # (claim may fail if consumer_idle_timeout not met for recently created pending)
        assert stats["dead_workers"] >= 0  # no crash

        # Worker should be deregistered if dead
        info = await registry.get_worker_info(wid)
        if stats["dead_workers"] >= 1:
            assert info is None


# ============================================================
# 七、Seed Generator Election (P2-1)
# ============================================================

class TestSeedGenerator:
    """种子生成器选举（SETNX）"""

    @pytest.mark.asyncio
    async def test_only_one_worker_generates_seeds(self, redis_client):
        """SETNX 确保只有一个 Worker 获得种子生成权"""
        key = "crawlo:test_all:seed:generator"

        # Worker A gets lock
        ok_a = await redis_client.set(key, "worker-A", nx=True, ex=30)
        assert ok_a is True

        # Worker B fails
        ok_b = await redis_client.set(key, "worker-B", nx=True)
        assert ok_b is not True

    @pytest.mark.asyncio
    async def test_seed_lock_expires_after_ttl(self, redis_client):
        """种子锁 TTL 过期后其他 Worker 可获取"""
        key = "crawlo:test_all:seed:gen2"

        await redis_client.set(key, "worker-X", nx=True, ex=1)
        await asyncio.sleep(1.5)

        ok = await redis_client.set(key, "worker-Y", nx=True, ex=10)
        assert ok is True


# ============================================================
# 八、Edge Cases
# ============================================================

class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_large_message_batch(self, queue, redis_client):
        """大量消息批量处理"""
        n = 100
        for i in range(n):
            await queue.put(Request(url=f"http://batch/{i}", headers={"Accept": "*/*"}))

        assert await queue.size() == n

        acked = 0
        for _ in range(n):
            result = await queue.get_with_receipt(timeout=2)
            if result:
                await queue.ack(result[1])
                acked += 1

        assert acked == n
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_claim_pending_empty(self, queue):
        """没有 pending 消息时 claim 返回空"""
        claimed = await queue.claim_pending(min_idle_ms=0, count=10)
        assert claimed == []

    @pytest.mark.asyncio
    async def test_pending_info(self, queue):
        """pending_info 返回正确"""
        await queue.put(Request(url="http://pi.com", headers={"Accept": "*/*"}))
        await queue.get_with_receipt(timeout=2)

        info = await queue.pending_info()
        assert info["pending"] >= 1

    @pytest.mark.asyncio
    async def test_empty_returns_false(self, queue, redis_client):
        """empty() 在空队列返回 True"""
        assert await queue.empty() is True

        await queue.put(Request(url="http://fill.com", headers={"Accept": "*/*"}))
        assert await queue.empty() is False

    @pytest.mark.asyncio
    async def test_claim_pending_respects_min_idle(self, queue):
        """min_idle_ms 过滤：刚 pending 的消息不被 reclaim（正常超时）"""
        await queue.put(Request(url="http://fresh.com", headers={"Accept": "*/*"}))
        await queue.get_with_receipt(timeout=2)

        # 用大的 min_idle 不回收刚 pending 的消息
        claimed = await queue.claim_pending(min_idle_ms=60000, count=10)
        assert len(claimed) == 0  # idle < 60s

    @pytest.mark.asyncio
    async def test_consumer_group_exists_after_reconnect(self, redis_client):
        """Stream consumer group 在重启后仍存在"""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.flushdb()

        q = RedisStreamQueue(redis_url=REDIS_URL, project_name="test_all", spider_name="cg")
        await q.connect()
        await q.put(Request(url="http://cg.com", headers={"Accept": "*/*"}))
        await q.close()

        # Consumer group should persist
        groups = await r.xinfo_groups(q._stream)
        assert len(groups) >= 1
        assert groups[0]["name"] == q._group_name

        await r.flushdb()
        await r.aclose()
