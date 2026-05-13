# -*- coding: utf-8 -*-
"""
===================================
Bot 模块单元测试
===================================

测试通知系统的核心功能、渠道、模板和工具模块。
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 导入被测试模块
from crawlo.bot.core.models import (
    NotificationMessage,
    NotificationResponse,
    ChannelResponse,
    ChannelType,
    NotificationType,
)
from crawlo.bot.core.notifier import NotificationDispatcher, get_notifier, reset_notifier
from crawlo.bot.core.handlers import (
    CrawlerNotificationHandler,
    get_notification_handler,
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress,
)
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.utils.deduplicator import MessageDeduplicator, get_deduplicator, reset_deduplicator
from crawlo.bot.templates.manager import MessageTemplateManager, get_template_manager, render_message


class TestNotificationModels(unittest.TestCase):
    """测试通知消息模型"""

    def test_notification_message_creation(self):
        """测试 NotificationMessage 创建"""
        msg = NotificationMessage(
            channel="dingtalk",
            notification_type=NotificationType.STATUS,
            title="测试标题",
            content="测试内容",
            priority="high",
            recipients=["user1@example.com"],
        )

        self.assertEqual(msg.channel, "dingtalk")
        self.assertEqual(msg.notification_type, NotificationType.STATUS)
        self.assertEqual(msg.title, "测试标题")
        self.assertEqual(msg.content, "测试内容")
        self.assertEqual(msg.priority, "high")
        self.assertEqual(msg.recipients, ["user1@example.com"])
        self.assertIsInstance(msg.timestamp, datetime)

    def test_notification_message_defaults(self):
        """测试 NotificationMessage 默认值"""
        msg = NotificationMessage(
            channel="email",
            notification_type=NotificationType.ALERT,
            title="告警",
            content="内容",
        )

        self.assertEqual(msg.priority, "medium")
        self.assertEqual(msg.recipients, [])
        self.assertEqual(msg.metadata, {})
        self.assertEqual(msg.raw_data, {})

    def test_notification_response_success(self):
        """测试成功响应创建"""
        response = NotificationResponse.success_response("发送成功", sent_count=5)

        self.assertTrue(response.success)
        self.assertEqual(response.message, "发送成功")
        self.assertEqual(response.sent_count, 5)
        self.assertEqual(response.failed_count, 0)
        self.assertEqual(response.error, "")

    def test_notification_response_error(self):
        """测试错误响应创建"""
        response = NotificationResponse.error_response("发送失败", failed_count=2)

        self.assertFalse(response.success)
        self.assertEqual(response.error, "发送失败")
        self.assertEqual(response.failed_count, 2)
        self.assertEqual(response.sent_count, 0)

    def test_channel_response_success(self):
        """测试渠道响应创建"""
        response = ChannelResponse.success({"status": "ok"})

        self.assertTrue(response.success)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, {"status": "ok"})

    def test_channel_response_error(self):
        """测试渠道错误响应创建"""
        response = ChannelResponse.error("错误信息", status_code=500)

        self.assertFalse(response.success)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.body, {"error": "错误信息"})

    def test_enum_values(self):
        """测试枚举值"""
        self.assertEqual(ChannelType.DINGTALK.value, "dingtalk")
        self.assertEqual(ChannelType.FEISHU.value, "feishu")
        self.assertEqual(ChannelType.WECOM.value, "wecom")
        self.assertEqual(ChannelType.EMAIL.value, "email")
        self.assertEqual(ChannelType.SMS.value, "sms")

        self.assertEqual(NotificationType.STATUS.value, "status")
        self.assertEqual(NotificationType.ALERT.value, "alert")
        self.assertEqual(NotificationType.PROGRESS.value, "progress")


class TestNotificationDispatcher(unittest.TestCase):
    """测试通知分发器"""

    def setUp(self):
        """测试前重置通知器"""
        reset_notifier()

    def test_register_channel(self):
        """测试注册渠道"""
        dispatcher = NotificationDispatcher()
        mock_channel = Mock()
        mock_channel.channel_type = ChannelType.DINGTALK

        dispatcher.register_channel(mock_channel)
        self.assertEqual(dispatcher.get_channel("dingtalk"), mock_channel)

    def test_unregister_channel(self):
        """测试注销渠道"""
        dispatcher = NotificationDispatcher()
        mock_channel = Mock()
        mock_channel.channel_type = ChannelType.DINGTALK

        dispatcher.register_channel(mock_channel)
        result = dispatcher.unregister_channel("dingtalk")

        self.assertTrue(result)
        self.assertIsNone(dispatcher.get_channel("dingtalk"))

    def test_unregister_nonexistent_channel(self):
        """测试注销不存在的渠道"""
        dispatcher = NotificationDispatcher()
        result = dispatcher.unregister_channel("nonexistent")

        self.assertFalse(result)

    def test_send_notification_success(self):
        """测试发送通知成功"""
        dispatcher = NotificationDispatcher()
        mock_channel = Mock()
        mock_channel.channel_type = ChannelType.DINGTALK
        mock_channel.send.return_value = NotificationResponse.success_response("成功")

        dispatcher.register_channel(mock_channel)

        message = NotificationMessage(
            channel="dingtalk",
            notification_type=NotificationType.STATUS,
            title="测试",
            content="内容",
        )

        response = dispatcher.send_notification(message)

        self.assertTrue(response.success)
        mock_channel.send.assert_called_once_with(message)

    def test_send_notification_unknown_channel(self):
        """测试发送通知到未知渠道"""
        dispatcher = NotificationDispatcher()

        message = NotificationMessage(
            channel="unknown",
            notification_type=NotificationType.STATUS,
            title="测试",
            content="内容",
        )

        response = dispatcher.send_notification(message)

        self.assertFalse(response.success)
        self.assertIn("未知的通知渠道", response.error)

    def test_send_notification_exception(self):
        """测试发送通知异常"""
        dispatcher = NotificationDispatcher()
        mock_channel = Mock()
        mock_channel.channel_type = ChannelType.DINGTALK
        mock_channel.send.side_effect = Exception("网络错误")

        dispatcher.register_channel(mock_channel)

        message = NotificationMessage(
            channel="dingtalk",
            notification_type=NotificationType.STATUS,
            title="测试",
            content="内容",
        )

        response = dispatcher.send_notification(message)

        self.assertFalse(response.success)
        self.assertIn("通知发送失败", response.error)

    def test_get_notifier_singleton(self):
        """测试 get_notifier 单例模式"""
        notifier1 = get_notifier()
        notifier2 = get_notifier()

        self.assertIs(notifier1, notifier2)

    def test_get_notifier_thread_safety(self):
        """测试 get_notifier 线程安全"""
        notifiers = []
        lock = threading.Lock()

        def get_notifier_in_thread():
            notifier = get_notifier()
            with lock:
                notifiers.append(notifier)

        # 创建 20 个线程同时获取通知器
        threads = [threading.Thread(target=get_notifier_in_thread) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有线程应该获得同一个实例
        self.assertEqual(len(set(id(n) for n in notifiers)), 1)


class TestMessageDeduplicator(unittest.TestCase):
    """测试消息去重器"""

    def setUp(self):
        """测试前重置去重器"""
        reset_deduplicator()

    def test_no_duplicate_for_new_message(self):
        """测试新消息不是重复消息"""
        deduplicator = MessageDeduplicator(time_window=60)

        is_dup = deduplicator.is_duplicate("标题", "内容", "dingtalk")

        self.assertFalse(is_dup)

    def test_duplicate_within_time_window(self):
        """测试时间窗口内的重复消息"""
        deduplicator = MessageDeduplicator(time_window=60)

        # 第一次发送
        is_dup1 = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertFalse(is_dup1)

        # 第二次发送（时间窗口内）
        is_dup2 = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertTrue(is_dup2)

    def test_not_duplicate_after_time_window(self):
        """测试超过时间窗口后不是重复消息"""
        deduplicator = MessageDeduplicator(time_window=1)  # 1秒时间窗口

        # 第一次发送
        is_dup1 = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertFalse(is_dup1)

        # 等待超过时间窗口
        time.sleep(1.1)

        # 第二次发送（超过时间窗口）
        is_dup2 = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertFalse(is_dup2)

    def test_different_channels_not_duplicate(self):
        """测试不同渠道不是重复消息"""
        deduplicator = MessageDeduplicator(time_window=60)

        is_dup1 = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertFalse(is_dup1)

        is_dup2 = deduplicator.is_duplicate("标题", "内容", "feishu")
        self.assertFalse(is_dup2)

    def test_different_content_not_duplicate(self):
        """测试不同内容不是重复消息"""
        deduplicator = MessageDeduplicator(time_window=60)

        is_dup1 = deduplicator.is_duplicate("标题", "内容1", "dingtalk")
        self.assertFalse(is_dup1)

        is_dup2 = deduplicator.is_duplicate("标题", "内容2", "dingtalk")
        self.assertFalse(is_dup2)

    def test_max_size_emergency_cleanup(self):
        """测试容量限制和紧急清理"""
        deduplicator = MessageDeduplicator(time_window=300, max_size=10)

        # 添加 10 条消息（达到容量限制）
        for i in range(10):
            deduplicator.is_duplicate(f"标题{i}", f"内容{i}", "dingtalk")

        self.assertEqual(len(deduplicator._seen_messages), 10)

        # 添加第 11 条消息（触发紧急清理）
        is_dup = deduplicator.is_duplicate("标题新", "内容新", "dingtalk")
        self.assertFalse(is_dup)

        # 验证清理后记录数少于 max_size
        self.assertLess(len(deduplicator._seen_messages), 10)

    def test_clear_history(self):
        """测试清空历史记录"""
        deduplicator = MessageDeduplicator(time_window=60)

        deduplicator.is_duplicate("标题", "内容", "dingtalk")
        deduplicator.clear_history()

        is_dup = deduplicator.is_duplicate("标题", "内容", "dingtalk")
        self.assertFalse(is_dup)

    def test_thread_safety(self):
        """测试去重器线程安全"""
        deduplicator = MessageDeduplicator(time_window=60, max_size=1000)
        results = []
        lock = threading.Lock()

        def check_duplicate(index):
            is_dup = deduplicator.is_duplicate(f"标题{index}", f"内容{index}", "dingtalk")
            with lock:
                results.append(is_dup)

        # 创建 50 个线程同时检查重复
        threads = [threading.Thread(target=check_duplicate, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有消息都应该是第一次出现（不重复）
        self.assertEqual(sum(1 for r in results if r), 0)


class TestMessageTemplateManager(unittest.TestCase):
    """测试消息模板管理器"""

    def setUp(self):
        """测试前重置模板管理器"""
        global _template_manager
        from crawlo.bot.templates.manager import _template_manager
        _template_manager = None

    def test_get_default_template(self):
        """测试获取默认模板"""
        manager = MessageTemplateManager()

        template = manager.get_template('task_startup')
        self.assertIsNotNone(template)
        self.assertIn('title', template)
        self.assertIn('content', template)

    def test_render_template(self):
        """测试渲染模板"""
        manager = MessageTemplateManager()

        rendered = manager.render_template(
            'task_startup',
            task_name='测试任务',
            target='https://example.com',
            estimated_time='10分钟'
        )

        self.assertIsNotNone(rendered)
        self.assertIn('测试任务', rendered['title'])
        self.assertIn('https://example.com', rendered['content'])

    def test_render_template_missing_variables(self):
        """测试渲染模板缺少变量"""
        manager = MessageTemplateManager()

        rendered = manager.render_template('task_startup')

        # 缺少变量时，应保持原样
        self.assertIsNotNone(rendered)
        self.assertIn('{task_name}', rendered['title'])

    def test_add_custom_template(self):
        """测试添加自定义模板"""
        manager = MessageTemplateManager()

        manager.add_template(
            'custom_template',
            '自定义标题: {name}',
            '自定义内容: {message}'
        )

        template = manager.get_template('custom_template')
        self.assertIsNotNone(template)
        self.assertEqual(template['title'], '自定义标题: {name}')

    def test_remove_custom_template(self):
        """测试删除自定义模板"""
        manager = MessageTemplateManager()

        manager.add_template('temp_template', '标题', '内容')
        result = manager.remove_template('temp_template')

        self.assertTrue(result)
        self.assertIsNone(manager.get_template('temp_template'))

    def test_cannot_remove_default_template(self):
        """测试不能删除默认模板"""
        manager = MessageTemplateManager()

        result = manager.remove_template('task_startup')

        self.assertFalse(result)
        self.assertIsNotNone(manager.get_template('task_startup'))

    def test_list_templates(self):
        """测试列出所有模板"""
        manager = MessageTemplateManager()

        templates = manager.list_templates()

        self.assertGreater(len(templates), 0)
        self.assertIn('task_startup', templates)

    def test_get_template_parameters(self):
        """测试获取模板参数列表"""
        manager = MessageTemplateManager()

        params = manager.get_template_parameters('task_startup')

        self.assertIsNotNone(params)
        self.assertIn('task_name', params)
        self.assertIn('target', params)

    def test_render_message_convenience_function(self):
        """测试便捷函数 render_message"""
        rendered = render_message(
            'task_completion',
            task_name='完成任务',
            success_count=100,
            duration='5分钟'
        )

        self.assertIsNotNone(rendered)
        self.assertIn('完成任务', rendered['title'])
        self.assertIn('100', rendered['content'])


class TestNotificationHandler(unittest.TestCase):
    """测试通知处理器"""

    @patch('crawlo.project.get_settings')
    def setUp(self, mock_get_settings):
        """测试前设置模拟配置"""
        # 模拟 settings 返回
        mock_settings = Mock()
        mock_settings.get = Mock(side_effect=lambda key, default=None: {
            'NOTIFICATION_ENABLED': True,
            'NOTIFICATION_CHANNELS': ['dingtalk'],
        }.get(key, default))
        mock_get_settings.return_value = mock_settings

        # 重置全局处理器
        import crawlo.bot.core.handlers as handlers_module
        handlers_module._notification_handler = None

    @patch('crawlo.project.get_settings')
    def test_handler_disabled_notification(self, mock_get_settings):
        """测试禁用通知系统"""
        mock_settings = Mock()
        mock_settings.get = Mock(side_effect=lambda key, default=None: {
            'NOTIFICATION_ENABLED': False,
        }.get(key, default))
        mock_get_settings.return_value = mock_settings

        # 重新创建处理器
        import crawlo.bot.core.handlers as handlers_module
        handlers_module._notification_handler = None

        handler = get_notification_handler()
        response = handler.send_status_notification("测试", "内容")

        self.assertIn("禁用", response.message)

    @patch('crawlo.project.get_settings')
    @patch('crawlo.bot.core.handlers.ensure_config_loaded')
    @patch('crawlo.bot.core.handlers.get_notifier')
    def test_send_status_notification(self, mock_get_notifier, mock_ensure_config, mock_get_settings):
        """测试发送状态通知"""
        mock_notifier = Mock()
        mock_notifier.send_notification.return_value = NotificationResponse.success_response("成功")
        mock_get_notifier.return_value = mock_notifier

        handler = get_notification_handler()
        response = handler.send_status_notification("状态标题", "状态内容")

        self.assertTrue(response.success)

    @patch('crawlo.project.get_settings')
    @patch('crawlo.bot.core.handlers.ensure_config_loaded')
    @patch('crawlo.bot.core.handlers.get_notifier')
    def test_send_alert_notification(self, mock_get_notifier, mock_ensure_config, mock_get_settings):
        """测试发送告警通知"""
        mock_notifier = Mock()
        mock_notifier.send_notification.return_value = NotificationResponse.success_response("成功")
        mock_get_notifier.return_value = mock_notifier

        handler = get_notification_handler()
        response = handler.send_alert_notification("告警标题", "告警内容")

        self.assertTrue(response.success)


class TestChannelBase(unittest.TestCase):
    """测试渠道基类"""

    def test_notification_channel_is_abstract(self):
        """测试 NotificationChannel 是抽象类"""
        with self.assertRaises(TypeError):
            NotificationChannel()

    def test_concrete_channel_implementation(self):
        """测试具体渠道实现"""
        class TestChannel(NotificationChannel):
            @property
            def channel_type(self):
                return ChannelType.EMAIL

            def send(self, message):
                return NotificationResponse.success_response("成功")

        channel = TestChannel()
        self.assertEqual(channel.channel_type, ChannelType.EMAIL)

        message = NotificationMessage(
            channel="email",
            notification_type=NotificationType.STATUS,
            title="测试",
            content="内容",
        )

        response = channel.send(message)
        self.assertTrue(response.success)

    def test_format_message(self):
        """测试消息格式化"""
        class TestChannel(NotificationChannel):
            @property
            def channel_type(self):
                return ChannelType.EMAIL

            def send(self, message):
                return NotificationResponse.success_response("成功")

        channel = TestChannel()
        message = NotificationMessage(
            channel="email",
            notification_type=NotificationType.STATUS,
            title="测试标题",
            content="测试内容",
        )

        formatted = channel.format_message(message)

        self.assertEqual(formatted['title'], '测试标题')
        self.assertEqual(formatted['content'], '测试内容')
        self.assertEqual(formatted['type'], 'status')


if __name__ == '__main__':
    unittest.main()
