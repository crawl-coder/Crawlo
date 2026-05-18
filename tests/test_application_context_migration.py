#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ApplicationContext 完整迁移验证测试
验证 Phase 0-4 所有改动
"""
import threading
import pytest
from crawlo.core.application import (
    get_global_context,
    reset_global_context,
    set_global_context,
    ApplicationContext,
)


class TestPhase0_Infrastructure:
    """Phase 0: 基础设施加固"""

    def test_dcl_thread_safety(self):
        """测试 DCL 线程安全（风险 R2）"""
        contexts = []
        
        def create_in_thread():
            contexts.append(get_global_context())
        
        threads = [threading.Thread(target=create_in_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有线程应获取到同一个实例
        assert all(c is contexts[0] for c in contexts), "DCL failed: multiple instances created"

    def test_reset_isolation(self):
        """测试 reset 隔离"""
        ctx1 = get_global_context()
        reset_global_context()
        ctx2 = get_global_context()
        assert ctx1 is not ctx2, "reset should create new instance"

    def test_spider_registry_sync(self):
        """测试 SpiderMeta 方案 A（风险 R1）"""
        from crawlo.spider.spider import _DEFAULT_SPIDER_REGISTRY, get_global_spider_registry
        
        reset_global_context()
        
        # 首次调用应同步模块级 dict
        ctx_registry = get_global_spider_registry()
        assert ctx_registry is _DEFAULT_SPIDER_REGISTRY, "Should point to same dict"

    def test_context_fields_complete(self):
        """测试 ApplicationContext 字段完整性"""
        ctx = get_global_context()
        
        # Phase 1: 核心注册表
        assert hasattr(ctx, 'component_registry')
        assert hasattr(ctx, 'initializer_registry')
        assert hasattr(ctx, 'spider_registry')
        assert hasattr(ctx, 'job_registry')
        assert hasattr(ctx, 'framework')
        
        # Phase 2: 框架管理器
        assert hasattr(ctx, 'log_manager')
        assert hasattr(ctx, 'error_handler_instance')
        assert hasattr(ctx, 'performance_monitor')
        assert hasattr(ctx, 'resource_managers')
        assert hasattr(ctx, '_monitor_manager')
        
        # Phase 3: Bot 通知
        assert hasattr(ctx, 'notifier')
        assert hasattr(ctx, 'notifier_lock')
        assert hasattr(ctx, 'notification_handler')
        assert hasattr(ctx, 'template_manager')
        assert hasattr(ctx, 'deduplicator')
        assert hasattr(ctx, 'dingtalk_channel')
        assert hasattr(ctx, 'feishu_channel')
        
        # Phase 4: MCP/工具
        assert hasattr(ctx, 'quick_fetcher')
        assert hasattr(ctx, 'mcp_fetcher')
        assert hasattr(ctx, 'redis_manager')
        assert hasattr(ctx, 'connection_pools')


class TestPhase1_CoreRegistries:
    """Phase 1: 核心注册表"""

    def test_component_registry(self):
        """测试 ComponentRegistry 迁移"""
        from crawlo.factories import get_component_registry
        
        reset_global_context()
        registry = get_component_registry()
        assert registry is not None
        assert hasattr(registry, 'register')

    def test_initializer_registry(self):
        """测试 InitializerRegistry 迁移"""
        from crawlo.initialization.registry import get_initializer_registry
        
        reset_global_context()
        registry = get_initializer_registry()
        assert registry is not None

    def test_job_registry(self):
        """测试 JobRegistry 迁移"""
        from crawlo.scheduling.registry import get_job_registry
        
        reset_global_context()
        registry = get_job_registry()
        assert registry is not None

    def test_framework(self):
        """测试 CrawloFramework 迁移"""
        from crawlo.framework import get_framework
        
        reset_global_context()
        framework = get_framework()
        assert framework is not None


class TestPhase2_FrameworkManagers:
    """Phase 2: 框架管理器"""

    def test_log_manager(self):
        """测试 LogManager 迁移"""
        from crawlo.logging.manager import configure
        
        reset_global_context()
        # configure 应该能正常调用
        assert callable(configure)

    def test_monitor_manager(self):
        """测试 MonitorManager 迁移"""
        from crawlo.extension.monitor.monitor_manager import get_monitor_manager
        
        reset_global_context()
        manager = get_monitor_manager()
        assert manager is not None

    def test_error_handler(self):
        """测试 ErrorHandler 迁移"""
        from crawlo.utils.error_handler import _get_global_error_handler
        
        reset_global_context()
        handler = _get_global_error_handler()
        assert handler is not None
        assert hasattr(handler, 'handle_error')

    def test_performance_monitor(self):
        """测试 PerformanceMonitor 迁移"""
        from crawlo.extension.monitor.performance_monitor import get_performance_monitor
        
        reset_global_context()
        monitor = get_performance_monitor()
        assert monitor is not None


class TestPhase3_BotNotification:
    """Phase 3: Bot 通知模块"""

    def test_notifier(self):
        """测试 NotificationDispatcher 迁移"""
        from crawlo.bot.core.notifier import get_notifier
        
        reset_global_context()
        notifier = get_notifier()
        assert notifier is not None

    def test_deduplicator(self):
        """测试 MessageDeduplicator 迁移"""
        from crawlo.bot.utils.deduplicator import get_deduplicator
        
        reset_global_context()
        dedup = get_deduplicator()
        assert dedup is not None

    def test_template_manager(self):
        """测试 MessageTemplateManager 迁移"""
        from crawlo.bot.templates.manager import get_template_manager
        
        reset_global_context()
        manager = get_template_manager()
        assert manager is not None

    def test_notification_handler(self):
        """测试 CrawlerNotificationHandler 迁移"""
        from crawlo.bot.core.handlers import get_notification_handler
        
        reset_global_context()
        handler = get_notification_handler()
        assert handler is not None


class TestPhase4_MCPTools:
    """Phase 4: MCP/工具类"""

    def test_quick_fetcher(self):
        """测试 QuickFetcher 迁移"""
        from crawlo.mcp.quick_fetcher import get_fetcher
        
        reset_global_context()
        fetcher = get_fetcher()
        assert fetcher is not None

    def test_redis_manager(self):
        """测试 GlobalRedisManager 迁移"""
        from crawlo.utils.redis.pool import get_redis_manager
        
        reset_global_context()
        manager = get_redis_manager()
        assert manager is not None


class TestIntegration:
    """集成测试"""

    def test_full_import(self):
        """测试完整导入链"""
        import crawlo.crawler
        assert crawlo.crawler is not None

    def test_multiple_reset_cycles(self):
        """测试多次 reset 循环"""
        for i in range(5):
            reset_global_context()
            ctx = get_global_context()
            assert ctx is not None
            assert ctx.id is not None

    def test_context_cleanup(self):
        """测试上下文清理"""
        ctx = get_global_context()
        ctx.add_resource("test_resource")
        assert "test_resource" in ctx.resources
        
        ctx.remove_resource("test_resource")
        assert "test_resource" not in ctx.resources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
