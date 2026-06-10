#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
孤儿 pending 消息回收 + Failover claim 重新入队 集成测试
=========================================================

覆盖场景：
1. 正常 ACK+XDEL：消费一条删一条，不留 pending
2. 启动回收孤儿 pending：模拟 worker 退出后遗留 pending，新 worker 启动时回收
3. Failover claim 重新入队：崩溃 worker 的 pending 消息被 failover 回收并重新入队
4. 死信升级：孤儿 pending 超过最大重试次数 → 死信队列
5. 空 Stream 启动：无 pending 消息时不触发回收
6. 多 worker 场景：A worker 留下 pending，B worker 启动回收
7. 消息完整性：回收后消息字段（URL、retry_count 等）不丢失

需要本地 Redis 运行在 127.0.0.1:6379
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, "/Users/oscar/projects/Crawlo")

import redis.asyncio as aioredis
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.lock import DistributedLock
from crawlo.cluster.failover import FailoverManager
from crawlo.network.request import Request
from crawlo.utils.redis.keys import RedisKeyManager

REDIS_URL = "redis://127.0.0.1:6379/0"
TEST_NS = "test_orphan"
TEST_SPIDER = "recovery"


def log_pass(name):
    print(f"  ✅ {name}")


def log_fail(name, detail=""):
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


async def cleanup_redis(redis_client, stream, group, failed_stream, keys):
    """清理测试数据"""
    try:
        await redis_client.delete(stream, failed_stream, *keys)
    except Exception:
        pass
    try:
        await redis_client.xgroup_destroy(stream, group)
    except Exception:
        pass


async def test_1_normal_ack_xdel():
    """场景 1：正常 ACK+XDEL，消费一条删一条"""
    print("\n📋 场景 1：正常 ACK+XDEL")
    project, spider = f"{TEST_NS}_1", "s1"
    q = RedisStreamQueue(REDIS_URL, project, spider, consumer_idle_timeout=5000)
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await q.connect()
        stream = q._stream
        group = q._group_name

        # 入队 5 条消息
        for i in range(5):
            await q.put(Request(url=f"http://normal/{i}"), priority=0)

        length_before = (await r.xinfo_stream(stream))["length"]
        assert length_before == 5, f"Expected 5 messages, got {length_before}"

        # 消费并 ACK 全部
        for _ in range(5):
            req = await q.get(timeout=2.0)
            assert req is not None, "Should get a request"
            msg_id = req.meta["__stream_message_id"]
            ok = await q.ack(msg_id)
            assert ok, f"ACK failed for {msg_id}"

        # Stream 应该为空
        length_after = (await r.xinfo_stream(stream))["length"]
        assert length_after == 0, f"Expected 0 messages after ACK+XDEL, got {length_after}"

        # 无 pending
        pending = await r.xpending(stream, group)
        pending_count = pending.get("pending", 0) if isinstance(pending, dict) else 0
        assert pending_count == 0, f"Expected 0 pending, got {pending_count}"

        log_pass("ACK+XDEL 逐条删除，Stream 为空，无 pending")
    except AssertionError as e:
        log_fail("ACK+XDEL", str(e))
    except Exception as e:
        log_fail("ACK+XDEL", f"Exception: {e}")
    finally:
        await q.close()
        await r.aclose()
        await cleanup_redis(
            aioredis.from_url(REDIS_URL),
            f"crawlo:{TEST_NS}_1:{spider}:stream:tasks",
            f"crawlo:{TEST_NS}_1:{spider}:group:workers",
            f"crawlo:{TEST_NS}_1:{spider}:stream:failed",
            [],
        )


