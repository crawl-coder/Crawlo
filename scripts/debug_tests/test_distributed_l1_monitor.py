"""L1: ClusterMonitor (4 cases)"""
import pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.progress import ProgressAggregator
from crawlo.cluster.monitor import ClusterMonitor
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.utils.redis.keys import RedisKeyManager

R = "redis://127.0.0.1:6379/0"

@pytest_asyncio.fixture
async def redis_str():
    rr = aioredis.from_url(R, decode_responses=True)
    yield rr
    try: await rr.aclose()
    except: pass

@pytest_asyncio.fixture
async def setup(redis_str):
    km = RedisKeyManager("test_l1", "mon")
    reg = WorkerRegistry(redis_str, km, worker_timeout=90)
    await redis_str.delete(reg._workers_key, reg._heartbeats_key)
    q = RedisStreamQueue(R, "test_l1", "mon")
    await q.connect()
    pa = ProgressAggregator(redis_str, km)
    await pa.reset()
    mn = ClusterMonitor(reg, pa, stream_queue=q)
    w = await reg.register({"host": "m", "pid": 1, "concurrency": 4})
    yield {"m": mn, "reg": reg, "pa": pa, "q": q, "w": w}
    await q.close()
    await pa.reset()
    await redis_str.delete(reg._workers_key, reg._heartbeats_key)

@pytest.mark.asyncio
async def test_m1_status(setup):
    s = await setup["m"].status()
    assert "workers" in s and "queue" in s and "progress" in s
    assert s["workers"]["total"] >= 1

@pytest.mark.asyncio
async def test_m2_workers(setup):
    assert len(await setup["m"].workers()) >= 1

@pytest.mark.asyncio
async def test_m3_queue(setup):
    qi = await setup["m"].queue_info()
    assert "pending" in qi and "processing" in qi

@pytest.mark.asyncio
async def test_m4_diagnose(setup):
    d = await setup["m"].diagnose()
    assert "healthy" in d and "issues" in d
