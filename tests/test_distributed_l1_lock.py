"""L1: DistributedLock (7 cases)"""
import asyncio, pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.lock import DistributedLock

@pytest_asyncio.fixture
async def redis_str():
    r = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    yield r
    try: await r.aclose()
    except: pass

@pytest_asyncio.fixture
async def lock(redis_str):
    lk = DistributedLock(redis_str, "test_l1_lock")
    await redis_str.delete(lk._lock_key)
    yield lk
    await redis_str.delete(lk._lock_key)

@pytest.mark.asyncio
async def test_l1_acquire(lock):
    h = await lock.acquire(timeout=5)
    assert h and lock.acquired
    await lock.release(h)

@pytest.mark.asyncio
async def test_l2_contention(lock):
    h = await lock.acquire(timeout=5)
    l2 = DistributedLock(lock._redis, "test_l1_lock")
    assert await l2.acquire(timeout=1, retry=0) is None
    await lock.release(h)

@pytest.mark.asyncio
async def test_l3_release(lock):
    h = await lock.acquire(timeout=5)
    await lock.release(h)
    assert not await lock.is_locked()

@pytest.mark.asyncio
async def test_l4_bad_holder(lock):
    h = await lock.acquire(timeout=5)
    l2 = DistributedLock(lock._redis, "test_l1_lock")
    l2._holder_id = "bad"
    await l2.release("bad")
    assert await lock.is_locked()
    await lock.release(h)

@pytest.mark.asyncio
async def test_l5_reacquire(lock):
    h1 = await lock.acquire(timeout=5)
    await lock.release(h1)
    h2 = await lock.acquire(timeout=3)
    assert h2
    await lock.release(h2)

@pytest.mark.asyncio
async def test_l6_extend(lock):
    h = await lock.acquire(timeout=1)
    assert await lock.extend(10)
    assert await lock.is_locked()
    await lock.release(h)

@pytest.mark.asyncio
async def test_l7_concurrent(lock, redis_str):
    results = []
    async def worker(i):
        lk = DistributedLock(redis_str, "test_l1_lock")
        for _ in range(50):
            h = await lk.acquire(timeout=1, retry=0)
            if h:
                results.append(i)
                await asyncio.sleep(0.03)
                await lk.release(h)
                return
            await asyncio.sleep(0.03)
        results.append(-i)
    await asyncio.gather(*[worker(i) for i in range(5)])
    assert all(x >= 0 for x in results) and len(results) == 5
