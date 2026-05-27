"""L1: FailoverManager (5 cases)"""
import time, pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.network.request import Request
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.lock import DistributedLock
from crawlo.cluster.failover import FailoverManager
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.utils.redis.keys import RedisKeyManager

R="redis://127.0.0.1:6379/0"

@pytest_asyncio.fixture
async def r():
    rr=aioredis.from_url(R,decode_responses=True); yield rr
    try: await rr.aclose()
    except: pass

@pytest_asyncio.fixture
async def setup(r):
    km=RedisKeyManager("test_l1","fail"); reg=WorkerRegistry(r,km,worker_timeout=3)
    await r.delete(reg._workers_key,reg._heartbeats_key)
    q=RedisStreamQueue(R,"test_l1","fail"); await q.connect()
    lk=DistributedLock(r,"test_l1:lock:fail"); await r.delete(lk._lock_key)
    fm=FailoverManager(reg,q,lk,r,suspect_timeout=1,failover_interval=10)
    yield {"reg":reg,"q":q,"lk":lk,"fm":fm}; await q.close()
    await r.delete(reg._workers_key,reg._heartbeats_key)

@pytest.mark.asyncio
async def test_f1_no_dead(setup): w=await setup["reg"].register({"host":"a","pid":1,"concurrency":4}); await setup["reg"].heartbeat(w); s=await setup["fm"].check_and_recover(); assert s["dead_workers"]==0
@pytest.mark.asyncio
async def test_f2_suspect(setup): w=await setup["reg"].register({"host":"d","pid":2,"concurrency":4}); await setup["reg"].update_status(w,"suspect",suspect_since=time.time()); assert (await setup["reg"].get_worker_info(w))["status"]=="suspect"
@pytest.mark.asyncio
async def test_f3_recover(setup):
    reg,q=setup["reg"],setup["q"]; w=await reg.register({"host":"d","pid":3,"concurrency":4})
    await reg.update_status(w,"suspect",suspect_since=time.time()-10)
    for i in range(3): await q.put(Request(url=f"http://f/{i}"),0)
    for _ in range(3): await q.get_with_receipt(timeout=2)
    s=await setup["fm"].check_and_recover(); assert s["dead_workers"]>=1 or s["claimed_tasks"]>=1
@pytest.mark.asyncio
async def test_f4_claim(setup):
    q=setup["q"]; [await q.put(Request(url=f"http://c/{i}"),0) for i in range(5)]
    [await q.get_with_receipt(timeout=2) for _ in range(5)]
    assert len(await q.claim_pending(min_idle_ms=0,count=10))>=1
@pytest.mark.asyncio
async def test_f5_dead(setup):
    q=setup["q"]; rr=aioredis.from_url(R,decode_responses=False); await q.put(Request(url="http://dl"),0)
    r2=await q.get_with_receipt(timeout=3); assert r2; await q._escalate_to_dead_letter(r2[1],"test")
    info=await rr.xinfo_stream(q._failed_stream); await rr.aclose(); assert info and info.get("length",0)>=1
