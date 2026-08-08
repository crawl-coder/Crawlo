"""
L1 Unit Tests: RedisStreamQueue (14 cases)
"""
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from crawlo.network.request import Request
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.queue.task_tracker import TaskResult

REDIS_URL = "redis://127.0.0.1:6379/0"


def make_request(url="http://test/default"):
    return Request(url=url)


@pytest_asyncio.fixture
async def redis():
    r = aioredis.from_url(REDIS_URL, decode_responses=False)
    yield r
    try:
        await r.aclose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def queue(redis):
    """Fresh RedisStreamQueue for each test."""
    q = RedisStreamQueue(REDIS_URL, "test_l1", "queue")
    await q.connect()
    yield q
    # Cleanup
    for s in (q._high_stream, q._low_stream, q._failed_stream):
        try:
            await q._redis.delete(s)
        except Exception:
            pass
    await q.close()


@pytest.mark.asyncio
async def test_q1_put(queue, redis):
    """L1-Q1: put single request"""
    req = make_request()
    ok = await queue.put(req, priority=0)
    assert ok
    hi_len = await redis.xlen(queue._high_stream)
    lo_len = await redis.xlen(queue._low_stream)
    assert hi_len + lo_len == 1


@pytest.mark.asyncio
async def test_q2_priority_streams(queue, redis):
    """L1-Q2: high priority → high stream, low → low stream"""
    ok1 = await queue.put(make_request("http://test/1"), priority=0)
    ok2 = await queue.put(make_request("http://test/2"), priority=1)
    assert ok1 and ok2
    hi = await redis.xlen(queue._high_stream)
    lo = await redis.xlen(queue._low_stream)
    assert hi == 1  # high priority → high stream
    assert lo == 1  # low priority → low stream


@pytest.mark.asyncio
async def test_q3_get_with_receipt(queue):
    """L1-Q3: get_with_receipt returns (Request, message_id) with meta"""
    await queue.put(make_request("http://test/get"), priority=0)
    result = await queue.get_with_receipt(timeout=3)
    assert result is not None
    req, msg_id = result
    assert req.url == "http://test/get"
    assert req.meta.get("__stream_message_id") == msg_id
    assert req.meta.get("__stream_retry_count") == 0
    await queue.ack(msg_id)


@pytest.mark.asyncio
async def test_q4_priority_order(queue):
    """L1-Q4: high priority dequeued before low priority"""
    await queue.put(make_request("http://test/low"), priority=1)
    await queue.put(make_request("http://test/high"), priority=0)
    # First get should be high
    r1 = await queue.get_with_receipt(timeout=3)
    assert r1 is not None and r1[0].url == "http://test/high"
    await queue.ack(r1[1])
    # Second get should be low
    r2 = await queue.get_with_receipt(timeout=3)
    assert r2 is not None and r2[0].url == "http://test/low"
    await queue.ack(r2[1])


@pytest.mark.asyncio
async def test_q5_ack(queue, redis):
    """L1-Q5: ack removes from pending"""
    await queue.put(make_request("http://test/ack"), priority=0)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    await queue.ack(r[1])
    # XPENDING should be empty
    info = await queue.pending_info()
    assert info.get("total", 999) == 0


@pytest.mark.asyncio
async def test_q6_nack_retry(queue):
    """L1-Q6: NACK+RETRY re-enqueues with incremented retry count"""
    await queue.put(make_request("http://test/retry"), priority=0)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    msg_id = r[1]
    ok = await queue.nack(msg_id, error="test", result=TaskResult.RETRY)
    # Should be re-enqueued
    r2 = await queue.get_with_receipt(timeout=3)
    assert r2 is not None
    assert r2[0].meta.get("__stream_retry_count") == 1
    await queue.ack(r2[1])


@pytest.mark.asyncio
async def test_q7_dead_letter(queue, redis):
    """L1-Q7: NACK after max retries → dead letter stream"""
    await queue.put(make_request("http://test/dead"), priority=0)
    msg_id = None
    for i in range(queue._delivery_count_limit + 1):
        r = await queue.get_with_receipt(timeout=3)
        if r:
            msg_id = r[1]
            if i < queue._delivery_count_limit - 1:
                await queue.nack(msg_id, result=TaskResult.RETRY)
            else:
                await queue.nack(msg_id, result=TaskResult.DEAD_LETTER)
    # Dead letter stream should have messages
    info = await redis.xinfo_stream(queue._failed_stream)
    assert info and info.get("length", 0) >= 1


@pytest.mark.asyncio
async def test_q8_nack_ack_terminal(queue, redis):
    """L1-Q8: NACK with ACK (terminal error) → direct XACK, no retry"""
    await queue.put(make_request("http://test/terminal"), priority=0)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    await queue.nack(r[1], result=TaskResult.ACK)
    # No retry — should be gone
    r2 = await queue.get_with_receipt(timeout=0.5)
    assert r2 is None


@pytest.mark.asyncio
async def test_q9_empty_queue(queue):
    """L1-Q9: empty queue returns None"""
    r = await queue.get_with_receipt(timeout=0.2)
    assert r is None


@pytest.mark.asyncio
async def test_q10_pending_info(queue):
    """L1-Q10: pending_info shows pending count"""
    await queue.put(make_request("http://test/pending"), priority=0)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    info = await queue.pending_info()
    assert info.get("total", 0) >= 1
    await queue.ack(r[1])


@pytest.mark.asyncio
async def test_q11_size(queue):
    """L1-Q11: size() matches XLEN"""
    for i in range(5):
        await queue.put(make_request(f"http://test/size/{i}"), priority=1)
    # Get fresh size from Redis
    r = aioredis.from_url(REDIS_URL, decode_responses=False)
    hi = await r.xlen(queue._high_stream)
    lo = await r.xlen(queue._low_stream)
    await r.aclose()
    qs = await queue.size()
    assert qs == hi + lo == 5


@pytest.mark.asyncio
async def test_q12_claim_pending(queue):
    """L1-Q12: claim_pending recovers timed-out messages"""
    await queue.put(make_request("http://test/claim"), priority=0)
    # Get but don't ACK (simulate crash)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    # Force a different consumer to claim with min_idle_ms=0
    claimed = await queue.claim_pending(min_idle_ms=0, count=10)
    assert len(claimed) >= 1


@pytest.mark.asyncio
async def test_q13_batch_100(queue):
    """L1-Q13: batch 100 put/get, no data loss"""
    N = 100
    urls = set()
    for i in range(N):
        await queue.put(make_request(f"http://test/batch/{i}"), priority=1)
    for _ in range(N + 10):
        r = await queue.get_with_receipt(timeout=2)
        if r:
            urls.add(r[0].url)
            await queue.ack(r[1])
        if len(urls) >= N:
            break
    assert len(urls) == N


@pytest.mark.asyncio
async def test_q14_reconnect_after_delete(queue, redis):
    """L1-Q14: connect() re-creates Consumer Group after stream deletion"""
    # Delete stream externally
    await redis.delete(queue._high_stream)
    # Force reconnect
    queue._connected = False
    await queue.connect()
    # Put and get should still work
    await queue.put(make_request("http://test/reconnect"), priority=0)
    r = await queue.get_with_receipt(timeout=3)
    assert r is not None
    await queue.ack(r[1])
