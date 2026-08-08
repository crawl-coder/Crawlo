#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 2 死锁专项回归测试
========================

验证背压双层合并后不会引入死锁：
1. QueueManager.put 队列满时阻塞等待，_pending_enqueue_count 正确 +1/-1
2. get 唤醒后 put 恢复
3. has_pending_enqueues 在阻塞时返回 True
4. Engine idle 判定在 pending > 0 时不退出

核心防死锁逻辑：
  若 Engine 在 put 阻塞等待时判定为 idle 并退出 →
  消费者停了 → 入队永远等不到消费 → 进程僵死。
  解法：_pending_enqueue_count 纳入 idle 判定。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawlo.queue.queue_manager import QueueManager
from crawlo.queue.config import QueueConfig
from crawlo.queue.queue_types import QueueType
from crawlo.core.engine_helpers import has_pending_enqueues
from crawlo.network.request import Request


def _make_memory_qm(max_size=2):
    """构造一个内存队列 QueueManager（跳过 initialize，直接 mock _queue）。"""
    qm = QueueManager(QueueConfig(max_queue_size=max_size))
    qm._queue = MagicMock()
    qm._queue.put = AsyncMock()
    qm._queue_type = QueueType.MEMORY
    qm._queue_semaphore = None  # 跳过信号量逻辑
    qm._backpressure_controller = MagicMock(enabled=False, active=False)
    return qm


class TestPendingEnqueueTracking:
    """_pending_enqueue_count 在 put 阻塞/恢复时的正确性。"""

    async def test_pending_count_zero_initially(self):
        """初始状态 pending_enqueue_count = 0。"""
        qm = _make_memory_qm()
        assert qm.pending_enqueue_count == 0

    async def test_pending_count_increments_during_block(self):
        """put 阻塞等待时 _pending_enqueue_count = 1，get 唤醒后恢复 0。"""
        qm = _make_memory_qm(max_size=2)

        # size 初始满，被唤醒后变不满
        async def mock_size():
            if not hasattr(mock_size, '_call_count'):
                mock_size._call_count = 0
            mock_size._call_count += 1
            if mock_size._call_count <= 2:
                return 2  # 满
            return 1  # 不满（被唤醒后）

        qm.size = mock_size

        request = Request(url="http://example.com/test", dont_filter=True)

        # 启动 put（会阻塞在 _wait_for_space，timeout=5s）
        put_task = asyncio.create_task(qm.put(request, priority=0, timeout=5.0))

        # 等待 put 进入阻塞
        await asyncio.sleep(0.2)

        # 验证 put 正在阻塞，pending_count = 1
        assert qm.pending_enqueue_count == 1, \
            "put 阻塞等待时 pending_enqueue_count 应为 1"

        # 唤醒等待的 put
        await qm._notify_space_available()

        # 等待 put 完成
        result = await asyncio.wait_for(put_task, timeout=2.0)
        assert result is True, "被唤醒后 put 应成功"

        # 验证 pending_count 恢复为 0
        assert qm.pending_enqueue_count == 0, \
            "put 完成后 pending_enqueue_count 应恢复为 0"

    async def test_pending_count_decrements_on_timeout(self):
        """put 超时后 _pending_enqueue_count 恢复 0（即使抛 QueueFullTimeout）。"""
        from crawlo.queue.exceptions import QueueFullTimeout

        qm = _make_memory_qm(max_size=2)

        async def mock_size():
            return 2  # 始终满

        qm.size = mock_size

        request = Request(url="http://example.com/timeout", dont_filter=True)

        # put 用很短的超时
        with pytest.raises(QueueFullTimeout):
            await qm.put(request, priority=0, timeout=0.3)

        # 超时后 pending_count 应恢复为 0
        assert qm.pending_enqueue_count == 0, \
            "put 超时后 pending_enqueue_count 应恢复为 0"


class TestEngineIdleDeadlockGuard:
    """Engine idle 判定在 pending > 0 时不退出（防死锁）。"""

    async def test_has_pending_enqueues_true_when_blocked(self):
        """scheduler.pending_enqueue_count > 0 时 has_pending_enqueues 返回 True。"""
        scheduler = MagicMock()
        scheduler.pending_enqueue_count = 3
        assert has_pending_enqueues(scheduler) is True

    async def test_has_pending_enqueues_false_when_clear(self):
        """scheduler.pending_enqueue_count == 0 时 has_pending_enqueues 返回 False。"""
        scheduler = MagicMock()
        scheduler.pending_enqueue_count = 0
        assert has_pending_enqueues(scheduler) is False

    async def test_has_pending_enqueues_false_when_none_scheduler(self):
        """scheduler 为 None 时 has_pending_enqueues 返回 False。"""
        assert has_pending_enqueues(None) is False

    async def test_exit_returns_false_when_pending(self):
        """Engine._exit 在有 pending enqueue 时返回 False（防死锁）。

        验证：即使 4 组件都 idle，只要有 put 在阻塞等待，Engine 不退出。
        """
        from crawlo.core.engine import Engine
        from crawlo.settings.setting_manager import SettingManager

        crawler = MagicMock()
        crawler.settings = SettingManager()
        engine = Engine(crawler)

        # mock 4 组件都 idle
        engine.scheduler = MagicMock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.scheduler.pending_enqueue_count = 5  # 有 5 个 put 在阻塞
        engine.downloader = MagicMock()
        engine.downloader.idle = MagicMock(return_value=True)
        engine.task_manager = MagicMock()
        engine.task_manager.all_done = MagicMock(return_value=True)
        engine.processor = MagicMock()
        engine.processor.idle_async = AsyncMock(return_value=True)

        result = await engine._exit()
        assert result is False, \
            "有 pending enqueue 时 _exit 应返回 False（防死锁）"

    async def test_exit_returns_true_when_no_pending(self):
        """Engine._exit 在无 pending enqueue 且组件 idle 时返回 True。"""
        from crawlo.core.engine import Engine
        from crawlo.settings.setting_manager import SettingManager

        crawler = MagicMock()
        crawler.settings = SettingManager()
        engine = Engine(crawler)

        engine.scheduler = MagicMock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.scheduler.pending_enqueue_count = 0  # 无阻塞
        engine.downloader = MagicMock()
        engine.downloader.idle = MagicMock(return_value=True)
        engine.task_manager = MagicMock()
        engine.task_manager.all_done = MagicMock(return_value=True)
        engine.processor = MagicMock()
        engine.processor.idle_async = AsyncMock(return_value=True)

        result = await engine._exit()
        assert result is True, \
            "无 pending enqueue 且组件 idle 时 _exit 应返回 True"
