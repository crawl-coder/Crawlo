"""L1: WorkerRegistry + HeartbeatDaemon (15 cases)"""
import time, asyncio, pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.heartbeat import HeartbeatDaemon
from crawlo.utils.redis.keys import RedisKeyManager

@pytest_asyncio.fixture
async def redis_str():
    r = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    yield r
    try: await r.aclose()
    except: pass

@pytest_asyncio.fixture
async def registry(redis_str):
    km = RedisKeyManager("test_l1", "reg")
    reg = WorkerRegistry(redis_str, km, worker_timeout=5)
    await redis_str.delete(reg._workers_key, reg._heartbeats_key)
    yield reg
    await redis_str.delete(reg._workers_key, reg._heartbeats_key)

@pytest.mark.asyncio
async def test_r1_register(registry): w = await registry.register({"host": "t","pid":1,"concurrency":4}); assert w
@pytest.mark.asyncio
async def test_r2_two(registry): await registry.register({"host":"h1","pid":1,"concurrency":4}); await registry.register({"host":"h2","pid":2,"concurrency":8}); assert await registry.get_worker_count()==2
@pytest.mark.asyncio
async def test_r3_heartbeat(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); old = await registry.get_worker_info(w)
    await asyncio.sleep(0.1); await registry.heartbeat(w); new = await registry.get_worker_info(w)
    assert new["last_heartbeat"] > old["last_heartbeat"]
@pytest.mark.asyncio
async def test_r4_extra(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); await registry.heartbeat(w,{"tasks_completed":99})
    assert (await registry.get_worker_info(w))["tasks_completed"]==99
@pytest.mark.asyncio
async def test_r5_info(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":8}); info = await registry.get_worker_info(w)
    assert info["host"]=="h" and info["status"]=="running"
@pytest.mark.asyncio
async def test_r6_suspect(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); await registry.update_status(w,"suspect",suspect_since=time.time())
    assert (await registry.get_worker_info(w))["status"]=="suspect"
@pytest.mark.asyncio
async def test_r7_active(registry):
    w = await registry.register({"host":"a","pid":1,"concurrency":4}); await registry.heartbeat(w)
    assert len(await registry.get_active_workers())>=1
@pytest.mark.asyncio
async def test_r8_dead0(registry): await registry.register({"host":"h","pid":1,"concurrency":4}); assert len(await registry.detect_dead_workers(timeout=0))>=1
@pytest.mark.asyncio
async def test_r9_dead_inf(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); await registry.heartbeat(w)
    assert len(await registry.detect_dead_workers(timeout=999))==0
@pytest.mark.asyncio
async def test_r10_dereg(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); await registry.deregister(w)
    assert await registry.get_worker_info(w) is None
@pytest.mark.asyncio
async def test_r11_noexist(registry): await registry.deregister("nx-12345")  # no exception
@pytest.mark.asyncio
async def test_h1_start(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); d = HeartbeatDaemon(registry,w,interval=1,jitter=0)
    t = await d.start(); assert isinstance(t,asyncio.Task); await d.stop()
@pytest.mark.asyncio
async def test_h2_cycle(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); old = await registry.get_worker_info(w)
    d = HeartbeatDaemon(registry,w,interval=0.3,jitter=0); await d.start(); await asyncio.sleep(0.5); await d.stop()
    assert (await registry.get_worker_info(w))["last_heartbeat"] > old["last_heartbeat"]
@pytest.mark.asyncio
async def test_h3_stop(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4}); d = HeartbeatDaemon(registry,w,interval=1,jitter=0)
    await d.start(); await asyncio.sleep(0.1); await d.stop(); assert d._task.done()
@pytest.mark.asyncio
async def test_h4_provider(registry):
    w = await registry.register({"host":"h","pid":1,"concurrency":4})
    class P: tasks_completed=42; tasks_processing=2
    d = HeartbeatDaemon(registry,w,interval=0.3,jitter=0); d.set_stats_provider(P()); await d.start()
    await asyncio.sleep(0.5); await d.stop()
    assert (await registry.get_worker_info(w))["tasks_completed"]==42
