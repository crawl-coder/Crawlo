#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Tests for Optimization Plan (Phase 1 + Phase 2)
================================================
覆盖 optimization_plan.md 中已实施的 12 个优化项：

Phase 1:
  - 4.2: _get_method_class_name 方法统一调用
  - 4.3: _lifecycle_manager cleaned_up 标志替代 sys.exc_info()
  - 5.1: close_spider 幂等性（异常时重置标志）
  - 5.7: _create_background_task 引用追踪
  - 3.1: isEnabledFor 日志守卫
  - 5.9: Processor QueueEmpty 异常模式

Phase 2:
  - 4.1: Scheduler _get_setting/_set_setting 辅助方法
  - 3.2: Scheduler Condition 等待替代轮询
  - 5.10: Redis 过滤器保守错误处理
  - 6.2: extras_require 依赖拆分
  - 2.1: Engine Event 驱动主循环
"""
import asyncio
import logging
import configparser
from unittest.mock import Mock, MagicMock, patch, AsyncMock, PropertyMock

import pytest


# ============================================================
# 4.2: _get_method_class_name 方法统一调用
# ============================================================
class TestOptimization_4_2_GetMethodClassName:
    """验证 middleware_manager 使用 _get_method_class_name 替代重复的 hasattr 链"""

    def test_method_exists(self):
        """_get_method_class_name 方法存在"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        assert hasattr(MiddlewareManager, '_get_method_class_name')

    def test_bound_method_returns_class_name(self):
        """对绑定方法返回正确的类名"""
        from crawlo.middleware.middleware_manager import MiddlewareManager

        class FakeMiddleware:
            def process_request(self, request, spider):
                return None

        mm = type('MM', (), {'_get_method_class_name': MiddlewareManager._get_method_class_name})()
        name = mm._get_method_class_name(FakeMiddleware().process_request)
        assert name == 'FakeMiddleware'

    def test_function_returns_str(self):
        """对普通函数返回 str()"""
        from crawlo.middleware.middleware_manager import MiddlewareManager

        mm = type('MM', (), {'_get_method_class_name': MiddlewareManager._get_method_class_name})()
        def my_func(): pass
        name = mm._get_method_class_name(my_func)
        assert name == str(my_func)

    def test_no_hasattr_pattern_in_process_exception(self):
        """_process_exception 中不应有重复的 hasattr(method, '__self__') 模式"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_exception)
        # 统计 hasattr(method, '__self__') 出现次数
        count = source.count("hasattr(method, '__self__')")
        assert count == 0, f"_process_exception 仍有 {count} 处 hasattr(method, '__self__')，应使用 _get_method_class_name"

    def test_uses_method_in_process_request(self):
        """_process_request 中应使用 _get_method_class_name"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_request)
        assert '_get_method_class_name' in source


