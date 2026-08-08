#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 CRITICAL-3: Crawler._cleanup 重复清理 Engine 的修复

验证点：
1. Engine.close_spider() 是幂等的（多次调用安全）
2. Crawler._cleanup() 不再重复调用 _cleanup_engine()
3. StatsCollector.close() 是幂等的
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


class TestEngineCloseSpiderIdempotent:
    """测试 Engine.close_spider() 的幂等性"""

    @pytest.fixture
    def mock_crawler(self):
        crawler = MagicMock()
        crawler.settings = {}
        return crawler

    @pytest.fixture
    def engine(self, mock_crawler):
        from crawlo.core.engine import Engine
        with patch.object(Engine, '__init__', lambda self, crawler: None):
            eng = Engine.__new__(Engine)
            eng.running = False
            eng.normal = True
            eng.crawler = mock_crawler
            eng.settings = {}
            eng.spider = None
            eng.downloader = None
            eng.scheduler = None
            eng.processor = None
            eng.start_requests = None
            eng._close_reason = 'finished'
            eng._spider_closed = False
            eng.logger = MagicMock()
            eng.task_manager = None
            return eng

    @pytest.mark.asyncio
    async def test_close_spider_idempotent_flag(self, engine):
        """close_spider 设置 _spider_closed 标志"""
        assert engine._spider_closed is False
        await engine.close_spider(reason='finished')
        assert engine._spider_closed is True

    @pytest.mark.asyncio
    async def test_close_spider_only_runs_once(self, engine):
        """close_spider 只执行一次清理逻辑"""
        # 设置必要的 mock
        engine.task_manager = MagicMock()
        engine.task_manager.current_task = []
        engine.processor = MagicMock()
        engine.processor.pipelines = AsyncMock()
        engine.scheduler = MagicMock()
        engine.scheduler.close = AsyncMock()

        # 第一次调用
        await engine.close_spider(reason='finished')
        assert engine.scheduler.close.call_count == 1

        # 第二次调用 - 应该跳过
        await engine.close_spider(reason='finished')
        assert engine.scheduler.close.call_count == 1  # 仍然是1，没有增加

    @pytest.mark.asyncio
    async def test_close_spider_different_reasons(self, engine):
        """第二次调用即使 reason 不同也跳过"""
        engine.task_manager = MagicMock()
        engine.task_manager.current_task = []
        engine.processor = MagicMock()
        engine.processor.pipelines = AsyncMock()
        engine.scheduler = MagicMock()
        engine.scheduler.close = AsyncMock()

        await engine.close_spider(reason='finished')
        assert engine._close_reason == 'finished'

        await engine.close_spider(reason='shutdown')
        assert engine._close_reason == 'finished'  # 不应被覆盖


class TestCrawlerCleanupNoDoubleEngine:
    """测试 Crawler._cleanup 不再重复清理 Engine"""

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.get = MagicMock(return_value=None)
        settings.attributes = {}
        return settings

    def test_cleanup_does_not_call_cleanup_engine(self, mock_settings):
        """验证 _cleanup 方法中不再调用 _cleanup_engine"""
        import inspect
        import ast
        import textwrap
        from crawlo.crawler import Crawler

        # 解析 _cleanup 的 AST，确保没有 _cleanup_engine 的调用
        source = textwrap.dedent(inspect.getsource(Crawler._cleanup))
        tree = ast.parse(source)
        
        call_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    call_names.append(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    call_names.append(node.func.id)
        
        assert '_cleanup_engine' not in call_names, (
            "_cleanup() should not call _cleanup_engine() since "
            "Engine.close_spider() is already called in Engine.crawl() finally block"
        )

    @pytest.mark.asyncio
    async def test_cleanup_calls_stats(self, mock_settings):
        """验证 _cleanup 仍然调用 _cleanup_stats"""
        from crawlo.crawler import Crawler, CrawlerState

        with patch('crawlo.crawler.initialize_framework'), \
             patch('crawlo.crawler.is_framework_ready', return_value=True), \
             patch('crawlo.crawler.get_logger', return_value=MagicMock()):
            crawler = Crawler.__new__(Crawler)
            crawler._state = CrawlerState.RUNNING
            crawler._state_lock = asyncio.Lock()
            crawler._resource_manager = MagicMock()
            crawler._resource_manager.cleanup_all = AsyncMock(return_value={
                'success': 0, 'errors': 0, 'duration': 0.0
            })
            crawler._engine = None
            crawler._stats = MagicMock()
            crawler._stats.close_spider = MagicMock()
            crawler._stats.close = MagicMock()
            crawler._subscriber = None
            crawler._logger = MagicMock()
            crawler._close_logger_handlers = MagicMock()

            # Mock _cleanup_stats
            crawler._cleanup_stats = AsyncMock()

            await crawler._cleanup(reason='finished')

            # _cleanup_stats 应该被调用
            crawler._cleanup_stats.assert_called_once_with('finished')


class TestStatsCollectorCloseIdempotent:
    """测试 StatsCollector.close() 的幂等性"""

    def test_close_is_idempotent(self):
        """close 方法只执行一次"""
        from crawlo.stats.collector import StatsCollector

        with patch('crawlo.stats.collector.StatsBackendFactory') as mock_factory:
            mock_backend = MagicMock()
            mock_backend.get_stats.return_value = {'spider_name': 'test'}
            mock_factory.from_settings.return_value = mock_backend

            crawler = MagicMock()
            crawler.settings = {}

            collector = StatsCollector(crawler)
            collector._dump = False  # 简化测试

            # 第一次调用
            collector.close()
            assert collector._closed is True
            assert mock_backend.close.call_count == 1

            # 第二次调用 - 应该跳过
            collector.close()
            assert mock_backend.close.call_count == 1  # 仍然是1

    def test_close_flag_initialized_false(self):
        """_closed 标志初始为 False"""
        from crawlo.stats.collector import StatsCollector

        with patch('crawlo.stats.collector.StatsBackendFactory') as mock_factory:
            mock_factory.from_settings.return_value = MagicMock()

            crawler = MagicMock()
            crawler.settings = {}

            collector = StatsCollector(crawler)
            assert collector._closed is False
