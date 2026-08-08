"""L1: Messenger + DynamicConfig (10 cases)"""
import asyncio, pytest, pytest_asyncio, redis.asyncio as aioredis
from crawlo.cluster.messaging import ClusterMessenger
from crawlo.cluster.config import DynamicConfig

@pytest_asyncio.fixture
async def redis_str():
    r = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    yield r
    try: await r.aclose()
    except: pass

@pytest_asyncio.fixture
async def messenger(redis_str):
    ns = "crawlo:test_l1:msg"
    await redis_str.delete(f"{ns}:control:state")
    m = ClusterMessenger(redis_str, ns)
    yield m
    await m.stop()
    await redis_str.delete(f"{ns}:control:state")

@pytest_asyncio.fixture
async def dconfig(redis_str):
    ns = "crawlo:test_l1:cfg"
    await redis_str.delete(f"{ns}:control:state", f"{ns}:config:rate_limits", f"{ns}:config:seed_urls")
    dc = DynamicConfig(redis_str, namespace=ns, enabled=True)
    yield dc
    await redis_str.delete(f"{ns}:control:state", f"{ns}:config:rate_limits", f"{ns}:config:seed_urls")

@pytest.mark.asyncio
async def test_ms1_pubsub(messenger):
    recv = []
    async def h(msg): recv.append(msg)
    await messenger.subscribe("control", h)
    await messenger.start()
    await asyncio.sleep(0.15)
    await messenger.publish("control", {"action": "test"})
    await asyncio.sleep(0.15)
    await messenger.stop()
    assert len(recv) >= 1 and recv[0]["action"] == "test"

@pytest.mark.asyncio
async def test_ms2_default(messenger):
    assert await messenger.get_control_state() == "running"

@pytest.mark.asyncio
async def test_ms3_multi(messenger):
    ctrl, cfg = [], []
    async def ch(msg): ctrl.append(msg)
    async def cf(msg): cfg.append(msg)
    await messenger.subscribe("control", ch)
    await messenger.subscribe("config", cf)
    await messenger.start()
    await asyncio.sleep(0.15)
    await messenger.publish("control", {"action": "pause"})
    await messenger.publish("config", {"action": "rate"})
    await asyncio.sleep(0.15)
    await messenger.stop()
    assert len(ctrl) >= 1 and len(cfg) >= 1

@pytest.mark.asyncio
async def test_d1_pause(dconfig):
    await dconfig.pause_spider()
    assert await dconfig.get_control_state() == "paused"

@pytest.mark.asyncio
async def test_d2_resume(dconfig):
    await dconfig.pause_spider()
    await dconfig.resume_spider()
    assert await dconfig.get_control_state() == "running"

@pytest.mark.asyncio
async def test_d3_shutdown(dconfig):
    await dconfig.shutdown_cluster()
    assert await dconfig.get_control_state() == "shutdown"

@pytest.mark.asyncio
async def test_d4_rate(dconfig):
    await dconfig.set_rate_limit("api.com", 5.0, 10)
    lim = await dconfig.get_rate_limits()
    assert "api.com" in lim and lim["api.com"]["rate"] == 5.0

@pytest.mark.asyncio
async def test_d5_remove(dconfig):
    await dconfig.set_rate_limit("api.com", 5.0)
    await dconfig.remove_rate_limit("api.com")
    assert "api.com" not in await dconfig.get_rate_limits()

@pytest.mark.asyncio
async def test_d6_seed(dconfig):
    await dconfig.add_seed_urls(["http://s1.com", "http://s2.com", "http://s3.com"])
    urls = await dconfig.pop_seed_urls(5)
    assert len(urls) == 3 and urls[0] == "http://s1.com"

@pytest.mark.asyncio
async def test_d7_empty(dconfig):
    assert await dconfig.pop_seed_urls(10) == []