# ============================================================
# 4.3: _lifecycle_manager cleaned_up 标志替代 sys.exc_info()
# ============================================================
class TestOptimization_4_3_LifecycleManagerFlag:
    """验证 crawler.py 使用 cleaned_up 标志替代 sys.exc_info()"""

    def test_no_sys_exc_info_import(self):
        """crawler.py 不应导入 sys（因为 sys.exc_info() 已被移除）"""
        import inspect
        from crawlo.crawler import Crawler
        source = inspect.getsource(Crawler)
        assert 'sys.exc_info' not in source, "crawler.py 仍使用 sys.exc_info()，应改用 cleaned_up 标志"

    @pytest.mark.asyncio
    async def test_normal_exit_calls_cleanup_once(self):
        """正常退出时 cleanup 恰好调用一次"""
        from crawlo.crawler import Crawler, CrawlerState
        from crawlo.settings.setting_manager import SettingManager

        class TestSpider:
            name = 'test'

        settings = SettingManager()
        settings.update_attributes({'LOG_LEVEL_NUM': 40})  # WARNING
        crawler = Crawler.__new__(Crawler)
        crawler._spider_cls = TestSpider
        crawler._settings = settings
        crawler._state = CrawlerState.CREATED
        crawler._state_lock = asyncio.Lock()
        crawler._metrics = type('M', (), {'start_time': None, 'end_time': None})()
        crawler._resource_manager = AsyncMock()
        crawler._resource_manager.cleanup_all = AsyncMock(return_value={'success': 1, 'errors': 0, 'duration': 0.1})
        crawler._stats = None
        crawler._subscriber = AsyncMock()
        crawler._extension = None
        crawler._logger = get_test_logger()

        cleanup_calls = 0
        async def mock_cleanup(reason='finished'):
            nonlocal cleanup_calls
            cleanup_calls += 1

        crawler._cleanup = mock_cleanup

        # 正常执行 lifecycle_manager
        async with crawler._lifecycle_manager():
            pass

        assert cleanup_calls == 1, f"正常退出时 cleanup 应调用 1 次，实际 {cleanup_calls} 次"

    @pytest.mark.asyncio
    async def test_cancelled_error_calls_cleanup_once(self):
        """CancelledError 时 cleanup 恰好调用一次（由 except 块处理，finally 不重复）"""
        from crawlo.crawler import Crawler, CrawlerState
        from crawlo.settings.setting_manager import SettingManager

        class TestSpider:
            name = 'test'

        settings = SettingManager()
        settings.update_attributes({'LOG_LEVEL_NUM': 40})
        crawler = Crawler.__new__(Crawler)
        crawler._spider_cls = TestSpider
        crawler._settings = settings
        crawler._state = CrawlerState.CREATED
        crawler._state_lock = asyncio.Lock()
        crawler._metrics = type('M', (), {'start_time': None, 'end_time': None})()
        crawler._resource_manager = AsyncMock()
        crawler._resource_manager.cleanup_all = AsyncMock(return_value={'success': 1, 'errors': 0, 'duration': 0.1})
        crawler._stats = None
        crawler._subscriber = AsyncMock()
        crawler._extension = None
        crawler._logger = get_test_logger()

        cleanup_calls = 0
        async def mock_cleanup(reason='finished'):
            nonlocal cleanup_calls
            cleanup_calls += 1

        crawler._cleanup = mock_cleanup

        with pytest.raises(asyncio.CancelledError):
            async with crawler._lifecycle_manager():
                raise asyncio.CancelledError()

        assert cleanup_calls == 1, f"CancelledError 时 cleanup 应调用 1 次，实际 {cleanup_calls} 次"

    @pytest.mark.asyncio
    async def test_generic_exception_calls_cleanup_once(self):
        """普通异常时 cleanup 恰好调用一次（由 finally 处理）"""
        from crawlo.crawler import Crawler, CrawlerState
        from crawlo.settings.setting_manager import SettingManager

        class TestSpider:
            name = 'test'

        settings = SettingManager()
        settings.update_attributes({'LOG_LEVEL_NUM': 40})
        crawler = Crawler.__new__(Crawler)
        crawler._spider_cls = TestSpider
        crawler._settings = settings
        crawler._state = CrawlerState.CREATED
        crawler._state_lock = asyncio.Lock()
        crawler._metrics = type('M', (), {'start_time': None, 'end_time': None})()
        crawler._resource_manager = AsyncMock()
        crawler._resource_manager.cleanup_all = AsyncMock(return_value={'success': 1, 'errors': 0, 'duration': 0.1})
        crawler._stats = None
        crawler._subscriber = AsyncMock()
        crawler._extension = None
        crawler._logger = get_test_logger()

        cleanup_calls = 0
        async def mock_cleanup(reason='finished'):
            nonlocal cleanup_calls
            cleanup_calls += 1

        crawler._cleanup = mock_cleanup
        crawler._handle_error = AsyncMock()

        with pytest.raises(RuntimeError):
            async with crawler._lifecycle_manager():
                raise RuntimeError("test error")

        assert cleanup_calls == 1, f"普通异常时 cleanup 应调用 1 次，实际 {cleanup_calls} 次"


