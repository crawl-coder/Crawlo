"""P3-1 Redis Cluster 接入 Stream 主链路测试"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from crawlo.queue.backends.redis_stream import RedisStreamQueue


def test_parse_cluster_nodes_from_url():
    q = RedisStreamQueue(redis_url='redis-cluster://10.0.0.1:7000,10.0.0.2:7001')
    nodes = q._parse_cluster_nodes_from_url()
    assert nodes == [('10.0.0.1', 7000), ('10.0.0.2', 7001)]


def test_cluster_enabled_detected_from_url():
    q = RedisStreamQueue(redis_url='rediss-cluster://10.0.0.1:7000')
    assert q._cluster_enabled is True
    q2 = RedisStreamQueue(redis_url='redis://127.0.0.1:6379/0')
    assert q2._cluster_enabled is False


@pytest.mark.asyncio
async def test_connect_creates_cluster_client():
    q = RedisStreamQueue(
        redis_url='redis://127.0.0.1:6379/0',
        cluster_enabled=True,
        cluster_nodes=['10.0.0.1:7000'],
    )
    with patch('crawlo.queue.backends.redis_stream.RedisStreamQueue._create_cluster_client') as m:
        fake_client = AsyncMock()
        m.return_value = fake_client
        with patch.object(q, '_ensure_consumer_groups', new=AsyncMock()), \
             patch.object(q, '_recover_orphan_pending', new=AsyncMock()), \
             patch('crawlo.queue.backends.redis_stream.detect_redis_version', new=AsyncMock(return_value=(7, 2, 0))), \
             patch('crawlo.queue.backends.redis_stream.supports_xautoclaim', new=AsyncMock(return_value=True)):
            await q.connect()
    assert q._is_cluster is True


@pytest.mark.asyncio
async def test_stream_read_cluster_polls():
    from crawlo.utils.redis.stream_utils import stream_read
    client = AsyncMock()
    # 前两次空，第三次有消息
    client.xreadgroup = AsyncMock(side_effect=[
        [],
        [],
        [('stream', [(b'1-0', {b'k': b'v'})])],
    ])
    msgs = await stream_read(client, 'g', 'c', 's', count=1, block=100, cluster_mode=True)
    assert msgs is not None
    assert client.xreadgroup.await_count == 3
    # 非 cluster 模式应带 block 参数
    client2 = AsyncMock()
    client2.xreadgroup = AsyncMock(return_value=[])
    await stream_read(client2, 'g', 'c', 's', count=1, block=100)
    _, kwargs = client2.xreadgroup.call_args
    assert kwargs.get('block') == 100
