"""
Phase 5: Engine 覆盖率补全测试（面向 P1-4 门槛 40%）

覆盖 close_spider 各 reason 分支、_cleanup_crawl 清理路径、
_crawl 成功/错误/关键错误路径、_setup_generation 生成模式。
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from crawlo.core.engine import Engine
from crawlo.core.errors import ErrorClassifier, Failure
from crawlo.cluster.coordinator import ClusterState


def _make_minimal_engine(settings=None):
    engine = Engine.__new__(Engine)
    engine.running = True
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
    engine._logger = Mock()
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
    engine._checkpoint = Mock()
    engine._checkpoint.save_checkpoint = AsyncMock(return_value=None)
    engine._checkpoint.clear_checkpoint = AsyncMock(return_value=None)
    engine._checkpoint.resume_from_checkpoint = AsyncMock(return_value=False)
    engine._handle_spider_output = AsyncMock()
    engine._handle_errback_output = AsyncMock()
    engine._cancel_logged = False
    return engine


class TestCloseSpider:
    """close_spider 各 reason 分支"""

    @pytest.mark.asyncio
    async def test_idempotent(self):
        engine = _make_minimal_engine()
        engine._spider_closed = True
        await engine.close_spider(reason='finished')
        engine._checkpoint.clear_checkpoint.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_saves_checkpoint(self):
        engine = _make_minimal_engine()
        engine.scheduler = Mock()
        engine.spider = Mock()
        engine.crawler = Mock()
        engine.crawler.stats = Mock()
        await engine.close_spider(reason='shutdown')
        engine._checkpoint.save_checkpoint.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_finished_clears_checkpoint(self):
        engine = _make_minimal_engine()
        await engine.close_spider(reason='finished')
        engine._checkpoint.clear_checkpoint.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_waiting_active_tasks(self):
        engine = _make_minimal_engine()
        engine.task_manager = Mock()
        engine.task_manager.current_task = set()

        async def slow():
            await asyncio.sleep(0.01)

        task = asyncio.create_task(slow())
        engine.task_manager.current_task.add(task)
        await engine.close_spider(reason='error')
        assert task.done()


class TestCleanupCrawl:
    """crawl() 退出后的清理"""

    @pytest.mark.asyncio
    async def test_cancels_generation_task(self):
        engine = _make_minimal_engine()
        engine.close_spider = AsyncMock()

        async def gen():
            await asyncio.sleep(10)

        generation_task = asyncio.create_task(gen())
        await engine._cleanup_crawl(generation_task)
        assert generation_task.cancelled()
        engine.close_spider.assert_awaited_once_with(reason='finished')

    @pytest.mark.asyncio
    async def test_shutdown_requested_reason(self):
        engine = _make_minimal_engine()
        engine.close_spider = AsyncMock()
        engine.crawler = Mock()
        engine.crawler._process = Mock()
        engine.crawler._process._shutdown_requested = True

        async def gen():
            await asyncio.sleep(10)

        generation_task = asyncio.create_task(gen())
        await engine._cleanup_crawl(generation_task)
        engine.close_spider.assert_awaited_once_with(reason='shutdown')

    @pytest.mark.asyncio
    async def test_cancels_seed_renewal(self):
        engine = _make_minimal_engine()
        engine.close_spider = AsyncMock()

        async def renew():
            await asyncio.sleep(10)

        engine._seed_renewal_task = asyncio.create_task(renew())

        async def gen():
            await asyncio.sleep(10)

        generation_task = asyncio.create_task(gen())
        await engine._cleanup_crawl(generation_task)
        assert engine._seed_renewal_task is None
        assert generation_task.cancelled()


class TestCrawl:
    """_crawl 成功/错误/关键错误路径"""

    def _setup(self, fetch_error=None, errback=None):
        engine = _make_minimal_engine()
        engine.task_manager = Mock()
        async def run_inline(coro):
            return await coro
        engine.task_manager.create_task_nowait = AsyncMock(side_effect=run_inline)
        engine.crawler = Mock()
        engine.crawler.stats = Mock()
        engine.crawler.stats.inc_value = Mock()
        engine._fetch = AsyncMock(side_effect=fetch_error)

        request = Mock()
        request.url = 'http://example.com'
        request.meta = {}
        request.errback = errback
        return engine, request

    @pytest.mark.asyncio
    async def test_success_path(self):
        engine, request = self._setup()
        engine._fetch.return_value = Mock()
        await engine._crawl(request)
        engine.task_manager.create_task_nowait.assert_awaited_once()
        engine._handle_spider_output.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_error_path_with_errback(self):
        async def errback(failure):
            assert isinstance(failure, Failure)
            return None

        engine, request = self._setup(fetch_error=RuntimeError('boom'), errback=errback)
        await engine._crawl(request)
        engine._handle_errback_output.assert_not_awaited()  # errback 返回 None
        engine.crawler.stats.inc_value.assert_any_call('downloader/exception_count')

    @pytest.mark.asyncio
    async def test_critical_error_propagates(self):
        engine, request = self._setup(fetch_error=MemoryError('oom'))
        # 真实行为：crawl_task 以后台任务运行，关键错误在任务内重新抛出
        captured = {}

        def schedule(coro):
            task = asyncio.create_task(coro)
            captured['task'] = task
            return task

        engine.task_manager.create_task_nowait = schedule
        await engine._crawl(request)
        with pytest.raises(MemoryError):
            await captured['task']

    @pytest.mark.asyncio
    async def test_create_task_failure_closes_coro(self):
        engine, request = self._setup()
        engine.task_manager.create_task_nowait = AsyncMock(
            side_effect=RuntimeError('task manager down')
        )
        await engine._crawl(request)
        engine.logger.error.assert_called()


class TestSetupGeneration:
    """请求生成模式选择"""

    @pytest.mark.asyncio
    async def test_traditional_generation(self):
        engine = _make_minimal_engine()
        engine._start_requests_source = iter([Mock()])
        task = engine._setup_generation()
        assert not task.done()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_controlled_generation(self):
        engine = _make_minimal_engine()
        engine.enable_controlled_generation = True
        engine._start_requests_source = iter([Mock()])
        task = engine._setup_generation()
        assert not task.done()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