# ============================================================
# 5.1: close_spider 幂等性（异常时重置标志）
# ============================================================
class TestOptimization_5_1_CloseSpiderIdempotency:
    """验证 engine.close_spider 在异常时重置 _spider_closed 标志"""

    def test_has_reset_on_exception(self):
        """close_spider 源码中应有 self._spider_closed = False 在 except 块"""
        import inspect
        from crawlo.core.engine import Engine
        source = inspect.getsource(Engine.close_spider)
        assert 'self._spider_closed = False' in source, \
            "close_spider 的 except 块中应包含 self._spider_closed = False 以允许重试"

    @pytest.mark.asyncio
    async def test_close_spider_resets_flag_on_exception(self):
        """close_spider 异常后 _spider_closed 应被重置为 False"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        crawler.spider = None

        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = None
        engine.downloader = None
        engine.scheduler = None
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        # Mock _cleanup_old_logs 抛异常（内部有 try/except 的步骤不会穿透）
        # 最可靠的方式是 mock 整个 try 块内的某个步骤
        # _clear_checkpoint 有 try/except, _cleanup_old_logs 也有
        # 直接 mock 一个能穿透的步骤
        async def failing_cleanup():
            raise RuntimeError("cleanup failed")
        engine._cleanup_old_logs = failing_cleanup
        engine._save_checkpoint = AsyncMock()
        engine._clear_checkpoint = AsyncMock()

        with pytest.raises(RuntimeError):
            await engine.close_spider()

        assert engine._spider_closed is False, \
            "close_spider 异常后 _spider_closed 应被重置为 False"

    @pytest.mark.asyncio
    async def test_close_spider_idempotent_on_success(self):
        """成功关闭后，再次调用应直接返回"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        crawler.spider = None

        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = None
        engine.downloader = None
        engine.scheduler = None
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        # 第一次调用
        await engine.close_spider()
        assert engine._spider_closed is True

        # 第二次调用（应跳过）
        await engine.close_spider()
        assert engine._spider_closed is True


# ============================================================
# 5.7: _create_background_task 引用追踪
# ============================================================
class TestOptimization_5_7_BackgroundTaskTracking:
    """验证 _create_background_task 正确追踪和清理任务引用"""

    def test_engine_has_background_tasks_and_method(self):
        """Engine 应有 _background_tasks set 和 _create_background_task 方法"""
        from crawlo.core.engine import Engine
        assert hasattr(Engine, '_create_background_task')
        # _background_tasks 是实例属性，通过检查 __init__ 源码确认
        import inspect
        source = inspect.getsource(Engine.__init__)
        assert '_background_tasks' in source

    def test_middleware_manager_has_background_tasks_and_method(self):
        """MiddlewareManager 应有 _background_tasks set 和 _create_background_task 方法"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        assert hasattr(MiddlewareManager, '_create_background_task')
        import inspect
        source = inspect.getsource(MiddlewareManager.__init__)
        assert '_background_tasks' in source

    @pytest.mark.asyncio
    async def test_task_added_to_set_on_create(self):
        """创建任务后应添加到 _background_tasks"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = None
        engine.downloader = None
        engine.scheduler = None
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        async def dummy_coro():
            await asyncio.sleep(0.01)

        task = engine._create_background_task(dummy_coro())
        assert task in engine._background_tasks, "任务应被添加到 _background_tasks"

        await task
        # done_callback 应自动移除
        assert task not in engine._background_tasks, "任务完成后应从 _background_tasks 自动移除"

    @pytest.mark.asyncio
    async def test_failed_task_removed_from_set(self):
        """异常任务完成后也应从集合中移除"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = None
        engine.downloader = None
        engine.scheduler = None
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        async def failing_coro():
            raise ValueError("test failure")

        task = engine._create_background_task(failing_coro())
        assert task in engine._background_tasks

        with pytest.raises(ValueError):
            await task

        # 即使任务异常，也应从集合移除
        assert task not in engine._background_tasks

    @pytest.mark.asyncio
    async def test_multiple_tasks_tracked_independently(self):
        """多个任务应独立追踪"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = None
        engine.downloader = None
        engine.scheduler = None
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        async def dummy():
            await asyncio.sleep(0.05)

        tasks = [engine._create_background_task(dummy()) for _ in range(5)]
        assert len(engine._background_tasks) == 5

        await asyncio.gather(*tasks)
        assert len(engine._background_tasks) == 0


