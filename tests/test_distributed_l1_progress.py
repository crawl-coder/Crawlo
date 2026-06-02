"""L1: ProgressAggregator (5 cases)"""
import pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.progress import ProgressAggregator
from crawlo.utils.redis.keys import RedisKeyManager

@pytest_asyncio.fixture
async def r():
    rr = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    yield rr
    try: await rr.aclose()
    except: pass

@pytest_asyncio.fixture
async def pa(r):
    p = ProgressAggregator(r, RedisKeyManager("test_l1", "prog"))
    await p.reset()
    yield p
    await p.reset()

@pytest.mark.asyncio
async def test_p1(pa):
    await pa.report("w1", {"completed": 10, "failed": 2})
    assert (await pa.get_global_stats())["total_completed"] == 10

@pytest.mark.asyncio
async def test_p2(pa):
    await pa.report("w1", {"completed": 10})
    await pa.report("w2", {"completed": 5})
    assert (await pa.get_global_stats())["total_completed"] == 15

@pytest.mark.asyncio
async def test_p3(pa):
    await pa.report("w1", {"completed": 100})
    ws = await pa.get_worker_stats("w1")
    assert ws and ws["completed"] == 100

@pytest.mark.asyncio
async def test_p4(pa):
    await pa.report("w1", {"completed": 50})
    assert (await pa.estimate_completion(100))["percent"] == 50.0

@pytest.mark.asyncio
async def test_p5(pa):
    await pa.report("w1", {"completed": 999})
    await pa.reset()
    assert (await pa.get_global_stats())["total_completed"] == 0
