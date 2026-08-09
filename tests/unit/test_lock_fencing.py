"""P3-3 Leader fencing token 测试"""

import pytest
from unittest.mock import AsyncMock

from crawlo.cluster.lock import DistributedLock


def _make_lock(redis_client):
    lock = DistributedLock(redis_client, 'test:lock:leader', default_timeout=30, retry_count=1)
    return lock


@pytest.mark.asyncio
async def test_acquire_sets_fence_token():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=42)
    lock = _make_lock(redis)
    holder = await lock.acquire()
    assert holder is not None
    assert lock._fence_token == 42
    redis.incr.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_holder_true_when_lock_and_fence_match():
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=['holder-1', 42])
    lock = _make_lock(redis)
    lock._acquired = True
    lock._holder_id = 'holder-1'
    lock._fence_token = 42
    assert await lock.is_holder() is True


@pytest.mark.asyncio
async def test_is_holder_false_when_fenced_by_new_leader():
    redis = AsyncMock()
    # 锁值已被新 Leader 覆盖（新 token）
    redis.get = AsyncMock(side_effect=['holder-2', 43])
    lock = _make_lock(redis)
    lock._acquired = True
    lock._holder_id = 'holder-1'
    lock._fence_token = 42
    assert await lock.is_holder() is False


@pytest.mark.asyncio
async def test_is_holder_false_when_lock_expired():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    lock = _make_lock(redis)
    lock._acquired = True
    lock._holder_id = 'holder-1'
    lock._fence_token = 42
    assert await lock.is_holder() is False


@pytest.mark.asyncio
async def test_release_clears_fence():
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)
    lock = _make_lock(redis)
    lock._acquired = True
    lock._holder_id = 'holder-1'
    lock._fence_token = 42
    await lock.release()
    assert lock._fence_token is None
    assert lock._acquired is False