# ============================================================
# 3.1: isEnabledFor 日志守卫
# ============================================================
class TestOptimization_3_1_IsEnabledForGuard:
    """验证中间件日志使用 isEnabledFor(10) 守卫避免不必要的字符串格式化"""

    def test_process_request_has_guard(self):
        """_process_request 应使用 isEnabledFor(10) 守卫"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_request)
        assert 'isEnabledFor(10)' in source or 'isEnabledFor(logging.DEBUG)' in source, \
            "_process_request 应使用 isEnabledFor(10) 守卫日志"

    def test_process_exception_has_guard(self):
        """_process_exception 应使用 isEnabledFor(10) 守卫"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_exception)
        assert 'isEnabledFor(10)' in source or 'isEnabledFor(logging.DEBUG)' in source, \
            "_process_exception 应使用 isEnabledFor(10) 守卫日志"

    def test_wrapped_download_has_guard(self):
        """wrapped_download 应使用 isEnabledFor(10) 守卫"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_request)
        # wrapped_download 定义在 _process_request 内部
        assert 'isEnabledFor(10)' in source, \
            "wrapped_download 应使用 isEnabledFor(10) 守卫日志"

    def test_no_unconditional_debug_f_string(self):
        """不应有无守卫的 self.logger.debug(f"...")"""
        import inspect
        from crawlo.middleware.middleware_manager import MiddlewareManager
        source = inspect.getsource(MiddlewareManager._process_request)
        # 找出不在 isEnabledFor 守卫内的 self.logger.debug 调用
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'self.logger.debug' in stripped and not stripped.startswith('#'):
                # 检查上一行是否有 isEnabledFor 守卫
                if i > 0 and 'isEnabledFor' not in lines[i-1]:
                    # 允许非 f-string 的 debug（不涉及格式化开销）
                    if 'f"' in stripped or "f'" in stripped:
                        pytest.fail(
                            f"第 {i} 行有无守卫的 self.logger.debug(f\"...\"): {stripped}"
                        )


# ============================================================
# 5.9: Processor QueueEmpty 异常模式
# ============================================================
class TestOptimization_5_9_ProcessorQueueEmpty:
    """验证 Processor 使用 get_nowait() + QueueEmpty 替代 queue.empty()"""

    def test_process_once_uses_try_except_queue_empty(self):
        """process_once 应使用 try/except asyncio.QueueEmpty 模式"""
        import inspect
        from crawlo.core.processor import Processor
        source = inspect.getsource(Processor.process_once)
        assert 'QueueEmpty' in source, "process_once 应捕获 asyncio.QueueEmpty"
        assert 'get_nowait' in source, "process_once 应使用 get_nowait()"
        # 不应有 while not self.queue.empty():
        assert 'while not self.queue.empty()' not in source, \
            "process_once 不应使用 queue.empty() 检查，存在竞态窗口"

    def test_drain_queue_uses_try_except_queue_empty(self):
        """_drain_queue 应使用 try/except asyncio.QueueEmpty 模式"""
        import inspect
        from crawlo.core.processor import Processor
        source = inspect.getsource(Processor._drain_queue)
        assert 'QueueEmpty' in source, "_drain_queue 应捕获 asyncio.QueueEmpty"
        assert 'while not self.queue.empty()' not in source, \
            "_drain_queue 不应使用 queue.empty() 检查"

    @pytest.mark.asyncio
    async def test_process_once_on_empty_queue(self):
        """空队列时 process_once 不应报错"""
        from crawlo.core.processor import Processor

        crawler = Mock()
        crawler.settings = {}
        crawler.engine = AsyncMock()
        crawler.middleware_manager = None

        processor = Processor.__new__(Processor)
        processor.crawler = crawler
        processor.queue = asyncio.Queue()
        processor.pipelines = AsyncMock()
        processor.logger = get_test_logger()
        processor._lock = AsyncMock()
        processor._lock.__aenter__ = AsyncMock(return_value=None)
        processor._lock.__aexit__ = AsyncMock(return_value=None)
        processor._state = type('S', (), {'name': 'IDLE'})()
        processor._task = None
        processor._stop_event = asyncio.Event()
        processor._processed_count = 0
        processor._item_count = 0
        processor._request_count = 0
        processor._error_count = 0
        processor._processing = {}
        processor._processing_counter = 0
        processor._batch_size = 10
        processor._timeout = 1.0

        # 空队列不应报错
        await processor.process_once()

    @pytest.mark.asyncio
    async def test_process_once_processes_all_items(self):
        """process_once 应处理完队列中所有项目"""
        from crawlo.core.processor import Processor
        from crawlo import Item

        processed = []

        crawler = Mock()
        crawler.settings = {}
        crawler.engine = AsyncMock()
        crawler.middleware_manager = None

        processor = Processor.__new__(Processor)
        processor.crawler = crawler
        processor.queue = asyncio.Queue()
        processor.pipelines = AsyncMock()
        processor.logger = get_test_logger()
        processor._lock = AsyncMock()
        processor._lock.__aenter__ = AsyncMock(return_value=None)
        processor._lock.__aexit__ = AsyncMock(return_value=None)
        processor._state = type('S', (), {'name': 'IDLE'})()
        processor._task = None
        processor._stop_event = asyncio.Event()
        processor._processed_count = 0
        processor._item_count = 0
        processor._request_count = 0
        processor._error_count = 0
        processor._processing = {}
        processor._processing_counter = 0
        processor._batch_size = 10
        processor._timeout = 1.0

        # Mock _handle_result
        async def mock_handle(result):
            processed.append(result)
        processor._handle_result = mock_handle

        # 添加 3 个 Item
        for i in range(3):
            item = Item()
            item['data'] = i
            await processor.queue.put(item)

        await processor.process_once()
        assert len(processed) == 3, f"应处理 3 个项目，实际处理了 {len(processed)} 个"
        assert processor.queue.empty()


# ============================================================
# 4.1: Scheduler _get_setting/_set_setting 辅助方法
# ============================================================
class TestOptimization_4_1_SchedulerHelperMethods:
    """验证 Scheduler 使用辅助方法替代重复的防御性代码"""

    def test_has_get_setting_method(self):
        """Scheduler 应有 _get_setting 方法"""
        from crawlo.core.scheduler import Scheduler
        assert hasattr(Scheduler, '_get_setting')

    def test_has_set_setting_method(self):
        """Scheduler 应有 _set_setting 方法"""
        from crawlo.core.scheduler import Scheduler
        assert hasattr(Scheduler, '_set_setting')

    @pytest.mark.asyncio
    async def test_get_setting_returns_default_when_no_crawler(self):
        """无 crawler 时返回默认值"""
        from crawlo.core.scheduler import Scheduler

        scheduler = Scheduler.__new__(Scheduler)
        scheduler.crawler = None
        scheduler.queue_manager = None
        scheduler.logger = get_test_logger()
        scheduler.error_handler = Mock()

        assert scheduler._get_setting('KEY', 'default') == 'default'

    @pytest.mark.asyncio
    async def test_get_setting_returns_default_when_no_settings(self):
        """settings 为 None 时返回默认值"""
        from crawlo.core.scheduler import Scheduler

        scheduler = Scheduler.__new__(Scheduler)
        scheduler.crawler = Mock()
        scheduler.crawler.settings = None
        scheduler.queue_manager = None
        scheduler.logger = get_test_logger()
        scheduler.error_handler = Mock()

        assert scheduler._get_setting('KEY', 'default') == 'default'

    @pytest.mark.asyncio
    async def test_get_setting_returns_value(self):
        """正常情况返回配置值"""
        from crawlo.core.scheduler import Scheduler
        from crawlo.settings.setting_manager import SettingManager

        settings = SettingManager()
        settings.update_attributes({'TEST_KEY': 'test_value'})

        scheduler = Scheduler.__new__(Scheduler)
        scheduler.crawler = Mock()
        scheduler.crawler.settings = settings
        scheduler.queue_manager = None
        scheduler.logger = get_test_logger()
        scheduler.error_handler = Mock()

        assert scheduler._get_setting('TEST_KEY', 'default') == 'test_value'

    @pytest.mark.asyncio
    async def test_get_setting_handles_exception(self):
        """settings.get 抛异常时返回默认值"""
        from crawlo.core.scheduler import Scheduler

        bad_settings = Mock()
        bad_settings.get = Mock(side_effect=RuntimeError("boom"))

        scheduler = Scheduler.__new__(Scheduler)
        scheduler.crawler = Mock()
        scheduler.crawler.settings = bad_settings
        scheduler.queue_manager = None
        scheduler.logger = get_test_logger()
        scheduler.error_handler = Mock()

        assert scheduler._get_setting('KEY', 'safe_default') == 'safe_default'

    @pytest.mark.asyncio
    async def test_set_setting_handles_exception_silently(self):
        """_set_setting 异常时不应抛出"""
        from crawlo.core.scheduler import Scheduler

        bad_settings = Mock()
        bad_settings.set = Mock(side_effect=RuntimeError("boom"))

        scheduler = Scheduler.__new__(Scheduler)
        scheduler.crawler = Mock()
        scheduler.crawler.settings = bad_settings
        scheduler.queue_manager = None
        scheduler.logger = get_test_logger()
        scheduler.error_handler = Mock()

        # 不应抛异常
        scheduler._set_setting('KEY', 'value')


# ============================================================
# 3.2: Scheduler Condition 等待替代轮询
# ============================================================
class TestOptimization_3_2_SchedulerConditionWait:
    """验证 Scheduler 使用 asyncio.Condition 替代 sleep 轮询"""

    def test_has_queue_not_full_condition(self):
        """Scheduler 应有 _queue_not_full = asyncio.Condition()"""
        from crawlo.core.scheduler import Scheduler
        # 检查 __init__ 中是否有 _queue_not_full
        import inspect
        source = inspect.getsource(Scheduler.__init__)
        assert '_queue_not_full' in source, "Scheduler.__init__ 应包含 _queue_not_full"
        assert 'Condition' in source, "Scheduler 应使用 asyncio.Condition"

    def test_enqueue_uses_condition_wait(self):
        """enqueue_request 应使用 Condition 等待而非 sleep"""
        import inspect
        from crawlo.core.scheduler import Scheduler
        source = inspect.getsource(Scheduler.enqueue_request)
        assert '_queue_not_full' in source, "enqueue_request 应使用 _queue_not_full Condition"
        assert 'asyncio.sleep' not in source or 'wait()' in source, \
            "enqueue_request 应使用 Condition.wait() 替代 asyncio.sleep 轮询"

    def test_next_request_notifies(self):
        """next_request 应在出队后 notify_all"""
        import inspect
        from crawlo.core.scheduler import Scheduler
        source = inspect.getsource(Scheduler.next_request)
        assert 'notify_all' in source or 'notify()' in source, \
            "next_request 应调用 notify_all 通知等待的入队协程"


# ============================================================
# 5.10: Redis 过滤器保守错误处理
# ============================================================
class TestOptimization_5_10_RedisFilterConservativeError:
    """验证 AioRedisFilter 在网络错误时返回 False（宁可重复，不可丢失）"""

    def test_requested_async_returns_false_on_exception(self):
        """requested_async 网络错误时应返回 False（放行请求，避免数据丢失）"""
        import inspect
        from crawlo.filters.aioredis_filter import AioRedisFilter
        source = inspect.getsource(AioRedisFilter.requested_async)

        # 检查 except 块中 return False
        lines = source.split('\n')
        in_except = False
        return_found = False
        for line in lines:
            stripped = line.strip()
            if 'except Exception' in stripped:
                in_except = True
            if in_except and 'return False' in stripped and 'return False  # 宁可重复' in stripped:
                return_found = True
                break
            if in_except and 'return False' in stripped:
                return_found = True
                break

        assert return_found, \
            "AioRedisFilter.requested_async 的 except 块应返回 False（宁可重复，不可丢失）"

    def test_contains_async_returns_false_on_exception(self):
        """contains_async 网络错误时应返回 False（放行请求，避免数据丢失）"""
        import inspect
        from crawlo.filters.aioredis_filter import AioRedisFilter
        source = inspect.getsource(AioRedisFilter.contains_async)

        lines = source.split('\n')
        in_except = False
        for line in lines:
            stripped = line.strip()
            if 'except Exception' in stripped:
                in_except = True
            if in_except and 'return False' in stripped:
                return
        pytest.fail("AioRedisFilter.contains_async 的 except 块应返回 False（宁可重复，不可丢失）")

    @pytest.mark.asyncio
    async def test_requested_async_with_connection_failed(self):
        """_connection_failed=True 时 requested_async 应返回 True（跳过）"""
        from crawlo.filters.aioredis_filter import AioRedisFilter

        filter_obj = AioRedisFilter(redis_key='test', client=None)
        filter_obj._connection_failed = True

        mock_request = Mock()
        mock_request.url = 'http://example.com'
        mock_request.method = 'GET'
        mock_request.meta = {}
        mock_request.headers = {}
        mock_request.params = {}
        mock_request.body = b''
        mock_request.dont_filter = False
        mock_request.callback = None
        mock_request.errback = None

        # _connection_failed -> _get_redis_client returns None -> requested_async returns False
        # 但这不是 "网络错误时返回 True" 的场景，而是 "无 Redis 时放行"
        # 实际上 _get_redis_client 返回 None 时返回 False（放行请求）
        result = await filter_obj.requested_async(mock_request)
        # Redis 不可用，请求不被视为重复 -> False（放行）
        assert result is False, "Redis 不可用时应放行请求（返回 False）"

    @pytest.mark.asyncio
    async def test_contains_async_with_mock_redis_error(self):
        """Redis 操作异常时 contains_async 应返回 False（放行请求，避免数据丢失）"""
        from crawlo.filters.aioredis_filter import AioRedisFilter

        # Mock redis client that throws error
        mock_redis = Mock()
        mock_redis.sismember = Mock(side_effect=ConnectionError("Redis connection lost"))

        filter_obj = AioRedisFilter(redis_key='test:filter', client=mock_redis)
        result = await filter_obj.contains_async('test_fingerprint')
        assert result is False, "Redis 网络错误时 contains_async 应返回 False（宁可重复，不可丢失）"


# ============================================================
# 6.2: extras_require 依赖拆分
# ============================================================
class TestOptimization_6_2_ExtrasRequire:
    """验证 setup.cfg 中数据库依赖已移到 extras_require"""

    def test_database_extras_exist(self):
        """setup.cfg 应有 [options.extras_require] 下的 database 分组"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        assert cfg.has_section('options.extras_require'), "缺少 [options.extras_require]"

    def test_asyncmy_not_in_install_requires(self):
        """asyncmy 不应在 install_requires 中"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        install_requires = cfg.get('options', 'install_requires')
        assert 'asyncmy' not in install_requires, "asyncmy 应在 extras_require 中，而非 install_requires"

    def test_motor_not_in_install_requires(self):
        """motor 不应在 install_requires 中"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        install_requires = cfg.get('options', 'install_requires')
        assert 'motor' not in install_requires, "motor 应在 extras_require 中，而非 install_requires"

    def test_pymongo_not_in_install_requires(self):
        """pymongo 不应在 install_requires 中"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        install_requires = cfg.get('options', 'install_requires')
        assert 'pymongo' not in install_requires, "pymongo 应在 extras_require 中，而非 install_requires"

    def test_database_extras_has_asyncmy(self):
        """database extras 应包含 asyncmy"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        database = cfg.get('options.extras_require', 'database', fallback='')
        assert 'asyncmy' in database, "database extras 应包含 asyncmy"

    def test_database_extras_has_motor(self):
        """database extras 应包含 motor"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        database = cfg.get('options.extras_require', 'database', fallback='')
        assert 'motor' in database, "database extras 应包含 motor"

    def test_database_extras_has_pymongo(self):
        """database extras 应包含 pymongo"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        database = cfg.get('options.extras_require', 'database', fallback='')
        assert 'pymongo' in database, "database extras 应包含 pymongo"

    def test_all_extras_includes_database(self):
        """all extras 应引用 database（configparser 会自动展开引用）"""
        cfg = configparser.ConfigParser()
        cfg.read('setup.cfg', encoding='utf-8')
        # configparser 自动展开 %(database)s 引用，检查展开后的内容
        all_extras = cfg.get('options.extras_require', 'all', fallback='')
        # 展开后应包含 database 组的内容
        assert 'asyncmy' in all_extras, "all extras 展开后应包含 asyncmy（来自 database 组）"
        assert 'motor' in all_extras, "all extras 展开后应包含 motor（来自 database 组）"

    def test_raw_config_has_database_reference(self):
        """原始 setup.cfg 文件中 all 应有 %(database)s 引用"""
        with open('setup.cfg', 'r', encoding='utf-8') as f:
            content = f.read()
        # 找到 [options.extras_require] 下的 all 部分
        in_extras = False
        in_all = False
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped == '[options.extras_require]':
                in_extras = True
                continue
            if in_extras and stripped.startswith('['):
                break
            if in_extras and stripped == 'all =':
                in_all = True
                continue
            if in_all and '%(database)s' in stripped:
                return  # 找到了
            if in_all and stripped and not stripped.startswith(('bitarray', 'PyExecJS', 'pymongo', 'redis-py', '%(render', '%(mcp')):
                # 跳过已知行，如果在所有行之后还没找到就失败
                pass
        # 直接检查原始内容
        assert '%(database)s' in content.split('[options.extras_require]')[1].split('[options')[0], \
            "all extras 应在原始 setup.cfg 中引用 %(database)s"


