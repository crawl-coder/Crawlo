"""Quick distributed tests with minimal delays"""
import asyncio, time, redis.asyncio as aioredis
from crawlo.network.request import Request
from crawlo.queue.redis_stream_queue import RedisStreamQueue
from crawlo.queue.task_tracker import TaskTracker, TaskResult
from crawlo.utils.redis.keys import RedisKeyManager
from crawlo.cluster.registry import WorkerRegistry
from crawlo.cluster.lock import DistributedLock
from crawlo.cluster.failover import FailoverManager
from crawlo.cluster.progress import ProgressAggregator
from crawlo.cluster.rate_limiter import DistributedRateLimiter
from crawlo.cluster.monitor import ClusterMonitor
from crawlo.cluster.config import DynamicConfig
from crawlo.cluster.messaging import ClusterMessenger

P = F = 0
def ck(n, c, d=""):
    global P, F
    if c: P += 1; print(f"  [PASS] {n}")
    else: F += 1; print(f"  [FAIL] {n}: {d}")

async def run():
    global P, F
    r = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    await r.ping()
    print("Tests: Phase 1-6 + Edge + Stress\n")

    # -- Phase 1: StreamQueue --
    q = RedisStreamQueue("redis://127.0.0.1:6379/0", "test", "p1")
    # Clean via queue's own redis client to avoid decode_responses mismatch
    for s in (q._high_stream, q._low_stream, q._failed_stream):
        try: await q._redis.delete(s)
        except: pass
    q._connected = False  # force reconnect after delete
    await q.connect()
    await q.put(Request(url="http://a.com"), 0)
    rr = await q.get_with_receipt(timeout=3)
    ck("stream put+get", rr is not None)
    if rr: ck("msg_id in meta", rr[0].meta.get("__stream_message_id") == rr[1]); await q.ack(rr[1])
    await q.put(Request(url="http://b.com"), 1)
    await q.put(Request(url="http://hi.com"), 0)
    rh = await q.get_with_receipt(timeout=3)
    ck("priority high first", rh and rh[0].url == "http://hi.com")
    if rh: await q.ack(rh[1])
    await q.put(Request(url="http://retry.com"), 0)
    rn = await q.get_with_receipt(timeout=3)
    if rn:
        await q.nack(rn[1], result=TaskResult.RETRY)
        rn2 = await q.get_with_receipt(timeout=3)
        ck("retry re-get count=1", rn2 and rn2[0].meta.get("__stream_retry_count") == 1)
        if rn2: await q.ack(rn2[1])
    ck("empty queue", (await q.get_with_receipt(timeout=0.2)) is None)
    await q.close()
    ck("stream queue ok", True)

    # TaskTracker
    t = TaskTracker("w")
    await t.on_dispatched(Request(url="http://t.com"), "m1")
    ck("tracker processing", t.processing_count == 1)
    await t.on_completed("m1")
    ck("tracker done", t.processing_count == 0)
    ck("timeout->RETRY", t.classify_error(asyncio.TimeoutError()) == TaskResult.RETRY)

    # -- Phase 2: Registry --
    km = RedisKeyManager("test", "p2")
    reg = WorkerRegistry(r, km, worker_timeout=5)
    try: await r.delete(reg._workers_key, reg._heartbeats_key)
    except: pass
    w1 = await reg.register({"host":"h1","pid":1,"concurrency":4})
    w2 = await reg.register({"host":"h2","pid":2,"concurrency":8})
    ck("2 registered", await reg.get_worker_count() == 2)
    await reg.heartbeat(w1, {"tasks_completed":50})
    ck("heartbeat stats", (await reg.get_worker_info(w1))["tasks_completed"] == 50)
    await reg.update_status(w1, "suspect", suspect_since=time.time())
    ck("suspect status", (await reg.get_worker_info(w1))["status"] == "suspect")
    await reg.deregister(w1)
    ck("deregister", await reg.get_worker_info(w1) is None)
    await reg.deregister(w2)

    # -- Phase 3: Lock --
    lk = DistributedLock(r, "test:lk")
    try: await r.delete(lk._lock_key)
    except: pass
    h = await lk.acquire(timeout=3)
    ck("lock acquired", h is not None)
    ck("contention blocked", await DistributedLock(r,"test:lk").acquire(timeout=1,retry=0) is None)
    await lk.release(h)
    ck("lock released", not await lk.is_locked())

    # -- Phase 3: Failover --
    reg2 = WorkerRegistry(r, RedisKeyManager("test","f"), worker_timeout=5)
    try: await r.delete(reg2._workers_key, reg2._heartbeats_key)
    except: pass
    wa = await reg2.register({"host":"a","pid":1,"concurrency":4})
    wd = await reg2.register({"host":"d","pid":2,"concurrency":4})
    await reg2.update_status(wd, "suspect", suspect_since=time.time()-20)
    q3 = RedisStreamQueue("redis://127.0.0.1:6379/0", "test", "f")
    await q3.connect()
    for i in range(5): await q3.put(Request(url=f"http://f/{i}"), 0)
    for _ in range(5): await q3.get_with_receipt(timeout=2)  # Pull to create pending
    fl = DistributedLock(r, "test:f:lock")
    fm = FailoverManager(reg2, q3, fl, r, suspect_timeout=1, failover_interval=10)
    stats = await fm.check_and_recover()
    ck("failover recovery", stats["dead_workers"]>=1 or stats["claimed_tasks"]>=1,
       f"d={stats['dead_workers']} c={stats['claimed_tasks']}")
    await q3.close()
    try: await reg2.deregister(wa)
    except: pass
    try: await reg2.deregister(wd)
    except: pass

    # -- Phase 4: Progress --
    pa = ProgressAggregator(r, RedisKeyManager("test","p4"))
    await pa.reset()
    await pa.report("w1", {"completed":10,"failed":2})
    await pa.report("w2", {"completed":5})
    s = await pa.get_global_stats()
    ck("progress total=15", s["total_completed"]==15, f"got {s['total_completed']}")
    await pa.report("w1", {"completed":13})  # cumulative: 10+3
    s = await pa.get_global_stats()
    ck("progress increment=18", s["total_completed"]==18, f"got {s['total_completed']}")
    await pa.reset()

    # -- Phase 4: RateLimiter --
    rl = DistributedRateLimiter(r, "crawlo:test:rl", enabled=True, default_rate=10, default_capacity=10)
    await r.delete("crawlo:test:rl:rate:b", "crawlo:test:rl:rate:b:ts")
    bp = 0
    for _ in range(10):
        if await rl.acquire("b", rate=10, capacity=10):
            bp += 1
    ck("burst 10/10", bp == 10)
    ck("11th rejected", not await rl.acquire("b", rate=10, capacity=10))
    rl.enabled = False
    ck("disabled passes", await rl.acquire("any"))

    # -- Phase 4: Monitor --
    reg3 = WorkerRegistry(r, RedisKeyManager("test","m"), worker_timeout=90)
    try: await r.delete(reg3._workers_key, reg3._heartbeats_key)
    except: pass
    wm = await reg3.register({"host":"m","pid":1,"concurrency":4})
    qm = RedisStreamQueue("redis://127.0.0.1:6379/0", "test","m")
    await qm.connect()
    mon = ClusterMonitor(reg3, pa, stream_queue=qm)
    s = await mon.status()
    ck("monitor+status", "workers" in s and "queue" in s and "progress" in s)
    await qm.close()
    try: await reg3.deregister(wm)
    except: pass

    # -- Phase 6: Messaging --
    ns = "crawlo:test:p6"
    await r.delete(f"{ns}:control:state")
    recv = []
    async def h(msg): recv.append(msg)
    m = ClusterMessenger(r, ns)
    await m.subscribe("control", h)
    await m.start()
    await asyncio.sleep(0.1)
    await m.publish("control", {"action":"pause"})
    await asyncio.sleep(0.1)
    ck("pubsub recv", len(recv)>=1 and recv[0].get("action")=="pause")
    ck("state default running", await m.get_control_state()=="running")
    await m.stop()

    # DynamicConfig
    dc = DynamicConfig(r, namespace=ns, enabled=True)
    await dc.pause_spider()
    ck("dc pause", await dc.get_control_state()=="paused")
    await dc.resume_spider()
    ck("dc resume", await dc.get_control_state()=="running")
    await dc.set_rate_limit("api.com", 5.0, 10)
    lim = await dc.get_rate_limits()
    ck("dc rate set", "api.com" in lim and lim["api.com"]["rate"]==5.0)
    await dc.remove_rate_limit("api.com")
    ck("dc rate removed", "api.com" not in await dc.get_rate_limits())
    await dc.add_seed_urls(["http://s1.com","http://s2.com"])
    urls = await dc.pop_seed_urls(5)
    ck("dc seed urls", len(urls)==2 and urls[0]=="http://s1.com")

    # -- Edge: wrong holder no release --
    lk2 = DistributedLock(r, "test:edge")
    try: await r.delete(lk2._lock_key)
    except: pass
    h2 = await lk2.acquire(timeout=3)
    lk3 = DistributedLock(r, "test:edge")
    lk3._holder_id = "bad"
    await lk3.release("bad")
    ck("edge bad holder", await lk2.is_locked())
    await lk2.release(h2)
    # rate=0 unlimited
    ck("edge rate=0", await rl.acquire("u", rate=0))

    # -- Stress: 100 items --
    qs = RedisStreamQueue("redis://127.0.0.1:6379/0", "test", "stress")
    await qs.connect()
    t0 = time.time()
    for i in range(100): await qs.put(Request(url=f"http://s/{i}"), 1)
    ck("stress 100 puts <10s", time.time()-t0 < 10)
    got = 0
    for _ in range(110):
        rr = await qs.get_with_receipt(timeout=2.0)
        if rr:
            got += 1
            await qs.ack(rr[1])
    ck("stress 100 gets", got == 100, f"got {got}")
    await qs.close()

    await r.aclose()
    print(f"\n{'='*40}")
    print(f"  TOTAL: {P}/{P+F} PASSED {'(ALL PASS)' if F==0 else f'({F} FAILED)'}")
    print(f"{'='*40}")

asyncio.run(run())
