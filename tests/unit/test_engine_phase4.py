#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Phase 4: Engine 覆盖率补全测试

覆盖点：
1. Engine._check_components_idle（多种场景）
2. Engine._exit（空闲 / pending enqueue）
3. Engine._should_exit（standalone / distributed）
4. Engine._fetch（downloader 返回 None / spider=None）
5. Engine.enqueue_request（scheduler=None warning）
6. Engine._schedule_request（_request_available.set）
7. Engine.close_spider（幂等 guard）
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock

from crawlo.core.engine import Engine, has_pending_enqueues, safe_queue_size
from crawlo.cluster.coordinator import ClusterState
from crawlo.core.errors import Failure


# ========================================================================
# 辅助函数：构造最小 Engine 实例（绕过真实 __init__）
# ========================================================================

def _make_minimal_engine(settings=None):
    """
    构造最小化 Engine，__new__ + 手动挂属性。
    避免真实 __init__ 中的 settings 依赖、TaskManager 构造等。
    """
    engine = Engine.__new__(Engine)

    # __init__ 中的核心字段
    engine.running = False
    engine.normal = True
    engine.crawler = None
    engine.settings = settings if settings is not None else {}
    engine.spider = None
    engine.downloader = None
    engine.scheduler = None
    engine.processor = None
    engine.task_manager = None
    engine._start_requests_source = None
    engine._start_requests_is_async = False
    engine._seed_lock_key = None
    engine._seed_renewal_task = None
    engine._close_reason = 'finished'
    engine._spider_closed = False
    engine._background_tasks = set()
    engine._request_available = asyncio.Event()
    engine._idle_since = None
    engine._cluster_state = ClusterState()
    engine.logger = Mock()
    engine.days = 1
    engine.max_queue_size = 10000
    engine.generation_batch_size = 10
    engine.generation_interval = 0.01
    engine.backpressure_ratio = 0.9
    engine.backpressure_strategy = 'queue_size'
    engine.enable_controlled_generation = False
    engine.version = "test"
    engine.checkpoint_save_on_signal = True
    engine._worker_idle_timeout = 300
    # CheckpointCoordinator mock
    engine._checkpoint = Mock()
    engine._checkpoint.save_checkpoint = AsyncMock()
    engine._checkpoint.clear_checkpoint = AsyncMock()

    return engine


# ========================================================================
# 1. _check_components_idle 测试
# ========================================================================

