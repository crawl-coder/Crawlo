"""L1: DistributedRateLimiter (7 cases)"""
import pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.rate_limiter import DistributedRateLimiter

@pytest_asyncio.fixture
async def redis_str():
    r = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    yield r
    try: await r.aclose()
    except: pass

@pytest_asyncio.fixture
async def limiter(redis_str):
    rl = DistributedRateLimiter(redis_str, "crawlo:test_l1:rate", enabled=True, default_rate=10, default_capacity=10)
    await redis_str.delete("crawlo:test_l1:rate:test", "crawlo:test_l1:rate:test:ts")
    yield rl
    await redis_str.delete("crawlo:test_l1:rate:test", "crawlo:test_l1:rate:test:ts")

@pytest.mark.asyncio
async def test_rl1_burst(limiter):
    p = 0
    for _ in range(10):
        if await limiter.acquire("test", rate=10, capacity=10): p += 1
    assert p == 10

@pytest.mark.asyncio
async def test_rl2_overflow(limiter):
    for _ in range(10): await limiter.acquire("test", rate=10, capacity=10)
    assert not await limiter.acquire("test", rate=10, capacity=10)

@pytest.mark.asyncio
async def test_rl3_wait(limiter):
    for _ in range(10): await limiter.acquire("test", rate=10, capacity=10)
    assert await limiter.wait_and_acquire("test", rate=10, capacity=10, timeout=2)

@pytest.mark.asyncio
async def test_rl4_zero(limiter):
    for _ in range(20): assert await limiter.acquire("test", rate=0)

@pytest.mark.asyncio
async def test_rl5_disabled(limiter):
    limiter.enabled = False
    assert await limiter.acquire("test", rate=1, capacity=1)

@pytest.mark.asyncio
async def test_rl6_set(limiter):
    await limiter.set_rate("test", 1, capacity=1)
    assert await limiter.acquire("test", rate=1, capacity=1)
    assert not await limiter.acquire("test", rate=1, capacity=1)

@pytest.mark.asyncio
async def test_rl7_remove(limiter):
    await limiter.set_rate("test", 1, capacity=1)
    await limiter.remove_rate("test")
    p = 0
    for _ in range(10):
        if await limiter.acquire("test", rate=10, capacity=10): p += 1
    assert p == 10
