# -*- coding: utf-8 -*-
"""
===================================
Bot 核心模块
===================================

包含通知系统的核心功能：
- 数据模型
- 通知分发器
- 通知处理器
"""

from crawlo.bot.core.models import (
    NotificationMessage,
    NotificationResponse,
    ChannelResponse,
    ChannelType,
    NotificationType,
)
from crawlo.bot.core.notifier import NotificationDispatcher, get_notifier
from crawlo.bot.core.handlers import (
    CrawlerNotificationHandler,
    get_notification_handler,
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress,
    send_template_notification,
    list_notification_templates,
    add_custom_notification_template,
)

__all__ = [
    # 模型
    'NotificationMessage',
    'NotificationResponse',
    'ChannelResponse',
    'ChannelType',
    'NotificationType',
    # 通知器
    'NotificationDispatcher',
    'get_notifier',
    # 处理器
    'CrawlerNotificationHandler',
    'get_notification_handler',
    'send_crawler_status',
    'send_crawler_alert',
    'send_crawler_progress',
    'send_template_notification',
    'list_notification_templates',
    'add_custom_notification_template',
]