# ============================================================
# 2.1: Engine Event 驱动主循环
# ============================================================
class TestOptimization_2_1_EngineEventDriven:
    """验证 Engine 使用 asyncio.Event 替代忙等待"""

    def test_has_request_available_event(self):
        """Engine 应有 _request_available = asyncio.Event()"""
        from crawlo.core.engine import Engine
        import inspect
        source = inspect.getsource(Engine.__init__)
        assert '_request_available' in source, "Engine.__init__ 应包含 _request_available"
        assert 'asyncio.Event' in source, "Engine 应使用 asyncio.Event"

    def test_schedule_request_sets_event(self):
        """_schedule_request 成功入队后应 set event"""
        import inspect
        from crawlo.core.engine import Engine
        source = inspect.getsource(Engine._schedule_request)
        assert '_request_available.set()' in source, \
            "_schedule_request 成功入队后应调用 _request_available.set()"

    def test_crawl_loop_uses_event_wait(self):
        """crawl 主循环空闲时应使用 event.wait()"""
        import inspect
        from crawlo.core.engine import Engine
        source = inspect.getsource(Engine.crawl)
        assert '_request_available.wait()' in source, \
            "crawl 主循环应使用 _request_available.wait() 替代纯 sleep 忙等待"

    def test_crawl_loop_clears_event(self):
        """crawl 主循环处理请求后应 clear event"""
        import inspect
        from crawlo.core.engine import Engine
        source = inspect.getsource(Engine.crawl)
        assert '_request_available.clear()' in source, \
            "crawl 主循环应在处理请求后 clear event"

    @pytest.mark.asyncio
    async def test_event_is_set_on_schedule(self):
        """调度请求时 Event 应被 set"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        crawler.spider = Mock()
        crawler.subscriber = AsyncMock()

        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = crawler.spider
        engine.downloader = None
        engine.scheduler = AsyncMock()
        engine.scheduler.enqueue_request = AsyncMock(return_value=True)
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        # 初始状态 event 不应被 set
        assert engine._request_available.is_set() is False

        from crawlo import Request
        req = Request('http://example.com')
        await engine._schedule_request(req)

        assert engine._request_available.is_set() is True, \
            "_schedule_request 成功后 _request_available 应被 set"

    @pytest.mark.asyncio
    async def test_event_not_set_on_enqueue_failure(self):
        """入队失败时 Event 不应被 set"""
        from crawlo.core.engine import Engine

        crawler = Mock()
        crawler.settings = {}
        crawler.spider = Mock()
        crawler.subscriber = AsyncMock()

        engine = Engine.__new__(Engine)
        engine.running = False
        engine.normal = True
        engine.crawler = crawler
        engine.settings = {}
        engine.spider = crawler.spider
        engine.downloader = None
        engine.scheduler = AsyncMock()
        engine.scheduler.enqueue_request = AsyncMock(return_value=False)
        engine.processor = None
        engine._start_requests_source = None
        engine._start_requests_is_async = False
        engine._close_reason = 'finished'
        engine._spider_closed = False
        engine._background_tasks = set()
        engine._request_available = asyncio.Event()
        engine.logger = get_test_logger()
        engine._init_configs()
        engine.task_manager = None

        from crawlo import Request
        req = Request('http://example.com')
        await engine._schedule_request(req)

        assert engine._request_available.is_set() is False, \
            "入队失败时 _request_available 不应被 set"


# ============================================================
# Helper
# ============================================================
def get_test_logger():
    """创建测试用 logger，避免污染全局日志"""
    import logging
    logger = logging.getLogger(f'test.{id(__import__("threading").current_thread())}')
    logger.setLevel(logging.CRITICAL)
    return logger
