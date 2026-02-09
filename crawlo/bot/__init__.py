# -*- coding: utf-8 -*-
"""
===================================
爬虫通知系统
===================================

用于爬虫框架的状态通知、异常告警、任务进度更新和数据推送。
支持多种消息渠道（如钉钉、飞书、邮件等）。

模块结构：
- models.py: 统一的通知消息模型
- notifier.py: 通知分发器
- channels/: 消息渠道适配器
- handlers.py: 通知处理器

使用方式：
1. 配置通知渠道（各平台的 Token 等）
2. 注册通知事件
3. 在爬虫中触发通知
"""

from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType
from crawlo.bot.notifier import NotificationDispatcher, get_notifier

__all__ = [
    'NotificationMessage',
    'NotificationResponse',
    'ChannelType',
    'NotificationDispatcher',
    'get_notifier',
]