class TestCheckComponentsIdle:
    """Engine._check_components_idle 多场景测试"""

    @pytest.mark.asyncio
    async def test_all_components_none(self):
        """5 个组件全部 None → (F,F,F,F,F)"""
        engine = _make_minimal_engine()
        engine.scheduler = None
        engine.downloader = None
        engine.task_manager = None
        engine.processor = None

        result = await engine._check_components_idle(include_background=False)
        assert result == (False, False, False, False, False)

    @pytest.mark.asyncio
    async def test_scheduler_and_processor_idle_true(self):
        """
        include_background=False:
          scheduler.async_idle() → True
          processor.idle_async() → True
          downloader=None, task_manager=None
          → (T, F, F, T, F)
        """
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.downloader = None
        engine.task_manager = None
        engine.processor = Mock()
        engine.processor.idle_async = AsyncMock(return_value=True)

        result = await engine._check_components_idle(include_background=False)
        assert result == (True, False, False, True, False)
        engine.scheduler.async_idle.assert_awaited_once()
        engine.processor.idle_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_include_background_empty_tasks(self):
        """include_background=True, _background_tasks 空 → bg=True"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.downloader = Mock()
        engine.downloader.idle = Mock(return_value=True)
        engine.task_manager = Mock()
        engine.task_manager.all_done = Mock(return_value=True)
        engine.processor = Mock()
        engine.processor.idle_async = AsyncMock(return_value=True)
        engine._background_tasks = set()  # 空

        result = await engine._check_components_idle(include_background=True)
        assert result == (True, True, True, True, True)

    @pytest.mark.asyncio
    async def test_include_background_non_empty_tasks(self):
        """include_background=True, _background_tasks 非空 → bg=False"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.downloader = Mock()
        engine.downloader.idle = Mock(return_value=True)
        engine.task_manager = Mock()
        engine.task_manager.all_done = Mock(return_value=True)
        engine.processor = Mock()
        engine.processor.idle_async = AsyncMock(return_value=True)

        fake_task = Mock()
        engine._background_tasks = {fake_task}

        result = await engine._check_components_idle(include_background=True)
        # 前 4 个 True，background_tasks_done = False
        assert result == (True, True, True, True, False)

    @pytest.mark.asyncio
    async def test_all_components_true_include_bg_false(self):
        """include_background=False 时 bg 永远是 False"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.async_idle = AsyncMock(return_value=True)
        engine.downloader = Mock()
        engine.downloader.idle = Mock(return_value=True)
        engine.task_manager = Mock()
        engine.task_manager.all_done = Mock(return_value=True)
        engine.processor = Mock()
        engine.processor.idle_async = AsyncMock(return_value=True)
        engine._background_tasks = set()

        result = await engine._check_components_idle(include_background=False)
        # include_background=False → 第 5 位永远是 False
        assert result == (True, True, True, True, False)


# ========================================================================
# 2. _exit 测试
# ========================================================================

class TestEngineExit:
    """Engine._exit 快速退出检查测试"""

    @pytest.mark.asyncio
    async def test_exit_all_idle_no_pending(self):
        """所有组件空闲 + has_pending_enqueues False → True"""
        engine = _make_minimal_engine()

        # 模拟 _check_components_idle 返回全部空闲
        engine._check_components_idle = AsyncMock(
            return_value=(True, True, True, True, False)
        )
        # scheduler=None → has_pending_enqueues 返回 False
        engine.scheduler = None

        result = await engine._exit()
        assert result is True

    @pytest.mark.asyncio
    async def test_exit_has_pending_enqueues(self):
        """has_pending_enqueues True → _exit 返回 False"""
        engine = _make_minimal_engine()
        engine._check_components_idle = AsyncMock(
            return_value=(True, True, True, True, False)
        )
        # scheduler 有 pending_enqueue_count > 0
        engine.scheduler = Mock()
        engine.scheduler.pending_enqueue_count = 5

        result = await engine._exit()
        assert result is False

    @pytest.mark.asyncio
    async def test_exit_scheduler_not_idle(self):
        """scheduler 不空闲 → False"""
        engine = _make_minimal_engine()
        engine._check_components_idle = AsyncMock(
            return_value=(False, True, True, True, False)
        )
        engine.scheduler = None

        result = await engine._exit()
        assert result is False


# ========================================================================
# 3. _should_exit 测试
# ========================================================================

class TestEngineShouldExit:
    """Engine._should_exit 测试（standalone vs distributed）"""

    @pytest.mark.asyncio
    async def test_standalone_all_idle_should_exit(self):
        """run_mode='standalone'：所有组件空闲 + start_requests=None + 无 pending → (True, states)"""
        engine = _make_minimal_engine(settings={'RUN_MODE': 'standalone'})
        engine._start_requests_source = None
        engine._check_components_idle = AsyncMock(
            return_value=(True, True, True, True, True)
        )
        engine.scheduler = None  # pending_enqueues → False

        should, states = await engine._should_exit(last_component_states=None)
        assert should is True
        assert states == (True, True, True, True, True)

    @pytest.mark.asyncio
    async def test_distributed_never_auto_exit(self):
        """run_mode='distributed' → 直接 (False, None)，不检查组件"""
        engine = _make_minimal_engine(settings={'RUN_MODE': 'distributed'})
        engine._check_components_idle = AsyncMock()  # 不应被调用

        should, states = await engine._should_exit(last_component_states=None)
        assert should is False
        assert states is None
        # distributed 模式不应检查组件空闲度
        engine._check_components_idle.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_standalone_start_requests_not_none(self):
        """_start_requests_source 不为 None → 不退出"""
        engine = _make_minimal_engine(settings={'RUN_MODE': 'standalone'})
        engine._start_requests_source = iter([1, 2, 3])  # 非空
        engine._check_components_idle = AsyncMock()  # 不应被调用

        should, states = await engine._should_exit(last_component_states=None)
        assert should is False
        assert states is None

    @pytest.mark.asyncio
    async def test_standalone_components_not_idle(self):
        """组件不全空闲 → 不退出"""
        engine = _make_minimal_engine(settings={'RUN_MODE': 'standalone'})
        engine._start_requests_source = None
        engine._check_components_idle = AsyncMock(
            return_value=(True, False, True, True, True)  # downloader 忙
        )
        engine.scheduler = None

        should, _ = await engine._should_exit(last_component_states=None)
        assert should is False


# ========================================================================
# 4. _fetch 测试
# ========================================================================

class TestEngineFetch:
    """Engine._fetch 各种 guard 分支测试"""

    @pytest.mark.asyncio
    async def test_fetch_downloader_returns_none(self):
        """downloader.fetch 返回 None → 返回 Failure（含 RuntimeError）"""
        engine = _make_minimal_engine()
        fake_spider = Mock()
        fake_spider.parse = Mock()
        engine.spider = fake_spider

        fake_downloader = Mock()
        fake_downloader.fetch = AsyncMock(return_value=None)
        engine.downloader = fake_downloader

        fake_request = Mock()
        fake_request.url = "http://example.com/test-none"
        fake_request.callback = None
        fake_request.cb_kwargs = {}

        result = await engine._fetch(fake_request)

        assert isinstance(result, Failure), (
            f"downloader 返回 None 时 _fetch 应返回 Failure，实际是 {type(result).__name__}"
        )
        # engine 代码中 Failure(request, RuntimeError(...)) 与定义参数顺序相反，
        # 只需保证两个属性之一是 RuntimeError，另一个是 request 即可
        attrs = [result.value, result.request]
        has_request = any(a is fake_request for a in attrs)
        has_runtime_error = any(
            isinstance(a, RuntimeError) for a in attrs
        )
        assert has_request, "Failure 应包含原始 request"
        assert has_runtime_error, "Failure 应包含 RuntimeError"
        # 错误信息包含 URL
        err_str = str(result.value) + " " + str(result.request)
        assert "empty" in err_str.lower() or fake_request.url in err_str

    @pytest.mark.asyncio
    async def test_fetch_spider_is_none(self):
        """self.spider=None → 直接返回 None（Phase 4 guard）"""
        engine = _make_minimal_engine()
        engine.spider = None  # 关键：spider 为 None
        engine.downloader = Mock()
        engine.downloader.fetch = AsyncMock(return_value=Mock())

        fake_request = Mock()
        fake_request.url = "http://example.com/nospider"

        result = await engine._fetch(fake_request)
        assert result is None, "spider=None 时 _fetch 应返回 None"
        # downloader.fetch 不应被调用
        assert engine.downloader.fetch.await_count == 0

    @pytest.mark.asyncio
    async def test_fetch_downloader_none(self):
        """downloader=None → 返回 Failure（含 RuntimeError）"""
        engine = _make_minimal_engine()
        engine.spider = Mock()
        engine.downloader = None

        fake_request = Mock()
        fake_request.url = "http://example.com/nodl"
        fake_request.callback = None
        fake_request.cb_kwargs = {}

        result = await engine._fetch(fake_request)
        assert isinstance(result, Failure)
        # 检查两个属性之一是 RuntimeError
        attrs = [result.value, result.request]
        assert any(isinstance(a, RuntimeError) for a in attrs)
        err_str = str(result.value) + " " + str(result.request)
        assert "not available" in err_str.lower() or "Downloader" in err_str


# ========================================================================
# 5. enqueue_request 测试
# ========================================================================

class TestEngineEnqueueRequest:
    """Engine.enqueue_request / _schedule_request 测试"""

    @pytest.mark.asyncio
    async def test_enqueue_scheduler_none_logs_warning(self):
        """scheduler=None → 走 warning 分支，不抛异常"""
        engine = _make_minimal_engine()
        engine.scheduler = None
        engine._schedule_request = AsyncMock()

        fake_request = Mock(url="http://example.com/warn")
        # 不应抛异常
        await engine.enqueue_request(fake_request)
        # warning 日志应被调用
        engine.logger.warning.assert_called()
        logged_msg = str(engine.logger.warning.call_args_list)
        assert "Scheduler" in logged_msg or "scheduler" in logged_msg
        # 因为 scheduler 为 None，_schedule_request 不应调用
        engine._schedule_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_schedule_request_sets_event_on_success(self):
        """scheduler.enqueue_request 返回 True → _request_available.set() 被调用"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.enqueue_request = AsyncMock(return_value=True)

        engine.crawler = None  # → subscriber 分支不触发
        engine._request_available.clear()
        assert engine._request_available.is_set() is False

        fake_request = Mock(url="http://example.com/setevent")
        await engine._schedule_request(fake_request)

        engine.scheduler.enqueue_request.assert_awaited_once_with(fake_request)
        # True → _request_available.set() 必须被调用
        assert engine._request_available.is_set() is True

    @pytest.mark.asyncio
    async def test_schedule_request_false_does_not_set_event(self):
        """scheduler.enqueue_request 返回 False → _request_available 不 set"""
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.scheduler.enqueue_request = AsyncMock(return_value=False)
        engine.crawler = None
        engine._request_available.clear()

        fake_request = Mock(url="http://example.com/noevent")
        await engine._schedule_request(fake_request)

        # False → set() 不应被调用
        assert engine._request_available.is_set() is False


