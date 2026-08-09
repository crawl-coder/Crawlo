"""P3-2 统一扩展点：register_queue_backend 测试"""

import pytest

from crawlo.queue import QueueConfig, QueueManager, QueueType, register_queue_backend, unregister_queue_backend
from crawlo.queue.queue_manager import _QUEUE_BUILDERS


class DummyBackend:
    def __init__(self, manager):
        self.manager = manager


async def _build_dummy(manager):
    return DummyBackend(manager)


def test_register_and_cleanup():
    register_queue_backend(QueueType.MEMORY, _build_dummy)
    try:
        assert _QUEUE_BUILDERS[QueueType.MEMORY] is _build_dummy
    finally:
        unregister_queue_backend(QueueType.MEMORY)
    assert QueueType.MEMORY not in _QUEUE_BUILDERS


@pytest.mark.asyncio
async def test_create_queue_uses_registry():
    register_queue_backend(QueueType.MEMORY, _build_dummy)
    try:
        manager = QueueManager(QueueConfig(queue_type='memory'))
        await manager.initialize()
        assert isinstance(manager._queue, DummyBackend)
    finally:
        unregister_queue_backend(QueueType.MEMORY)


def test_unregister_by_string():
    register_queue_backend('memory', _build_dummy)
    assert unregister_queue_backend('memory') is True
    assert unregister_queue_backend('memory') is False


def test_register_invalid():
    with pytest.raises(ValueError):
        register_queue_backend('no_such_queue', _build_dummy)
    with pytest.raises(ValueError):
        register_queue_backend(QueueType.MEMORY, None)
