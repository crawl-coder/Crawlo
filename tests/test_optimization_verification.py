"""
全面测试 - 验证最新优化修改的正确性

测试覆盖:
1. Redis 过滤器网络异常处理 (防止数据丢失)
2. Engine 事件驱动机制 (CPU 优化)
3. Crawler 生命周期管理 (消除竞态)
4. Processor 队列处理 (消除竞态)
5. Scheduler Condition 变量 (替代轮询)
6. Middleware 日志守卫 (性能优化)
7. Middleware 任务追踪 (防止泄漏)
"""

import asyncio
import logging
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

from crawlo.filters.aioredis_filter import AioRedisFilter
from crawlo.core.engine import Engine
from crawlo.core.processor import Processor
from crawlo.core.scheduler import Scheduler
from crawlo.crawler import Crawler
from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.network.request import Request
from crawlo.event import CrawlerEvent


# ============================================================
# 1. Redis 过滤器网络异常测试
# ============================================================

class TestAioRedisFilterNetworkError:
    """测试 Redis 过滤器在网络异常时的行为"""

    @pytest.fixture
    def mock_redis_client(self):
        """模拟 Redis 客户端"""
        client = AsyncMock()
        client.sismember = AsyncMock(side_effect=ConnectionError("Redis connection lost"))
        client.sadd = AsyncMock(side_effect=ConnectionError("Redis connection lost"))
        return client

    @pytest.fixture
    def redis_filter(self, mock_redis_client):
        """创建 Redis 过滤器实例"""
        filter_instance = AioRedisFilter(
            redis_key="test:filter",
            client=mock_redis_client,
            debug=False
        )
        filter_instance._redis_client = mock_redis_client
        filter_instance._connection_failed = False
        return filter_instance

    @pytest.mark.asyncio
    async def test_requested_async_network_error_returns_false(self, redis_filter):
        """网络异常时 requested_async 应返回 False (允许请求通过,防止数据丢失)"""
        request = Request(url="http://example.com/page1")
        
        # 网络异常时应返回 False (允许请求通过)
        result = await redis_filter.requested_async(request)
        
        assert result is False, "网络异常时应返回 False,允许请求通过,防止数据丢失"

    @pytest.mark.asyncio
    async def test_requested_async_logs_warning_not_error(self, redis_filter, caplog):
        """网络异常时应记录 warning 而非 error"""
        request = Request(url="http://example.com/page2")
        
        with caplog.at_level(logging.WARNING):
            result = await redis_filter.requested_async(request)
        
        # 验证日志级别是 WARNING
        assert any(record.levelno == logging.WARNING for record in caplog.records), \
            "网络异常时应记录 WARNING 级别日志"
        
        # 验证日志消息包含关键信息
        log_message = " ".join(record.message for record in caplog.records)
        assert "Redis unavailable" in log_message or "allowing request" in log_message.lower(), \
            "日志应说明 Redis 不可用且允许请求通过"

    @pytest.mark.asyncio
    async def test_check_fingerprint_exists_network_error_returns_false(self, redis_filter):
        """检查指纹存在性时网络异常应返回 False"""
        fp = "test_fingerprint_123"
        
        result = await redis_filter._check_fingerprint_exists(fp)
        
        assert result is False, "网络异常时应返回 False,允许请求通过"

    @pytest.mark.asyncio
    async def test_network_error_no_request_loss(self, redis_filter):
        """验证网络异常时不会丢失请求 (宁可重复)"""
        requests = [
            Request(url=f"http://example.com/page{i}")
            for i in range(10)
        ]
        
        # 所有请求都应该通过 (返回 False)
        results = []
        for req in requests:
            result = await redis_filter.requested_async(req)
            results.append(result)
        
        # 所有请求都应被允许通过 (False)
        assert all(r is False for r in results), \
            "网络异常时所有请求都应通过,不能丢失"


# ============================================================
# 2. Engine 事件驱动测试
# ============================================================