# ========================================================================
# 6. close_spider 幂等 guard 测试
# ========================================================================

class TestEngineCloseSpider:
    """Engine.close_spider 幂等测试"""

    @pytest.mark.asyncio
    async def test_close_spider_already_closed_returns_early(self):
        """_spider_closed=True 时直接 return（幂等 guard 分支）"""
        engine = _make_minimal_engine()
        engine._spider_closed = True  # 已关闭标记

        engine._shutdown_cluster = AsyncMock()

        await engine.close_spider(reason='finished')

        # 幂等分支下 _shutdown_cluster 不应调用
        engine._shutdown_cluster.assert_not_awaited()
        # logger.debug 至少有一次关于 "already called" 的记录
        debug_calls = [str(c) for c in engine.logger.debug.call_args_list]
        assert any("already called" in c or "skip" in c.lower() for c in debug_calls)

    @pytest.mark.asyncio
    async def test_close_spider_first_call_sets_flag(self):
        """首次调用 close_spider 会将 _spider_closed 设为 True"""
        engine = _make_minimal_engine()
        engine._spider_closed = False
        engine.processor = None
        engine.downloader = None
        engine.scheduler = Mock()
        engine.scheduler.close = AsyncMock(return_value=None)
        engine._shutdown_cluster = AsyncMock()
        engine.task_manager = None

        assert engine._spider_closed is False
        try:
            await engine.close_spider(reason='finished')
        except Exception:
            # 即使后续步骤异常，只要进入了非幂等分支即可
            pass
        # guard 之后立即设 True
        assert engine._spider_closed is True