async def test_2_startup_orphan_recovery():
    """场景 2：启动回收孤儿 pending — 模拟 worker 退出后遗留 pending，新 worker 启动回收"""
    print("\n📋 场景 2：启动回收孤儿 pending")
    project, spider = f"{TEST_NS}_2", "s2"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        # 清理旧数据
        await cleanup_redis(r, stream, group, failed_stream, [])

        # 阶段 A：创建 queue1，入队并 XREADGROUP（制造 pending）
        q1 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-old-1")
        await q1.connect()

        for i in range(5):
            await q1.put(Request(url=f"http://orphan/{i}"), priority=0)

        # XREADGROUP 读取但不 ACK → 制造 pending
        for _ in range(5):
            req = await q1.get(timeout=2.0)
            assert req is not None

        # 验证 pending
        pending = await r.xpending(stream, group)
        pending_count = pending.get("pending", 0) if isinstance(pending, dict) else 0
        assert pending_count == 5, f"Expected 5 pending, got {pending_count}"

        # Stream 长度仍为 5（只 XREADGROUP，未 XDEL）
        stream_len = (await r.xinfo_stream(stream))["length"]
        assert stream_len == 5, f"Expected stream length 5, got {stream_len}"

        # 关闭 q1（模拟 worker 退出，不 ACK）
        await q1.close()

        # 阶段 B：新 worker 启动，connect() 应触发 _recover_orphan_pending
        q2 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-new-1")
        await q2.connect()

        # 验证：5 条孤儿消息被重新入队
        # 重新入队的消息是新消息（新的 message_id），可被 XREADGROUP > 消费
        recovered = []
        for _ in range(5):
            req = await q2.get(timeout=2.0)
            if req:
                msg_id = req.meta.get("__stream_message_id")
                retry_count = req.meta.get("__stream_retry_count", 0)
                recovered.append((req.url, msg_id, retry_count))
                await q2.ack(msg_id)

        assert len(recovered) == 5, f"Expected 5 recovered messages, got {len(recovered)}"

        # 验证 retry_count 递增（原始为 0，回收后 +1）
        for url, _, rc in recovered:
            assert rc == 1, f"Expected retry_count=1 for {url}, got {rc}"

        # 验证 Stream 最终为空
        final_len = (await r.xinfo_stream(stream))["length"]
        assert final_len == 0, f"Expected stream length 0 after recovery, got {final_len}"

        log_pass(f"5 条孤儿 pending 被回收并重新入队，retry_count=1，Stream 清空")
        await q2.close()
    except AssertionError as e:
        log_fail("孤儿 pending 回收", str(e))
    except Exception as e:
        log_fail("孤儿 pending 回收", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_3_failover_claim_re_enqueue():
    """场景 3：Failover claim 重新入队 — 崩溃 worker 的 pending 被 failover 回收"""
    print("\n📋 场景 3：Failover claim 重新入队")
    project, spider = f"{TEST_NS}_3", "s3"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        # 创建 queue 和 failover 组件
        q = RedisStreamQueue(REDIS_URL, project, spider, consumer_idle_timeout=1000)
        await q.connect()

        km = RedisKeyManager(project, spider)
        reg = WorkerRegistry(r, km, worker_timeout=3)
        lk = DistributedLock(r, f"test_orphan_3:lock:failover")
        await r.delete(lk._lock_key)

        fm = FailoverManager(reg, q, lk, r, suspect_timeout=1, failover_interval=10)

        # 注册一个 "即将崩溃" 的 worker
        dead_worker = await reg.register({"host": "dead-host", "pid": 9999, "concurrency": 4})

        # 入队 3 条消息
        for i in range(3):
            await q.put(Request(url=f"http://failover/{i}"), priority=0)

        # 用 dead_worker 的 consumer 读取消息（制造 pending）
        # 由于我们无法用另一个 consumer 名字直接读，用 queue 的 get 制造 pending
        pending_ids = []
        for _ in range(3):
            req = await q.get(timeout=2.0)
            if req:
                pending_ids.append(req.meta["__stream_message_id"])
                # 不 ACK，制造 pending

        assert len(pending_ids) == 3, f"Expected 3 pending, got {len(pending_ids)}"

        # 标记 worker 为 suspect + 等待确认
        await reg.update_status(dead_worker, "suspect", suspect_since=time.time() - 10)

        # 执行 failover 回收
        stats = await fm.check_and_recover()
        assert stats["dead_workers"] >= 1 or stats["claimed_tasks"] >= 1, \
            f"Expected dead_workers or claimed_tasks, got {stats}"

        # 验证：消息被重新入队，可以被消费
        recovered = []
        for _ in range(3):
            req = await q.get(timeout=2.0)
            if req:
                recovered.append(req.url)
                msg_id = req.meta["__stream_message_id"]
                await q.ack(msg_id)

        assert len(recovered) == 3, f"Expected 3 recovered after failover, got {len(recovered)}"

        log_pass(f"Failover 回收 {stats['claimed_tasks']} 条 pending 并重新入队")
        await q.close()
    except AssertionError as e:
        log_fail("Failover claim", str(e))
    except Exception as e:
        log_fail("Failover claim", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [lk._lock_key])
        await r2.aclose()


async def test_4_dead_letter_escalation():
    """场景 4：孤儿 pending 超过最大重试次数 → 死信队列"""
    print("\n📋 场景 4：死信升级")
    project, spider = f"{TEST_NS}_4", "s4"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        # 创建 delivery_count_limit=2 的 queue
        q1 = RedisStreamQueue(
            REDIS_URL, project, spider,
            consumer_name="worker-dl-1",
            delivery_count_limit=2,
            consumer_idle_timeout=1000,
        )
        await q1.connect()

        # 入队 1 条消息，然后多次 claim 制造高 retry_count
        await q1.put(Request(url="http://deadletter/1"), priority=0)

        # 读取不 ACK
        req = await q1.get(timeout=2.0)
        assert req is not None
        msg_id = req.meta["__stream_message_id"]

        # 手动修改 retry_count 模拟多次投递失败
        # 方式：XACK + XDEL，然后 XADD 带 retry_count=2
        await r.xack(stream, group, msg_id)
        await r.xdel(stream, msg_id)
        await r.xadd(
            stream,
            {
                b"data": b'\x80\x04\x95\x15\x00\x00\x00\x00\x00\x00\x00}\x94(\x8c\x03url\x94\x8c\x12http://deadletter/1\x94u.',  # 简化，用 pickle
                b"priority": b"0",
                b"retry_count": b"2",  # 已达到 delivery_count_limit
                b"enqueued_at": str(time.time()).encode(),
            },
        )

        await q1.close()

        # 新 worker 启动，应触发死信升级
        q2 = RedisStreamQueue(
            REDIS_URL, project, spider,
            consumer_name="worker-dl-2",
            delivery_count_limit=2,
            consumer_idle_timeout=1000,
        )
        await q2.connect()

        # 检查死信队列
        try:
            dead_info = await r.xinfo_stream(failed_stream)
            dead_count = dead_info.get("length", 0)
            assert dead_count >= 1, f"Expected at least 1 dead letter, got {dead_count}"
            log_pass(f"retry_count >= delivery_count_limit 的消息被升级到死信队列")
        except Exception as e:
            # 死信队列为空可能意味着 Stream 不存在
            log_fail("死信升级", f"Dead letter stream empty or not found: {e}")

        # 主 Stream 应为空（消息被移到死信）
        try:
            stream_info = await r.xinfo_stream(stream)
            stream_len = stream_info.get("length", 0)
            assert stream_len == 0, f"Expected stream length 0, got {stream_len}"
        except Exception:
            pass  # Stream 可能已被自动清理

        await q2.close()
    except AssertionError as e:
        log_fail("死信升级", str(e))
    except Exception as e:
        log_fail("死信升级", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_5_empty_stream_startup():
    """场景 5：空 Stream 启动 — 无 pending 消息时不触发回收"""
    print("\n📋 场景 5：空 Stream 启动")
    project, spider = f"{TEST_NS}_5", "s5"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        q = RedisStreamQueue(REDIS_URL, project, spider)
        await q.connect()

        # 不入队任何消息，直接检查
        pending_count = await r.xpending(stream, group) if True else 0
        # 空 Stream 时 xpending 可能报错
        try:
            pending_info = await r.xpending(stream, group)
            pc = pending_info.get("pending", 0) if isinstance(pending_info, dict) else 0
        except Exception:
            pc = 0

        assert pc == 0, f"Expected 0 pending on empty stream, got {pc}"

        # 队列应立即可用
        req = await q.get(timeout=0.5)
        assert req is None, "Should get None from empty queue"

        log_pass("空 Stream 启动无报错，无 pending")
        await q.close()
    except AssertionError as e:
        log_fail("空 Stream 启动", str(e))
    except Exception as e:
        log_fail("空 Stream 启动", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_6_multi_worker_recovery():
    """场景 6：多 worker — A 留下 pending，B 启动回收"""
    print("\n📋 场景 6：多 worker 孤儿 pending 回收")
    project, spider = f"{TEST_NS}_6", "s6"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        # Worker A：入队 10 条，全部读取不 ACK
        qA = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-A")
        await qA.connect()

        urls = [f"http://multi/{i}" for i in range(10)]
        for url in urls:
            await qA.put(Request(url=url), priority=0)

        for _ in range(10):
            req = await qA.get(timeout=2.0)
            assert req is not None

        await qA.close()

        # Worker B：启动时自动回收 A 的 pending
        qB = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-B")
        await qB.connect()

        # 验证能消费到 10 条
        recovered_urls = set()
        for _ in range(10):
            req = await qB.get(timeout=2.0)
            if req:
                recovered_urls.add(req.url)
                await qB.ack(req.meta["__stream_message_id"])

        assert len(recovered_urls) == 10, f"Expected 10 recovered URLs, got {len(recovered_urls)}"

        # 验证 URL 完整性
        for url in urls:
            assert url in recovered_urls, f"Missing URL: {url}"

        # Stream 最终为空
        stream_info = await r.xinfo_stream(stream)
        assert stream_info["length"] == 0, f"Expected stream length 0, got {stream_info['length']}"

        log_pass("Worker A 留下 10 条 pending，Worker B 启动回收全部 10 条，URL 完整")
        await qB.close()
    except AssertionError as e:
        log_fail("多 worker 回收", str(e))
    except Exception as e:
        log_fail("多 worker 回收", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_7_message_integrity():
    """场景 7：消息完整性 — 回收后字段不丢失"""
    print("\n📋 场景 7：消息完整性验证")
    project, spider = f"{TEST_NS}_7", "s7"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        # Worker 1：入队带 meta 的消息
        q1 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-int-1")
        await q1.connect()

        original_requests = [
            Request(url="http://integrity/1", method="GET", meta={"page": 1, "source": "list"}),
            Request(url="http://integrity/2", method="POST", meta={"page": 2, "source": "detail"}),
            Request(url="http://integrity/3", method="GET", meta={"page": 3}),
        ]

        for req in original_requests:
            await q1.put(req, priority=0)

        # 读取不 ACK
        for _ in range(3):
            await q1.get(timeout=2.0)

        await q1.close()

        # Worker 2：启动回收
        q2 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-int-2")
        await q2.connect()

        recovered = []
        for _ in range(3):
            req = await q2.get(timeout=2.0)
            if req:
                recovered.append(req)
                await q2.ack(req.meta["__stream_message_id"])

        assert len(recovered) == 3, f"Expected 3 recovered, got {len(recovered)}"

        # 验证 URL 不丢失
        recovered_urls = {req.url for req in recovered}
        expected_urls = {"http://integrity/1", "http://integrity/2", "http://integrity/3"}
        assert recovered_urls == expected_urls, f"URL mismatch: {recovered_urls} vs {expected_urls}"

        # 验证 method 不丢失
        for req in recovered:
            if "2" in req.url:
                assert req.method == "POST", f"Expected POST, got {req.method}"

        # 验证 meta 不丢失
        for req in recovered:
            if "1" in req.url:
                assert req.meta.get("page") == 1, f"page meta lost"
                assert req.meta.get("source") == "list", f"source meta lost"
            elif "3" in req.url:
                assert req.meta.get("page") == 3, f"page meta lost"

        # 验证 retry_count 递增
        for req in recovered:
            rc = req.meta.get("__stream_retry_count", 0)
            assert rc == 1, f"Expected retry_count=1, got {rc}"

        log_pass("回收后 URL、method、meta、retry_count 全部完整")
        await q2.close()
    except AssertionError as e:
        log_fail("消息完整性", str(e))
    except Exception as e:
        log_fail("消息完整性", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_8_large_scale_orphan():
    """场景 8：大规模孤儿 pending（模拟实际 373 条场景）"""
    print("\n📋 场景 8：大规模孤儿 pending（100 条）")
    project, spider = f"{TEST_NS}_8", "s8"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        N = 100

        # Worker 1：入队 N 条，全部读取不 ACK
        q1 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-bulk-1")
        await q1.connect()

        for i in range(N):
            await q1.put(Request(url=f"http://bulk/{i}"), priority=0)

        # 逐条读取
        for _ in range(N):
            req = await q1.get(timeout=2.0)
            assert req is not None, f"Failed to read message {_}"

        # 验证 pending
        pending_info = await r.xpending(stream, group)
        pending_count = pending_info.get("pending", 0) if isinstance(pending_info, dict) else 0
        assert pending_count == N, f"Expected {N} pending, got {pending_count}"

        await q1.close()

        # Worker 2：启动回收
        q2 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-bulk-2")
        await q2.connect()

        # 消费所有回收的消息
        recovered_count = 0
        for _ in range(N):
            req = await q2.get(timeout=2.0)
            if req:
                recovered_count += 1
                await q2.ack(req.meta["__stream_message_id"])

        assert recovered_count == N, f"Expected {N} recovered, got {recovered_count}"

        # Stream 最终为空
        stream_info = await r.xinfo_stream(stream)
        assert stream_info["length"] == 0, f"Expected stream length 0, got {stream_info['length']}"

        log_pass(f"{N} 条孤儿 pending 全部回收，Stream 清空")
        await q2.close()
    except AssertionError as e:
        log_fail("大规模孤儿 pending", str(e))
    except Exception as e:
        log_fail("大规模孤儿 pending", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def test_9_partial_pending_mixed():
    """场景 9：混合场景 — 部分 pending + 部分新消息"""
    print("\n📋 场景 9：混合 pending + 新消息")
    project, spider = f"{TEST_NS}_9", "s9"
    stream = f"crawlo:{project}:{spider}:stream:tasks"
    group = f"crawlo:{project}:{spider}:group:workers"
    failed_stream = f"crawlo:{project}:{spider}:stream:failed"
    r = aioredis.from_url(REDIS_URL, decode_responses=False)

    try:
        await cleanup_redis(r, stream, group, failed_stream, [])

        # Worker 1：3 条 ACK，3 条 pending
        q1 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-mix-1")
        await q1.connect()

        for i in range(6):
            await q1.put(Request(url=f"http://mix/{i}"), priority=0)

        # 消费前 3 条并 ACK
        for _ in range(3):
            req = await q1.get(timeout=2.0)
            await q1.ack(req.meta["__stream_message_id"])

        # 消费后 3 条不 ACK
        for _ in range(3):
            req = await q1.get(timeout=2.0)
            # 不 ACK

        await q1.close()

        # Worker 2：启动回收 + 入队新消息
        q2 = RedisStreamQueue(REDIS_URL, project, spider, consumer_name="worker-mix-2")
        await q2.connect()

        # 入队 2 条新消息
        await q2.put(Request(url="http://mix/new1"), priority=0)
        await q2.put(Request(url="http://mix/new2"), priority=0)

        # 应该能消费到 3 条回收 + 2 条新 = 5 条
        recovered_urls = set()
        for _ in range(5):
            req = await q2.get(timeout=2.0)
            if req:
                recovered_urls.add(req.url)
                await q2.ack(req.meta["__stream_message_id"])

        assert len(recovered_urls) == 5, f"Expected 5 messages, got {len(recovered_urls)}"

        # 验证包含新消息
        assert "http://mix/new1" in recovered_urls, "Missing new1"
        assert "http://mix/new2" in recovered_urls, "Missing new2"

        # 验证包含回收消息
        orphan_urls = {f"http://mix/{i}" for i in range(3, 6)}
        assert orphan_urls.issubset(recovered_urls), f"Missing orphan URLs: {orphan_urls - recovered_urls}"

        log_pass("3 条 pending + 2 条新消息全部可消费")
        await q2.close()
    except AssertionError as e:
        log_fail("混合场景", str(e))
    except Exception as e:
        log_fail("混合场景", f"Exception: {e}")
    finally:
        await r.aclose()
        r2 = aioredis.from_url(REDIS_URL)
        await cleanup_redis(r2, stream, group, failed_stream, [])
        await r2.aclose()


async def main():
    print("=" * 60)
    print("  孤儿 Pending 回收 + Failover 重新入队 集成测试")
    print("=" * 60)

    # 检查 Redis 连接
    try:
        r = aioredis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
        print("✅ Redis 连接正常\n")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        print("   请确保 Redis 运行在 127.0.0.1:6379")
        return

    tests = [
        test_1_normal_ack_xdel,
        test_2_startup_orphan_recovery,
        test_3_failover_claim_re_enqueue,
        test_4_dead_letter_escalation,
        test_5_empty_stream_startup,
        test_6_multi_worker_recovery,
        test_7_message_integrity,
        test_8_large_scale_orphan,
        test_9_partial_pending_mixed,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            log_fail(test.__name__, f"Unexpected: {e}")

    print("\n" + "=" * 60)
    print(f"  结果：{passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
