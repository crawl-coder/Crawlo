# -*- coding: utf-8 -*-
"""
===================================
爬虫通知系统
===================================

用于爬虫框架的状态通知、异常告警、任务进度更新和数据推送。
支持多种消息渠道（钉钉、飞书、企业微信、邮件、短信）。

模块结构：
- models.py: 统一的通知消息模型
- notifier.py: 通知分发器
- channels/: 消息渠道适配器
- handlers.py: 通知处理器
- config_loader.py: 配置加载器

使用方式：
1. 在 settings.py 中配置通知渠道参数
2. 在爬虫中通过 handlers 发送通知
"""

from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType, NotificationType
from crawlo.bot.notifier import NotificationDispatcher, get_notifier
from crawlo.bot.handlers import (
    CrawlerNotificationHandler,
    get_notification_handler,
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress,
)

__all__ = [
    # 模型
    'NotificationMessage',
    'NotificationResponse',
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
]