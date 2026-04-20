#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 HIGH-1: Subscriber.notify 事件异常静默吞噬的修复

验证点：
1. 关键事件（spider_closed 等）失败时使用 WARNING 级别
2. NotifyResult 提供结构化的错误信息
3. _last_notify_result 记录最近一次通知的执行状态
4. 普通事件仍使用 ERROR 级别
5. 向后兼容：notify() 仍返回 List[Any]
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from crawlo.subscriber import Subscriber, NotifyResult, CRITICAL_EVENTS


class TestNotifyResultDataclass:
    """测试 NotifyResult 数据类"""

    def test_notify_result_has_errors(self):
        """has_errors 正确反映错误状态"""
        result = NotifyResult(results=[1, 2], errors=[("func", ValueError("test"))], event="test")
        assert result.has_errors is True

    def test_notify_result_no_errors(self):
        """无错误时 has_errors 为 False"""
        result = NotifyResult(results=[1, 2], errors=[], event="test")
        assert result.has_errors is False

    def test_notify_result_counts(self):
        """success_count 和 error_count 正确"""
        result = NotifyResult(
            results=["ok", ValueError("err"), "ok2"],
            errors=[("func1", ValueError("err"))],
            event="test"
        )
        assert result.success_count == 2
        assert result.error_count == 1


class TestCriticalEventLogging:
    """测试关键事件的日志级别提升"""

    @pytest.mark.asyncio
    async def test_critical_event_uses_warning_level(self):
        """关键事件失败时使用 WARNING 级别"""
        sub = Subscriber(error_handling="log", timeout=0)

        async def failing_handler():
            raise RuntimeError("handler failed")

        sub.subscribe(failing_handler, event="spider_closed")

        with patch('crawlo.subscriber.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            results = await sub.notify("spider_closed")
            
            # 验证关键事件有 WARNING 日志
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("spider_closed" in call and "关键事件" in call for call in warning_calls), (
                f"Expected WARNING log for critical event, got: {warning_calls}"
            )

    @pytest.mark.asyncio
    async def test_normal_event_uses_error_level(self):
        """普通事件失败时使用 ERROR 级别"""
        sub = Subscriber(error_handling="log", timeout=0)

        async def failing_handler():
            raise RuntimeError("handler failed")

        sub.subscribe(failing_handler, event="request_scheduled")

        with patch('crawlo.subscriber.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            results = await sub.notify("request_scheduled")
            
            # 验证普通事件有 ERROR 日志
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("request_scheduled" in call or "执行失败" in call for call in error_calls), (
                f"Expected ERROR log for normal event, got: {error_calls}"
            )


class TestLastNotifyResult:
    """测试 _last_notify_result 属性"""

    @pytest.mark.asyncio
    async def test_last_notify_result_updated(self):
        """notify 后 _last_notify_result 被更新"""
        sub = Subscriber(error_handling="log", timeout=0)

        async def ok_handler():
            return "ok"

        sub.subscribe(ok_handler, event="test_event")

        assert sub._last_notify_result is None
        await sub.notify("test_event")

        assert sub._last_notify_result is not None
        assert isinstance(sub._last_notify_result, NotifyResult)
        assert sub._last_notify_result.event == "test_event"

    @pytest.mark.asyncio
    async def test_last_notify_result_with_errors(self):
        """失败时 _last_notify_result 包含错误信息"""
        sub = Subscriber(error_handling="log", timeout=0)

        async def failing_handler():
            raise ValueError("test error")

        sub.subscribe(failing_handler, event="test_event")

        await sub.notify("test_event")

        result = sub._last_notify_result
        assert result.has_errors is True
        assert result.error_count == 1
        assert len(result.errors) == 1
        name, exc = result.errors[0]
        assert "failing_handler" in name
        assert isinstance(exc, ValueError)

    @pytest.mark.asyncio
    async def test_no_subscribers_result(self):
        """无订阅者时 _last_notify_result 也被设置"""
        sub = Subscriber(error_handling="log", timeout=0)

        await sub.notify("nonexistent_event")

        result = sub._last_notify_result
        assert result is not None
        assert result.event == "nonexistent_event"
        assert result.has_errors is False
        assert result.success_count == 0


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.mark.asyncio
    async def test_notify_returns_list(self):
        """notify() 仍返回 List[Any]"""
        sub = Subscriber(error_handling="log", timeout=0)

        async def handler():
            return "result"

        sub.subscribe(handler, event="test")

        results = await sub.notify("test")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_critical_events_constant(self):
        """CRITICAL_EVENTS 包含关键事件"""
        assert "spider_closed" in CRITICAL_EVENTS
        assert "spider_error" in CRITICAL_EVENTS
        assert "spider_opened" in CRITICAL_EVENTS
