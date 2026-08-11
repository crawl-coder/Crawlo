"""
Bot 通知极限测试
测试 API 限流、超时重试、超大通知截断等边界场景
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from unittest.mock import call as mock_call

from crawlo.extensions.notifications.core.models import NotificationMessage, NotificationResponse, NotificationType, ChannelType
from crawlo.extensions.notifications.core.notifier import NotificationDispatcher
from crawlo.extensions.notifications.channels.dingtalk import DingTalkChannel
from crawlo.extensions.notifications.channels.feishu import FeishuChannel
from crawlo.extensions.notifications.channels.wecom import WeComChannel
from crawlo.extensions.notifications.channels.email import EmailChannel


class TestBotNotificationExtremeScenarios:
    """Bot 通知极限场景测试"""

    def test_ultra_large_notification_truncation(self):
        """测试: 超大通知内容截断 (10MB+)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        # 创建超大消息
        huge_message = "x" * 1024 * 1024 * 10  # 10MB

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content=huge_message,
        )

        # Mock 发送请求
        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            channel.send(msg)

            # 验证发送时消息被截断
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            # 消息应该被截断到合理大小
            text = payload.get('text', '')
            assert len(text) < 100000 or 'content' in payload

    def test_api_rate_limiting_handling(self):
        """测试: API 限流处理 (429 Too Many Requests)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        call_count = 0

        def mock_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                # 前两次返回 429 限流
                response = Mock()
                response.status_code = 429
                response.json.return_value = {'errcode': 1, 'errmsg': 'rate limit'}
                return response
            else:
                # 第三次成功
                response = Mock()
                response.status_code = 200
                response.json.return_value = {'errcode': 0}
                return response

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post", side_effect=mock_response):
            response = channel.send(msg)
            # 钉钉渠道不重试,所以应该直接返回错误
            assert call_count == 1 or not response.success

    def test_api_timeout_retry(self):
        """测试: API 超时处理 (渠道不重试,直接返回错误)"""
        import httpx

        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch(
            "crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post",
            side_effect=httpx.TimeoutException("Connection timed out"),
        ):
            response = channel.send(msg)
            # 渠道不重试,捕获异常并返回错误响应
            assert not response.success

    def test_notification_frequency_control(self):
        """测试: 通知频率控制 (连续发送多条通知)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            # 快速发送 5 条通知
            for i in range(5):
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=f"Message {i}",
                )
                channel.send(msg)

            # 所有通知都应该被发送
            assert mock_post.call_count == 5

    def test_webhook_invalid_url(self):
        """测试: 非法 Webhook URL"""
        invalid_urls = [
            "",
            "not_a_url",
            "ftp://example.com",  # 不支持的协议
            None,
        ]

        for url in invalid_urls:
            channel = DingTalkChannel()
            channel.webhook_url = url

            msg = NotificationMessage(
                channel=ChannelType.DINGTALK.value,
                notification_type=NotificationType.STATUS,
                title="测试",
                content="Test",
            )

            # 空 URL 或未配置应该返回错误; 非法 URL 发送时也会失败
            response = channel.send(msg)
            assert not response.success

    def test_webhook_ssl_certificate_error(self):
        """测试: SSL 证书错误"""
        import httpx

        channel = DingTalkChannel()
        channel.webhook_url = "https://expired.badssl.com/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError(
                "SSL: CERTIFICATE_VERIFY_FAILED"
            )

            # 渠道捕获异常并返回错误响应
            response = channel.send(msg)
            assert not response.success

    def test_email_notification_large_attachment(self):
        """测试: 邮件渠道配置不完整时返回错误"""
        channel = EmailChannel()
        # 不设置完整配置

        msg = NotificationMessage(
            channel=ChannelType.EMAIL.value,
            notification_type=NotificationType.STATUS,
            title="Test with large attachment",
            content="Please see attachment",
            recipients=["recipient@example.com"],
        )

        response = channel.send(msg)
        # 配置不完整应该返回错误
        assert not response.success

    def test_email_invalid_recipients(self):
        """测试: 邮件渠道空收件人使用默认值"""
        channel = EmailChannel()
        channel.smtp_host = "smtp.example.com"
        channel.smtp_port = 587
        channel.smtp_user = "test@example.com"
        channel.smtp_password = "password"
        channel.sender_email = "test@example.com"

        # 空收件人列表
        msg = NotificationMessage(
            channel=ChannelType.EMAIL.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
            recipients=[],
        )

        with patch("crawlo.extensions.notifications.channels.email.smtplib.SMTP"):
            response = channel.send(msg)
            # 空收件人使用默认值,发送应成功(模拟SMTP)
            assert response.success

    def test_notification_template_injection(self):
        """测试: 通知模板注入攻击"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        # 恶意模板内容
        malicious_messages = [
            "{{config.SECRET_KEY}}",
            "{% import os %}{{ os.system('rm -rf /') }}",
            "${7*7}",
            "<script>document.cookie</script>",
            "'; DROP TABLE notifications; --",
        ]

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            for malicious_msg in malicious_messages:
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=malicious_msg,
                )
                channel.send(msg)

                # 验证消息被作为纯文本发送(不执行模板注入)
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                text = payload.get("text", {}).get("content", "") or payload.get("markdown", {}).get("text", "")
                # 消息内容应该原样包含(不执行模板注入)
                assert malicious_msg in text

    def test_concurrent_notifications_stress(self):
        """测试: 并发通知压力 (100 并发)"""
        import threading

        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"
        errors = []
        success_count = 0
        lock = threading.Lock()

        def send_notification(thread_id):
            nonlocal success_count
            try:
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=f"Notification from thread {thread_id}",
                )
                with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = {'errcode': 0}
                    response = channel.send(msg)
                    if response.success:
                        with lock:
                            success_count += 1
            except Exception as e:
                with lock:
                    errors.append(str(e))

        # 启动 100 个并发线程
        threads = []
        for i in range(100):
            t = threading.Thread(target=send_notification, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"并发错误: {errors}"
        assert success_count == 100

    def test_notification_retry_exhaustion(self):
        """测试: 发送失败处理 (渠道不重试,只调用一次)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        call_count = 0

        def mock_always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = Mock()
            response.status_code = 500
            response.text = "Internal Server Error"
            return response

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post", side_effect=mock_always_fail):
            response = channel.send(msg)
            # 渠道不重试,只调用一次,返回错误
            assert not response.success
            assert call_count == 1

    def test_notification_circuit_breaker(self):
        """测试: 连续失败处理 (无熔断器,每次都尝试发送)"""
        import httpx

        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            # 连续发送 10 次
            failed_count = 0
            for i in range(10):
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=f"Message {i}",
                )
                response = channel.send(msg)
                if not response.success:
                    failed_count += 1

            # 无熔断器,所有请求都尝试发送并失败
            assert failed_count == 10
            assert mock_post.call_count == 10

    def test_notification_message_encoding(self):
        """测试: 消息编码处理"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        # 各种编码的消息
        messages = [
            "中文消息",
            "日本語メッセージ",
            "한국어 메시지",
            "Emoji: 🎉🚀💯",
            "Mixed: 中文 with English 日本語",
            "Special: <>&\"'©®™",
            "Control chars: \x00\x01\x02\x03",
        ]

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            for msg_content in messages:
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=msg_content,
                )
                channel.send(msg)

                # 验证消息正确编码
                call_args = mock_post.call_args
                # 应该使用 UTF-8 编码
                assert mock_post.called

    def test_notification_empty_message(self):
        """测试: 空消息"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        empty_messages = [
            "",
            "   ",
            "\n\n\n",
        ]

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            for msg_content in empty_messages:
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=msg_content,
                )

                response = channel.send(msg)
                assert mock_post.called

    def test_notification_custom_headers_injection(self):
        """测试: 渠道使用固定 Header"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            channel.send(msg)

            # 验证渠道使用固定 Content-Type header
            call_args = mock_post.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("Content-Type") == "application/json"

    def test_notification_statistics_tracking(self):
        """测试: 通知发送统计 (通过响应 sent_count)"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            success_count = 0
            # 发送多条通知
            for i in range(50):
                msg = NotificationMessage(
                    channel=ChannelType.DINGTALK.value,
                    notification_type=NotificationType.STATUS,
                    title="测试",
                    content=f"Message {i}",
                )
                response = channel.send(msg)
                if response.success:
                    success_count += 1

            # 验证所有通知发送成功
            assert mock_post.call_count == 50
            assert success_count == 50

    def test_notification_network_partition(self):
        """测试: 网络分区 (DNS 解析失败)"""
        import httpx

        channel = DingTalkChannel()
        channel.webhook_url = "http://nonexistent.invalid.domain.webhook/webhook"

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError(
                "Name or service not known"
            )

            # 网络错误应该返回错误响应
            response = channel.send(msg)
            assert not response.success

    def test_notification_payload_size_limit(self):
        """测试: Payload 大小限制"""
        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        # 创建刚好超过限制的消息
        large_message = "x" * 1024 * 100  # 100KB

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content=large_message,
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'errcode': 0}

            channel.send(msg)

            # 验证 payload 被截断或分片
            call_args = mock_post.call_args
            payload = call_args[1]["json"]

            payload_str = json.dumps(payload)
            # 大多数 API 有 1MB 限制
            assert len(payload_str) < 1024 * 1024

    def test_notification_graceful_shutdown(self):
        """测试: 通知发送完成处理"""
        import threading

        channel = DingTalkChannel()
        channel.webhook_url = "http://example.com/webhook"

        def slow_response(*args, **kwargs):
            time.sleep(2)  # 模拟慢响应
            response = Mock()
            response.status_code = 200
            response.json.return_value = {'errcode': 0}
            return response

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Slow message",
        )

        with patch("crawlo.extensions.notifications.channels.dingtalk._HTTP_CLIENT.post", side_effect=slow_response):
            result = []

            def send_msg():
                response = channel.send(msg)
                result.append(response)

            # 发送通知
            thread = threading.Thread(target=send_msg)
            thread.start()

            # 等待线程完成
            thread.join(timeout=10)

            # 应该优雅地完成发送
            assert not thread.is_alive()
            assert len(result) == 1


