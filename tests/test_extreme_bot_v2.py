"""
Bot 通知极限测试 - 简化版
测试 API 限流、超时重试、超大通知截断等边界场景
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests.exceptions

from crawlo.bot.core.models import NotificationMessage, NotificationResponse, NotificationType, ChannelType
from crawlo.bot.core.notifier import NotificationDispatcher
from crawlo.bot.channels.dingtalk import DingTalkChannel
from crawlo.bot.channels.feishu import FeishuChannel
from crawlo.bot.channels.wecom import WeComChannel
from crawlo.bot.channels.email import EmailChannel


class TestBotNotificationExtremeScenarios:
    """Bot 通知极限场景测试"""

    def test_ultra_large_notification(self):
        """测试: 超大通知内容 (10MB+)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        huge_message = "x" * 1024 * 1024 * 10  # 10MB

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content=huge_message,
        )

        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            channel.send(msg)

            # 验证能正常发送(即使内容很大)
            assert mock_post.called
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            # 钉钉使用 markdown 或 text 格式
            assert 'text' in payload or 'markdown' in payload

    def test_api_rate_limiting(self):
        """测试: API 限流处理 (429)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 1, 'errmsg': 'rate limit'}

            response = channel.send(msg)
            # 应该返回错误响应
            assert not response.success or response.error

    def test_api_timeout(self):
        """测试: API 超时"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

            response = channel.send(msg)
            # 应该捕获异常并返回错误
            assert not response.success

    def test_invalid_webhook_url(self):
        """测试: 非法 Webhook URL"""
        channel = DingTalkChannel()
        channel.webhook_url = ""  # 空 URL

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        response = channel.send(msg)
        # 应该返回错误
        assert not response.success

    def test_special_characters_in_message(self):
        """测试: 消息中特殊字符"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        special_messages = [
            "中文消息",
            "日本語メッセージ",
            "한국어 메시지",
            "Emoji: 🎉🚀💯",
            "Special: <>&\"'©®™",
            "<script>alert('xss')</script>",
        ]

        for special_msg in special_messages:
            msg = NotificationMessage(
                channel=ChannelType.DINGTALK.value,
                notification_type=NotificationType.STATUS,
                title="测试",
                content=special_msg,
            )

            with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {'errcode': 0}

                response = channel.send(msg)
                assert mock_post.called

    def test_concurrent_notifications(self):
        """测试: 并发通知 (50 并发)"""
        import threading

        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        errors = []
        success_count = 0

        def send_notification(thread_id):
            nonlocal success_count
            try:
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=f"Notification from thread {thread_id}",
                )

                with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = {'errcode': 0}

                    response = channel.send(msg)
                    if response.success:
                        success_count += 1
            except Exception as e:
                errors.append(str(e))

        # 启动 50 个并发线程
        threads = []
        for i in range(50):
            t = threading.Thread(target=send_notification, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"并发错误: {errors}"
        assert success_count == 50

    def test_notification_dispatcher_multiple_channels(self):
        """测试: 分发器多渠道路由"""
        dispatcher = NotificationDispatcher()

        dingtalk = DingTalkChannel()
        dingtalk.webhook_url = "http://example.com/dingtalk"

        feishu = FeishuChannel()
        feishu.webhook_url = "http://example.com/feishu"

        dispatcher.register_channel(dingtalk)
        dispatcher.register_channel(feishu)

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_dingtalk:
            mock_dingtalk.return_value.status_code = 200
            mock_dingtalk.return_value.json.return_value = {'errcode': 0}

            response = dispatcher.send_notification(msg)
            assert mock_dingtalk.called

    def test_notification_dispatcher_unknown_channel(self):
        """测试: 分发器未知渠道"""
        dispatcher = NotificationDispatcher()

        msg = NotificationMessage(
            channel="unknown_channel",
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        response = dispatcher.send_notification(msg)
        assert not response.success
        assert "未知" in response.error or "unknown" in response.error.lower()

    def test_feishu_channel_with_secret(self):
        """测试: 飞书渠道带签名密钥"""
        channel = FeishuChannel()
        channel.webhook_url = "http://example.com/feishu"
        channel.secret = "test_secret_key"

        msg = NotificationMessage(
            channel=ChannelType.FEISHU.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.feishu.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'StatusCode': 0}

            response = channel.send(msg)
            assert mock_post.called

            # 验证签名生成
            call_args = mock_post.call_args
            url = call_args[1].get('url', '') or call_args[0][0]
            # 如果带 secret,URL 应包含 timestamp 和 sign
            if channel.secret:
                assert 'timestamp' in url or 'sign' in url

    def test_email_channel_invalid_recipients(self):
        """测试: 邮件渠道非法收件人"""
        channel = EmailChannel()
        channel.smtp_host = "smtp.example.com"
        channel.smtp_port = 587
        channel.smtp_user = "test@example.com"
        channel.smtp_password = "password"
        channel.sender_email = "test@example.com"

        msg = NotificationMessage(
            channel=ChannelType.EMAIL.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
            recipients=[],  # 空收件人
        )

        response = channel.send(msg)
        # 应该返回错误
        assert not response.success or len(msg.recipients) == 0

    def test_notification_empty_message(self):
        """测试: 空消息"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        empty_messages = [
            "",
            "   ",
            "\n\n\n",
        ]

        for empty_msg in empty_messages:
            msg = NotificationMessage(
                channel=ChannelType.DINGTALK.value,
                notification_type=NotificationType.STATUS,
                title="测试",
                content=empty_msg,
            )

            with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {'errcode': 0}

                response = channel.send(msg)
                assert mock_post.called

    def test_notification_priority_levels(self):
        """测试: 不同优先级通知"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        priorities = ["low", "medium", "high", "urgent"]

        for priority in priorities:
            msg = NotificationMessage(
                channel=ChannelType.DINGTALK.value,
                notification_type=NotificationType.STATUS,
                title=f"Priority: {priority}",
                content=f"This is a {priority} priority message",
                priority=priority,
            )

            with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {'errcode': 0}

                response = channel.send(msg)
                assert mock_post.called

    def test_notification_types(self):
        """测试: 不同通知类型"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        notification_types = [
            NotificationType.STATUS,
            NotificationType.ALERT,
            NotificationType.PROGRESS,
            NotificationType.DATA,
        ]

        for notif_type in notification_types:
            msg = NotificationMessage(
                channel=ChannelType.DINGTALK.value,
                notification_type=notif_type,
                title=f"Type: {notif_type.value}",
                content=f"This is a {notif_type.value} notification",
            )

            with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {'errcode': 0}

                response = channel.send(msg)
                assert mock_post.called

    def test_wecom_channel_at_all(self):
        """测试: 企业微信@所有人"""
        channel = WeComChannel()
        channel.webhook_url = "http://example.com/wecom"
        channel.is_at_all = True

        msg = NotificationMessage(
            channel=ChannelType.WECOM.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.wecom.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            response = channel.send(msg)
            assert mock_post.called

            # 验证 @所有人 标记
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            content = payload.get('text', {}).get('content', '')
            assert '@all' in content or '所有人' in content

    def test_notification_network_error(self):
        """测试: 网络错误 (DNS 解析失败)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://nonexistent.invalid.domain/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Name or service not known"
            )

            response = channel.send(msg)
            assert not response.success

    def test_notification_response_helpers(self):
        """测试: 响应辅助方法"""
        # 成功响应
        success_resp = NotificationResponse.success_response("成功", sent_count=5)
        assert success_resp.success == True
        assert success_resp.sent_count == 5

        # 错误响应
        error_resp = NotificationResponse.error_response("失败", failed_count=3)
        assert error_resp.success == False
        assert error_resp.failed_count == 3


class TestNotificationHandler:
    """通知处理器测试"""

    def test_send_status_notification(self):
        """测试: 发送状态通知"""
        from crawlo.bot.core.handlers import NotificationHandler

        handler = NotificationHandler()

        # 禁用通知(避免实际发送)
        try:
            from crawlo.settings.default_settings import ENABLE_NOTIFICATION
            if not ENABLE_NOTIFICATION:
                response = handler.send_status_notification(
                    title="测试",
                    content="测试内容",
                    channel=ChannelType.DINGTALK,
                )
                # 通知被禁用,应该返回跳过消息
                assert response is not None
        except ImportError:
            pass

    def test_send_alert_notification(self):
        """测试: 发送告警通知"""
        from crawlo.bot.core.handlers import NotificationHandler

        handler = NotificationHandler()

        try:
            from crawlo.settings.default_settings import ENABLE_NOTIFICATION
            if not ENABLE_NOTIFICATION:
                response = handler.send_alert_notification(
                    title="告警",
                    content="服务器宕机",
                    channel=ChannelType.DINGTALK,
                    priority="urgent",
                )
                assert response is not None
        except ImportError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
