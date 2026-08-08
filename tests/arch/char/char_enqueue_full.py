#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Characterization Test — Phase 2 入队满策略行为验证
=================================================

Phase 2 背压双层合并后，``enqueue_request`` 的行为变为：
- 去重 → 转发 ``queue_manager.put(timeout=policy_timeout)``
- 按 ``ENQUEUE_FULL_POLICY`` 处理 ``QueueFullTimeout``

策略（见 ``default_settings.py``）：
- ``block``            : 无限等待（受 ``ENQUEUE_BLOCK_TIMEOUT`` 约束），超时按 drop 兜底
- ``drop_with_counter``: 超时丢弃 + 递增 ``scheduler/enqueue_dropped_count``（默认）
- ``raise``            : 超时抛 ``QueueFullTimeout`` 给上层

本测试替代原 Phase 0 行为基线（100×0.5s retry 循环），验证新策略语义正确。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from crawlo.core.scheduling.task_scheduler import Scheduler
from crawlo.queue.exceptions import QueueFullTimeout
from crawlo.http.request import Request


def _make_scheduler(policy='drop_with_counter', block_timeout=None, drop_timeout=50.0):
    """构造带指定入队策略的 Scheduler（mock queue_manager）。

    queue_manager.put 默认返回 True（成功），测试中可覆盖为 side_effect。
    """
    stats = MagicMock()
    scheduler = Scheduler(
        crawler=MagicMock(),
        dupe_filter=MagicMock(),
        stats=stats,
        priority=0,
    )
    qm = MagicMock()
    qm.size = AsyncMock(return_value=10)
    qm.max_size = 10
    qm.config = MagicMock(
        enqueue_full_policy=policy,
        enqueue_block_timeout=block_timeout,
        enqueue_drop_timeout=drop_timeout,
        queue_name='test:queue',
        max_queue_size=10,
    )
    qm.put = AsyncMock(return_value=True)
    scheduler.queue_manager = qm
    return scheduler, stats, qm


def _make_timeout_error(waited=50.0, size=10, max_size=10):
    return QueueFullTimeout(
        queue_name='test:queue',
        waited_seconds=waited,
        queue_size=size,
        max_size=max_size,
    )


class TestEnqueueFullPolicy:
    """Phase 2：ENQUEUE_FULL_POLICY 三策略行为验证。"""

    async def test_drop_with_counter_drops_and_counts(self):
        """policy=drop_with_counter：QueueFullTimeout 被捕获，递增 dropped_count，return False。"""
        scheduler, stats, qm = _make_scheduler(policy='drop_with_counter')
        qm.put = AsyncMock(side_effect=_make_timeout_error())

        request = Request(url="http://example.com/full", dont_filter=True)
        result = await scheduler.enqueue_request(request)

        assert result is False, "drop_with_counter 超时应 return False"
        stats.inc_value.assert_called_once_with('scheduler/enqueue_dropped_count')
        # 验证 put 被调用时传了 drop_timeout（50.0s）
        _, kwargs = qm.put.call_args
        assert kwargs.get('timeout') == 50.0

    async def test_raise_policy_propagates_timeout(self):
        """policy=raise：QueueFullTimeout 不被捕获，向上抛。"""
        scheduler, stats, qm = _make_scheduler(policy='raise')
        qm.put = AsyncMock(side_effect=_make_timeout_error())

        request = Request(url="http://example.com/full", dont_filter=True)
        with pytest.raises(QueueFullTimeout):
            await scheduler.enqueue_request(request)

        # dropped_count 不应递增（raise 不吞错）
        stats.inc_value.assert_not_called()

    async def test_block_policy_uses_block_timeout_none(self):
        """policy=block + ENQUEUE_BLOCK_TIMEOUT=None：put 传 timeout=None（无限等待）。"""
        scheduler, stats, qm = _make_scheduler(policy='block', block_timeout=None)
        qm.put = AsyncMock(return_value=True)  # 队列未满，直接成功

        request = Request(url="http://example.com/ok", dont_filter=True)
        result = await scheduler.enqueue_request(request)

        assert result is True
        _, kwargs = qm.put.call_args
        assert kwargs.get('timeout') is None, "block 策略 + None = 无限等待"

    async def test_block_policy_with_timeout_limit(self):
        """policy=block + ENQUEUE_BLOCK_TIMEOUT=30：put 传 timeout=30。"""
        scheduler, stats, qm = _make_scheduler(policy='block', block_timeout=30.0)
        qm.put = AsyncMock(return_value=True)

        request = Request(url="http://example.com/ok", dont_filter=True)
        await scheduler.enqueue_request(request)

        _, kwargs = qm.put.call_args
        assert kwargs.get('timeout') == 30.0

    async def test_successful_enqueue_no_drop(self):
        """入队成功时不递增 dropped_count。"""
        scheduler, stats, qm = _make_scheduler(policy='drop_with_counter')
        qm.put = AsyncMock(return_value=True)

        request = Request(url="http://example.com/ok", dont_filter=True)
        result = await scheduler.enqueue_request(request)

        assert result is True
        stats.inc_value.assert_not_called()

    async def test_block_policy_timeout_falls_back_to_drop(self):
        """policy=block + ENQUEUE_BLOCK_TIMEOUT=30 + 超时：按 drop 兜底（记日志+计数）。"""
        scheduler, stats, qm = _make_scheduler(policy='block', block_timeout=30.0)
        qm.put = AsyncMock(side_effect=_make_timeout_error(waited=30.0))

        request = Request(url="http://example.com/full", dont_filter=True)
        result = await scheduler.enqueue_request(request)

        assert result is False, "block 超时后应兜底为 drop"
        stats.inc_value.assert_called_once_with('scheduler/enqueue_dropped_count')


class TestPendingEnqueueCount:
    """Phase 2：pending_enqueue_count 防死锁机制验证。

    QueueManager 维护 _pending_enqueue_count，put 阻塞等待时 +1，退出时 -1。
    Engine 的 idle 判定检查此值，防止"入队在 block 等待"被误判为"没事干"导致死锁。
    """

    async def test_pending_count_exposed_via_scheduler(self):
        """Scheduler.pending_enqueue_count 委托到 QueueManager。"""
        scheduler, stats, qm = _make_scheduler()
        qm.pending_enqueue_count = 3
        assert scheduler.pending_enqueue_count == 3

    async def test_pending_count_defaults_to_zero(self):
        """QueueManager 初始化时 pending_enqueue_count = 0。"""
        from crawlo.queue.queue_manager import QueueManager
        from crawlo.queue.config import QueueConfig
        qm = QueueManager(QueueConfig())
        assert qm.pending_enqueue_count == 0

    async def test_pending_count_zero_when_no_queue_manager(self):
        """无 queue_manager 时 pending_enqueue_count 返回 0。"""
        scheduler = Scheduler(
            crawler=MagicMock(),
            dupe_filter=MagicMock(),
            stats=MagicMock(),
            priority=0,
        )
        assert scheduler.pending_enqueue_count == 0
