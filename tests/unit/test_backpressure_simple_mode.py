"""P3-5 背压简化模式开关测试"""

import pytest
from unittest.mock import Mock

from crawlo.core.engine_helpers import EngineBackpressureAdapter


def _make_adapter(enabled=True):
    return EngineBackpressureAdapter(
        max_queue_size=10,
        backpressure_ratio=0.5,
        strategy='queue_size',
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_disabled_never_pauses():
    adapter = _make_adapter(enabled=False)
    scheduler = Mock()
    # 队列满也应直接放行
    assert adapter.should_pause(scheduler) is False
    assert await adapter.wait_for_capacity(scheduler) is True


@pytest.mark.asyncio
async def test_enabled_pauses_when_full():
    adapter = _make_adapter(enabled=True)
    scheduler = Mock()
    scheduler._is_memory_queue = Mock(return_value=True)
    scheduler.queue_manager = Mock()
    scheduler.queue_manager._queue = Mock()
    scheduler.queue_manager._queue.qsize = Mock(return_value=10)  # 超过 50% 阈值
    assert adapter.should_pause(scheduler) is True


def test_default_enabled():
    adapter = EngineBackpressureAdapter()
    assert adapter.enabled is True