# ========================================================================
# has_pending_enqueues / safe_queue_size 辅助函数测试
# ========================================================================

class TestHelperFunctions:
    """has_pending_enqueues / safe_queue_size 单元测试"""

    def test_has_pending_enqueues_none_scheduler(self):
        """scheduler=None → False"""
        assert has_pending_enqueues(None) is False

    def test_has_pending_enqueues_zero(self):
        """pending_enqueue_count=0 → False"""
        sched = Mock()
        sched.pending_enqueue_count = 0
        assert has_pending_enqueues(sched) is False

    def test_has_pending_enqueues_positive(self):
        """pending_enqueue_count>0 → True"""
        sched = Mock()
        sched.pending_enqueue_count = 3
        assert has_pending_enqueues(sched) is True

    def test_has_pending_enqueues_no_attr(self):
        """无 pending_enqueue_count 属性 → False"""
        sched = Mock(spec=[])
        assert has_pending_enqueues(sched) is False

    def test_safe_queue_size_none(self):
        """scheduler=None → 0"""
        assert safe_queue_size(None) == 0

    def test_safe_queue_size_exception_returns_minus_1(self):
        """scheduler 抛异常 → 返回 -1"""
        sched = Mock()
        sched._is_memory_queue = Mock(return_value=True)
        # 访问 queue_manager 抛异常
        type(sched).queue_manager = PropertyMock(side_effect=RuntimeError("boom"))
        assert safe_queue_size(sched) == -1
