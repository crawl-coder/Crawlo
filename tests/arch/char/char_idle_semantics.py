#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Characterization Test — Scheduler async_idle/async_size 语义
============================================================

v2.0：sync ``idle()`` 与 ``__len__`` 已物理删除，仅保留异步 API。

当前行为（v2.0 后）：
- ``async_idle()`` 异步 API：返回 queue_manager.async_empty()（推荐使用）
- ``async_size()`` 异步 API：返回 queue_manager.size()（推荐用于背压等精确场景）
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawlo.core.task_scheduler import Scheduler
from crawlo.queue.queue_types import QueueType


def _make_scheduler_with_queue(queue_type):
    """构造一个仅设置 queue_manager 的 Scheduler（绕过 __init__，最小依赖）。"""
    scheduler = Scheduler.__new__(Scheduler)
    qm = MagicMock()
    qm._queue_type = queue_type
    scheduler.queue_manager = qm
    return scheduler, qm


class TestSchedulerIdleSemantics:
    """async_idle / async_size 语义测试（v2.0 后）。"""

    @pytest.mark.asyncio
    async def test_async_idle(self):
        """async_idle() 返回 queue_manager.async_empty() 的结果。"""
        scheduler, qm = _make_scheduler_with_queue(QueueType.REDIS)

        qm.async_empty = AsyncMock(return_value=True)
        assert await scheduler.async_idle() is True

        qm.async_empty = AsyncMock(return_value=False)
        assert await scheduler.async_idle() is False

    @pytest.mark.asyncio
    async def test_async_size_returns_queue_size(self):
        """async_size() 返回 queue_manager.size() 的结果。"""
        scheduler, qm = _make_scheduler_with_queue(QueueType.MEMORY)

        qm.size = AsyncMock(return_value=42)
        assert await scheduler.async_size() == 42