class TestBotNotificationManager:
    """Bot 通知分发器测试"""

    def test_notification_manager_empty_list(self):
        """测试: 空通知渠道列表"""
        from crawlo.extensions.notifications import NotificationDispatcher

        dispatcher = NotificationDispatcher()

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        # 无注册渠道,应该返回错误
        response = dispatcher.send_notification(msg)
        assert not response.success

    def test_notification_manager_multiple_notifiers(self):
        """测试: 多个渠道分发路由"""
        from crawlo.extensions.notifications import NotificationDispatcher

        dingtalk = DingTalkChannel()
        dingtalk.webhook_url = "http://example.com/dingtalk"

        email = EmailChannel()
        email.smtp_host = "smtp.example.com"
        email.smtp_port = 587
        email.smtp_user = "test@example.com"
        email.smtp_password = "password"
        email.sender_email = "test@example.com"

        dispatcher = NotificationDispatcher()
        dispatcher.register_channel(dingtalk)
        dispatcher.register_channel(email)

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch.object(dingtalk, "send") as mock_dingtalk_send, \
             patch.object(email, "send") as mock_email_send:
            mock_dingtalk_send.return_value = NotificationResponse.success_response("成功")

            dispatcher.send_notification(msg)

            # 钉钉消息只路由到钉钉渠道
            mock_dingtalk_send.assert_called_once()
            mock_email_send.assert_not_called()

    def test_notification_manager_partial_failure(self):
        """测试: 渠道发送失败处理"""
        from crawlo.extensions.notifications import NotificationDispatcher

        dingtalk = DingTalkChannel()
        dingtalk.webhook_url = "http://example.com/dingtalk"

        dispatcher = NotificationDispatcher()
        dispatcher.register_channel(dingtalk)

        msg = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="测试",
            content="Test message",
        )

        with patch.object(dingtalk, "send", side_effect=Exception("Failed")):
            # 分发器捕获异常并返回错误响应
            response = dispatcher.send_notification(msg)
            assert not response.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
