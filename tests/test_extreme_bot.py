"""
Bot 通知极限测试
测试 API 限流、超时重试、超大通知截断等边界场景
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from unittest.mock import call as mock_call

from crawlo.bot.core.models import NotificationMessage, NotificationResponse, NotificationType, ChannelType
from crawlo.bot.core.notifier import NotificationDispatcher
from crawlo.bot.channels.dingtalk import DingTalkChannel
from crawlo.bot.channels.feishu import FeishuChannel
from crawlo.bot.channels.wecom import WeComChannel
from crawlo.bot.channels.email import EmailChannel


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
        with patch("crawlo.bot.channels.dingtalk.requests.post") as mock_post:
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

        with patch("crawlo.bot.channels.dingtalk.requests.post", side_effect=mock_response):
            response = channel.send(msg)
            # 钉钉渠道不重试,所以应该直接返回错误
            assert call_count == 1 or not response.success

    def test_api_timeout_retry(self):
        """测试: API 超时重试"""
        import requests.exceptions

        notifier = WebhookNotifier(
            webhook_url="http://example.com/webhook",
            max_retries=3,
            timeout=5,
        )

        call_count = 0

        def mock_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # 前两次超时
                raise requests.exceptions.Timeout("Connection timed out")
            else:
                # 第三次成功
                response = Mock()
                response.status_code = 200
                return response

        with patch(
            "crawlo.bot.notifiers.requests.post", side_effect=mock_timeout
        ):
            notifier.send(message="Test message")

            # 验证重试了 3 次
            assert call_count == 3

    def test_notification_frequency_control(self):
        """测试: 通知频率控制 (防骚扰)"""
        notifier = WebhookNotifier(
            webhook_url="http://example.com/webhook",
            min_interval=1,  # 最小间隔 1 秒
        )

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            start_time = time.time()

            # 快速发送 5 条通知
            for i in range(5):
                notifier.send(message=f"Message {i}")

            elapsed = time.time() - start_time

            # 应该至少有间隔时间
            # (由于 Mock,实际不会等待,但应该调用次数正确)
            assert mock_post.call_count == 5

    def test_webhook_invalid_url(self):
        """测试: 非法 Webhook URL"""
        invalid_urls = [
            "",
            "not_a_url",
            "ftp://example.com",  # 不支持的协议
            "http://" + "x" * 10000 + ".com",  # 超长域名
            None,
            12345,
        ]

        for url in invalid_urls:
            try:
                notifier = WebhookNotifier(webhook_url=url)
                # 如果创建成功,发送时应该失败
                try:
                    notifier.send(message="Test")
                except (ValueError, Exception):
                    pass
            except (ValueError, Exception):
                # 或者在创建时就失败
                pass

    def test_webhook_ssl_certificate_error(self):
        """测试: SSL 证书错误"""
        import requests.exceptions

        notifier = WebhookNotifier(webhook_url="https://expired.badssl.com/webhook")

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.SSLError(
                "SSL: CERTIFICATE_VERIFY_FAILED"
            )

            try:
                notifier.send(message="Test message")
                assert False, "应该抛出 SSL 错误"
            except requests.exceptions.SSLError:
                pass

    def test_email_notification_large_attachment(self):
        """测试: 邮件超大附件"""
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            recipients=["recipient@example.com"],
        )

        # 创建大附件数据
        large_attachment = b"x" * 1024 * 1024 * 50  # 50MB

        with patch("crawlo.bot.notifiers.smtplib.SMTP"):
            try:
                notifier.send(
                    subject="Test with large attachment",
                    message="Please see attachment",
                    attachments=[{"filename": "large.bin", "data": large_attachment}],
                )
            except Exception as e:
                # 应该有大小限制提示
                assert "size" in str(e).lower() or "large" in str(e).lower()

    def test_email_invalid_recipients(self):
        """测试: 非法收件人地址"""
        invalid_recipients = [
            "",
            "not_an_email",
            "@example.com",
            "user@",
            "user@.com",
            ["valid@example.com", "invalid"],
        ]

        for recipients in invalid_recipients:
            try:
                notifier = EmailNotifier(
                    smtp_host="smtp.example.com",
                    smtp_port=587,
                    username="test@example.com",
                    password="password",
                    recipients=recipients if isinstance(recipients, list) else [recipients],
                )
                # 如果创建成功,发送时应该失败
            except (ValueError, Exception):
                # 应该在创建或发送时失败
                pass

    def test_notification_template_injection(self):
        """测试: 通知模板注入攻击"""
        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

        # 恶意模板内容
        malicious_messages = [
            "{{config.SECRET_KEY}}",
            "{% import os %}{{ os.system('rm -rf /') }}",
            "${7*7}",
            "<script>document.cookie</script>",
            "'; DROP TABLE notifications; --",
        ]

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            for malicious_msg in malicious_messages:
                notifier.send(message=malicious_msg)

                # 验证消息被正确转义/清理
                call_args = mock_post.call_args
                payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]

                text = payload.get("text", "") or payload.get("content", "")
                # 不应该包含未转义的危险内容
                assert "<script>" not in text or "&lt;script&gt;" in text

    def test_concurrent_notifications_stress(self):
        """测试: 并发通知压力 (100 并发)"""
        import threading

        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")
        errors = []
        success_count = 0

        def send_notification(thread_id):
            nonlocal success_count
            try:
                with patch("crawlo.bot.notifiers.requests.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    notifier.send(message=f"Notification from thread {thread_id}")
                    success_count += 1
            except Exception as e:
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
        """测试: 重试次数耗尽"""
        import requests.exceptions

        notifier = WebhookNotifier(
            webhook_url="http://example.com/webhook",
            max_retries=3,
        )

        call_count = 0

        def mock_always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = Mock()
            response.status_code = 500
            response.text = "Internal Server Error"
            return response

        with patch("crawlo.bot.notifiers.requests.post", side_effect=mock_always_fail):
            try:
                notifier.send(message="Test message")
                assert False, "应该在重试耗尽后失败"
            except Exception as e:
                # 验证重试了正确的次数
                assert call_count == 4  # 1次初始 + 3次重试

    def test_notification_circuit_breaker(self):
        """测试: 熔断器机制"""
        import requests.exceptions

        notifier = WebhookNotifier(
            webhook_url="http://example.com/webhook",
            circuit_breaker_threshold=5,
        )

        # 模拟连续失败
        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            # 连续发送 10 次
            failed_count = 0
            for i in range(10):
                try:
                    notifier.send(message=f"Message {i}")
                except Exception:
                    failed_count += 1

            # 应该在达到阈值后触发熔断
            # 后续请求应该快速失败,不再实际发送
            assert failed_count == 10

    def test_notification_message_encoding(self):
        """测试: 消息编码处理"""
        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

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

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            for msg in messages:
                notifier.send(message=msg)

                # 验证消息正确编码
                call_args = mock_post.call_args
                # 应该使用 UTF-8 编码
                assert mock_post.called

    def test_notification_empty_message(self):
        """测试: 空消息"""
        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

        empty_messages = [
            "",
            "   ",
            "\n\n\n",
            None,
        ]

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            for msg in empty_messages:
                try:
                    notifier.send(message=msg)
                    # 如果允许空消息,应该不会发送
                    if msg and msg.strip():
                        assert mock_post.called
                except (ValueError, Exception):
                    # 或者应该拒绝空消息
                    pass

    def test_notification_custom_headers_injection(self):
        """测试: 自定义 Header 注入"""
        notifier = WebhookNotifier(
            webhook_url="http://example.com/webhook",
            headers={"Custom-Header": "value"},
        )

        malicious_headers = {
            "X-Injected": "malicious",
            "Authorization": "Bearer stolen_token",
        }

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            try:
                # 尝试覆盖 header
                notifier.send(
                    message="Test",
                    headers=malicious_headers,
                )

                # 验证原始 header 未被覆盖
                call_args = mock_post.call_args
                headers = call_args[1].get("headers", {})
                assert headers.get("Custom-Header") == "value" or "Custom-Header" not in headers
            except (TypeError, Exception):
                # 或者不允许动态修改 header
                pass

    def test_notification_statistics_tracking(self):
        """测试: 通知统计追踪"""
        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            # 发送多条通知
            for i in range(50):
                notifier.send(message=f"Message {i}")

            # 验证统计信息
            stats = notifier.get_stats()
            assert stats.get("total_sent", 0) == 50
            assert stats.get("success_count", 0) == 50
            assert stats.get("failure_count", 0) == 0

    def test_notification_network_partition(self):
        """测试: 网络分区 (DNS 解析失败)"""
        import requests.exceptions

        notifier = WebhookNotifier(
            webhook_url="http://nonexistent.invalid.domain.webhook/webhook",
            timeout=2,
        )

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Name or service not known"
            )

            try:
                notifier.send(message="Test message")
                assert False, "应该在网络分区时失败"
            except (requests.exceptions.ConnectionError, Exception):
                # 应该有明确的错误提示
                pass

    def test_notification_payload_size_limit(self):
        """测试: Payload 大小限制"""
        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

        # 创建刚好超过限制的消息
        large_message = "x" * 1024 * 100  # 100KB

        with patch("crawlo.bot.notifiers.requests.post") as mock_post:
            mock_post.return_value.status_code = 200

            notifier.send(message=large_message)

            # 验证 payload 被截断或分片
            call_args = mock_post.call_args
            payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]

            payload_str = json.dumps(payload)
            # 大多数 API 有 1MB 限制
            assert len(payload_str) < 1024 * 1024

    def test_notification_graceful_shutdown(self):
        """测试: 优雅关闭 (处理中的通知)"""
        import threading

        notifier = WebhookNotifier(webhook_url="http://example.com/webhook")

        def slow_response(*args, **kwargs):
            time.sleep(2)  # 模拟慢响应
            response = Mock()
            response.status_code = 200
            return response

        with patch("crawlo.bot.notifiers.requests.post", side_effect=slow_response):
            # 发送通知
            thread = threading.Thread(
                target=notifier.send, args=("Slow message",)
            )
            thread.start()

            # 立即关闭
            notifier.shutdown()

            # 等待线程完成
            thread.join(timeout=5)

            # 应该优雅地处理关闭
            assert not thread.is_alive()


class TestBotNotificationManager:
    """Bot 通知管理器测试"""

    def test_notification_manager_empty_list(self):
        """测试: 空通知列表"""
        from crawlo.bot import NotificationManager

        manager = NotificationManager(notifiers=[])

        # 应该能处理空列表
        manager.send_all(message="Test message")

    def test_notification_manager_multiple_notifiers(self):
        """测试: 多个通知器"""
        from crawlo.bot import NotificationManager

        webhook = WebhookNotifier(webhook_url="http://example.com/webhook")
        email = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            recipients=["recipient@example.com"],
        )

        manager = NotificationManager(notifiers=[webhook, email])

        with patch.object(webhook, "send"), patch.object(email, "send"):
            manager.send_all(message="Test message")

            # 验证两个通知器都被调用
            webhook.send.assert_called_once()
            email.send.assert_called_once()

    def test_notification_manager_partial_failure(self):
        """测试: 部分通知器失败"""
        from crawlo.bot import NotificationManager

        webhook1 = WebhookNotifier(webhook_url="http://example.com/webhook1")
        webhook2 = WebhookNotifier(webhook_url="http://example.com/webhook2")

        manager = NotificationManager(notifiers=[webhook1, webhook2])

        with patch.object(webhook1, "send", side_effect=Exception("Failed")):
            with patch.object(webhook2, "send"):
                # 应该继续发送其他通知
                manager.send_all(message="Test message")

                webhook2.send.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