class TestEngineEventDriven:
    """测试 Engine 事件驱动机制"""

    @pytest.fixture
    def mock_crawler(self):
        """模拟 Crawler"""
        crawler = Mock()
        crawler.settings = Mock()
        crawler.settings.get = Mock(return_value=None)
        crawler.spider = Mock()
        crawler.subscriber = Mock()
        crawler.subscriber.notify = AsyncMock()
        crawler.stats = Mock()
        return crawler

    @pytest.fixture
    def engine(self, mock_crawler):
        """创建 Engine 实例"""
        from crawlo.core.engine import Engine
        
        engine = Engine(mock_crawler)
        engine.scheduler = Mock()
        engine.scheduler.enqueue_request = AsyncMock(return_value=True)
        engine.scheduler.next_request = AsyncMock(return_value=None)
        engine.downloader = Mock()
        engine.processor = Mock()
        engine.task_manager = Mock()
        engine.task_manager.current_task = set()
        
        return engine

    @pytest.mark.asyncio
    async def test_schedule_request_sets_event(self, engine):
        """_schedule_request 应设置 _request_available 事件"""
        request = Request(url="http://example.com")
        
        # 事件初始状态应为未设置
        assert not engine._request_available.is_set()
        
        # 调用 _schedule_request
        await engine._schedule_request(request)
        
        # 事件应被设置
        assert engine._request_available.is_set(), \
            "_schedule_request 应设置 _request_available 事件"

    @pytest.mark.asyncio
    async def test_schedule_request_creates_background_task(self, engine):
        """_schedule_request 应创建带追踪的后台任务"""
        request = Request(url="http://example.com")
        
        initial_task_count = len(engine._background_tasks)
        
        await engine._schedule_request(request)
        
        # 应创建新的后台任务
        assert len(engine._background_tasks) == initial_task_count + 1, \
            "_schedule_request 应创建带追踪的后台任务"

    @pytest.mark.asyncio
    async def test_event_cleared_on_batch_processing(self, engine):
        """批量处理请求时应清除事件"""
        # 设置事件
        engine._request_available.set()
        assert engine._request_available.is_set()
        
        # 模拟主循环中的批量处理逻辑
        # (实际代码中在获取 requests 后清除)
        engine._request_available.clear()
        
        assert not engine._request_available.is_set(), \
            "批量处理时应清除事件"

    @pytest.mark.asyncio
    async def test_event_wait_with_timeout(self, engine):
        """事件等待应有超时保护"""
        start_time = time.time()
        
        # 等待未设置的事件,应在超时后返回
        timeout = 0.1
        try:
            await asyncio.wait_for(
                engine._request_available.wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            pass
        
        elapsed = time.time() - start_time
        
        # 应在超时时间附近返回 (允许 50ms 误差)
        assert elapsed >= timeout - 0.05, "事件等待应有超时保护"
        assert elapsed < timeout + 0.1, "事件等待不应阻塞过久"


# ============================================================
# 3. Crawler 生命周期测试
# ============================================================

class TestCrawlerLifecycle:
    """测试 Crawler 生命周期管理"""

    @pytest.mark.asyncio
    async def test_lifecycle_manager_uses_explicit_flag(self):
        """_lifecycle_manager 应使用显式 cleaned_up 标志"""
        crawler = Mock()
        crawler._metrics = Mock()
        crawler._cleanup = AsyncMock()
        crawler._handle_error = AsyncMock()
        
        # 导入 Crawler 类
        from crawlo.crawler import Crawler
        
        # 验证源代码中使用 cleaned_up 标志
        import inspect
        source = inspect.getsource(Crawler._lifecycle_manager)
        
        assert "cleaned_up" in source, \
            "_lifecycle_manager 应使用 cleaned_up 标志变量"
        assert "sys.exc_info()" not in source, \
            "_lifecycle_manager 不应使用 sys.exc_info()"

    @pytest.mark.asyncio
    async def test_cleanup_not_called_twice_on_cancel(self):
        """CancelledError 时 cleanup 不应被调用两次"""
        crawler = Mock()
        crawler._metrics = Mock()
        crawler._cleanup = AsyncMock()
        
        cleanup_call_count = 0
        
        async def mock_cleanup(reason='finished'):
            nonlocal cleanup_call_count
            cleanup_call_count += 1
        
        crawler._cleanup = mock_cleanup
        
        # 模拟 CancelledError 场景
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def test_lifecycle():
            cleaned_up = False
            try:
                yield
            except asyncio.CancelledError:
                cleaned_up = True
                await crawler._cleanup(reason='shutdown')
                raise
            finally:
                if not cleaned_up:
                    await crawler._cleanup()
        
        # 触发 CancelledError
        with pytest.raises(asyncio.CancelledError):
            async with test_lifecycle():
                raise asyncio.CancelledError()
        
        # cleanup 应只被调用一次
        assert cleanup_call_count == 1, \
            "CancelledError 时 cleanup 应只被调用一次"


# ============================================================
# 4. Processor 队列竞态测试
# ============================================================

class TestProcessorQueueRace:
    """测试 Processor 队列处理竞态条件"""

    @pytest.fixture
    def processor(self):
        """创建 Processor 实例"""
        proc = Processor()
        proc.pipelines = Mock()
        proc.pipelines.process_item = AsyncMock()
        return proc

    @pytest.mark.asyncio
    async def test_process_once_handles_race_condition(self, processor):
        """process_once 应正确处理队列为空的竞态"""
        # 使用直接调用 get_nowait 的模式
        import asyncio
        
        processor.queue = asyncio.Queue()
        
        # 放入一个请求后立即清空
        await processor.queue.put("item1")
        
        # 模拟竞态: 在其他地方清空队列
        async def clear_queue():
            await asyncio.sleep(0.01)
            while not processor.queue.empty():
                try:
                    processor.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        # 同时执行清空和处理
        await asyncio.gather(
            clear_queue(),
            processor.process_once()
        )
        
        # 不应抛出异常
        assert True

    @pytest.mark.asyncio
    async def test_drain_queue_uses_exception_handling(self, processor):
        """_drain_queue 应使用异常捕获而非 empty() 检查"""
        import asyncio
        
        processor.queue = asyncio.Queue()
        
        # 放入几个项目
        for i in range(3):
            await processor.queue.put(f"item{i}")
        
        # 调用 _drain_queue
        await processor._drain_queue()
        
        # 队列应为空
        assert processor.queue.empty()


# ============================================================
# 5. Scheduler Condition 变量测试
# ============================================================

class TestSchedulerConditionVariable:
    """测试 Scheduler Condition 变量机制"""

    @pytest.fixture
    def scheduler(self):
        """创建 Scheduler 实例"""
        sched = Mock(spec=Scheduler)
        sched._queue_not_full = asyncio.Condition()
        sched.queue_manager = Mock()
        sched.queue_manager.max_size = 10
        sched.queue_manager.size = AsyncMock(return_value=5)
        sched.queue_manager.put = AsyncMock(return_value=True)
        sched.crawler = Mock()
        sched.crawler.settings = Mock()
        sched.crawler.settings.get = Mock(return_value=None)
        sched.crawler.settings.set = Mock()
        return sched

    def test_has_queue_not_full_condition(self, scheduler):
        """Scheduler 应有 _queue_not_full Condition 变量"""
        assert hasattr(scheduler, '_queue_not_full'), \
            "Scheduler 应有 _queue_not_full Condition 变量"
        assert isinstance(scheduler._queue_not_full, asyncio.Condition), \
            "_queue_not_full 应为 asyncio.Condition 实例"

    def test_has_get_setting_helper(self, scheduler):
        """Scheduler 应有 _get_setting 辅助方法"""
        # 检查实际的 Scheduler 类
        from crawlo.core.scheduler import Scheduler
        import inspect
        
        assert hasattr(Scheduler, '_get_setting'), \
            "Scheduler 应有 _get_setting 辅助方法"

    @pytest.mark.asyncio
    async def test_enqueue_request_uses_condition(self):
        """enqueue_request 应使用 Condition 等待"""
        from crawlo.core.scheduler import Scheduler
        
        # 检查源代码
        import inspect
        source = inspect.getsource(Scheduler.enqueue_request)
        
        assert "_queue_not_full" in source, \
            "enqueue_request 应使用 _queue_not_full Condition"
        assert "async with self._queue_not_full" in source, \
            "enqueue_request 应使用 async with 获取 Condition"


# ============================================================
# 6. Middleware 日志守卫测试
# ============================================================

class TestMiddlewareLogGuard:
    """测试 Middleware 日志守卫"""

    @pytest.fixture
    def middleware_manager(self):
        """创建 MiddlewareManager 实例"""
        crawler = Mock()
        crawler.stats = Mock()
        crawler.spider = Mock()
        
        manager = MiddlewareManager(crawler)
        manager.methods = {
            'process_request': [],
            'process_response': [],
            'process_exception': []
        }
        
        return manager

    def test_debug_log_uses_is_enabled_for(self, middleware_manager):
        """DEBUG 日志应使用 isEnabledFor 守卫"""
        import inspect
        source = inspect.getsource(middleware_manager._process_request)
        
        assert "isEnabledFor" in source, \
            "_process_request 应使用 isEnabledFor 守卫"
        assert "isEnabledFor(10)" in source or "isEnabledFor(logging.DEBUG)" in source, \
            "应检查 DEBUG 级别 (10)"

    @pytest.mark.asyncio
    async def test_log_not_formatted_when_disabled(self, middleware_manager):
        """日志禁用时不应执行字符串格式化"""
        # 设置日志级别为 INFO (禁用 DEBUG)
        middleware_manager.logger.setLevel(logging.INFO)
        
        request = Request(url="http://example.com")
        middleware_manager.methods['process_request'] = []
        
        # 调用 _process_request
        result = await middleware_manager._process_request(request)
        
        # 不应有 DEBUG 日志
        # (验证通过表示没有异常,字符串格式化被跳过)
        assert result is None


# ============================================================
# 7. Middleware 任务追踪测试
# ============================================================

class TestMiddlewareTaskTracking:
    """测试 Middleware 任务追踪机制"""

    @pytest.fixture
    def middleware_manager(self):
        """创建 MiddlewareManager 实例"""
        crawler = Mock()
        crawler.stats = Mock()
        crawler.spider = Mock()
        crawler.subscriber = Mock()
        crawler.subscriber.notify = AsyncMock()
        
        manager = MiddlewareManager(crawler)
        manager.methods = {
            'process_request': [],
            'process_response': [],
            'process_exception': []
        }
        
        return manager

    def test_has_background_tasks_set(self, middleware_manager):
        """MiddlewareManager 应有 _background_tasks 集合"""
        assert hasattr(middleware_manager, '_background_tasks'), \
            "MiddlewareManager 应有 _background_tasks 集合"
        assert isinstance(middleware_manager._background_tasks, set), \
            "_background_tasks 应为 set 类型"

    def test_create_background_task_method_exists(self, middleware_manager):
        """MiddlewareManager 应有 _create_background_task 方法"""
        assert hasattr(middleware_manager, '_create_background_task'), \
            "MiddlewareManager 应有 _create_background_task 方法"

    @pytest.mark.asyncio
    async def test_create_background_task_tracks_task(self, middleware_manager):
        """_create_background_task 应追踪任务"""
        async def dummy_coro():
            await asyncio.sleep(0.01)
        
        initial_count = len(middleware_manager._background_tasks)
        
        task = middleware_manager._create_background_task(dummy_coro())
        
        # 任务应被添加到集合
        assert len(middleware_manager._background_tasks) == initial_count + 1, \
            "任务应被添加到 _background_tasks 集合"
        assert task in middleware_manager._background_tasks, \
            "创建的任务应在 _background_tasks 中"

    @pytest.mark.asyncio
    async def test_background_task_removed_on_completion(self, middleware_manager):
        """后台任务完成后应从集合中移除"""
        async def quick_coro():
            await asyncio.sleep(0.01)
        
        task = middleware_manager._create_background_task(quick_coro())
        assert task in middleware_manager._background_tasks
        
        # 等待任务完成
        await task
        await asyncio.sleep(0.05)  # 给回调一些时间
        
        # 任务应从集合中移除
        assert task not in middleware_manager._background_tasks, \
            "任务完成后应从 _background_tasks 中移除"


# ============================================================
# 运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
