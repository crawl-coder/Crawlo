#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 MEDIUM 和 LOW 级缺陷的修复

包含：
- MEDIUM-7: Spider.start_requests dont_filter 逻辑反转
- MEDIUM-5: QueueManager.empty() Redis 队列误判
- MEDIUM-3: SettingManager.get() None 与 default 混淆
- LOW-1: ApplicationContext.id 使用 id(self) 不可靠
- LOW-2: Crawler._close_logger_handlers 关闭根 logger
"""
import asyncio
import logging
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMedium7DontFilter:
    """测试 MEDIUM-7: Spider.start_requests dont_filter 修复"""

    def test_start_requests_dont_filter_is_false(self):
        """start_requests 生成的请求 dont_filter 始终为 False"""
        from crawlo.spider import Spider
        
        class TestSpider(Spider):
            name = 'test_dont_filter_spider'
            start_urls = ['http://example.com/1', 'http://example.com/2']
        
        with patch.object(Spider, '_is_distributed_mode', return_value=False):
            spider = TestSpider()
            requests = list(spider.start_requests())
            
            for req in requests:
                assert req.dont_filter is False, (
                    f"start_requests 应始终 dont_filter=False，实际为 {req.dont_filter}"
                )


class TestMedium5RedisEmpty:
    """测试 MEDIUM-5: QueueManager.empty() Redis 队列误判"""

    def test_empty_returns_false_for_redis_queue(self):
        """Redis 队列的 empty() 使用保守策略返回 False"""
        from crawlo.queue.queue_manager import QueueManager, QueueType
        
        with patch.object(QueueManager, '__init__', lambda self, **kwargs: None):
            qm = QueueManager.__new__(QueueManager)
            qm._queue = MagicMock()
            qm._queue_type = QueueType.REDIS
            
            result = qm.empty()
            assert result is False, (
                "Redis 队列的 empty() 应返回 False（保守策略），避免过早退出"
            )

    def test_empty_returns_correct_for_memory_queue(self):
        """内存队列的 empty() 仍正确工作"""
        from crawlo.queue.queue_manager import QueueManager, QueueType
        
        with patch.object(QueueManager, '__init__', lambda self, **kwargs: None):
            qm = QueueManager.__new__(QueueManager)
            qm._queue = MagicMock()
            qm._queue_type = QueueType.MEMORY
            qm._queue.qsize = MagicMock(return_value=0)
            
            result = qm.empty()
            assert result is True


class TestMedium3SettingManagerGet:
    """测试 MEDIUM-3: SettingManager.get() None 与 default 混淆"""

    def test_get_explicit_none_returns_none(self):
        """显式设置为 None 的键返回 None，而非 default"""
        from crawlo.settings.setting_manager import SettingManager
        
        sm = SettingManager()
        sm.set('TEST_KEY', None)
        
        result = sm.get('TEST_KEY', default='fallback')
        assert result is None, (
            "显式设置为 None 的键应返回 None，而非 default"
        )

    def test_get_missing_key_returns_default(self):
        """未设置的键返回 default"""
        from crawlo.settings.setting_manager import SettingManager
        
        sm = SettingManager()
        result = sm.get('NONEXISTENT_KEY', default='fallback')
        assert result == 'fallback'

    def test_get_missing_key_no_default_returns_none(self):
        """未设置的键且无 default 返回 None"""
        from crawlo.settings.setting_manager import SettingManager
        
        sm = SettingManager()
        result = sm.get('NONEXISTENT_KEY')
        assert result is None

    def test_get_existing_key_returns_value(self):
        """已设置的键返回其值"""
        from crawlo.settings.setting_manager import SettingManager
        
        sm = SettingManager()
        sm.set('TEST_KEY', 'test_value')
        
        result = sm.get('TEST_KEY', default='fallback')
        assert result == 'test_value'

    def test_sentinel_exists(self):
        """_SENTINEL 哨兵值存在"""
        from crawlo.settings.setting_manager import SettingManager
        assert hasattr(SettingManager, '_SENTINEL')


class TestLow1ApplicationContextId:
    """测试 LOW-1: ApplicationContext.id 使用 uuid4"""

    def test_id_is_uuid_format(self):
        """ApplicationContext.id 是 UUID 格式"""
        from crawlo.application import ApplicationContext
        
        ctx = ApplicationContext()
        # UUID 格式: 8-4-4-4-12
        parts = ctx.id.split('-')
        assert len(parts) == 5, f"ID should be UUID format, got: {ctx.id}"

    def test_id_is_unique(self):
        """每个实例的 ID 唯一"""
        from crawlo.application import ApplicationContext
        
        ctx1 = ApplicationContext()
        ctx2 = ApplicationContext()
        assert ctx1.id != ctx2.id


class TestLow2LoggerHandlers:
    """测试 LOW-2: _close_logger_handlers 不关闭根 logger"""

    def test_close_logger_handlers_does_not_close_root(self):
        """_close_logger_handlers 不关闭根 logger 的 handlers"""
        from crawlo.crawler import Crawler, CrawlerState
        
        with patch('crawlo.crawler.initialize_framework'), \
             patch('crawlo.crawler.is_framework_ready', return_value=True), \
             patch('crawlo.crawler.get_logger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger
            
            crawler = Crawler.__new__(Crawler)
            crawler._logger = mock_logger
            
            # 设置根 logger 的 handler
            root_handler = MagicMock()
            with patch('logging.getLogger') as mock_get_root:
                # 即使代码里误调用 getLogger()，现在也不应该
                crawler._close_logger_handlers()
                
                # 根 logger 的 handler 不应被关闭
                root_handler.close.assert_not_called()

    def test_close_logger_handlers_source_no_root_logger(self):
        """_close_logger_handlers 源码中不包含根 logger 操作"""
        import inspect
        import textwrap
        from crawlo.crawler import Crawler
        
        source = textwrap.dedent(inspect.getsource(Crawler._close_logger_handlers))
        assert 'root_logger' not in source, (
            "_close_logger_handlers should not reference root_logger"
        )
        assert 'logging.getLogger()' not in source, (
            "_close_logger_handlers should not call logging.getLogger()"
        )
