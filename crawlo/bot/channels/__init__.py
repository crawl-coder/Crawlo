# -*- coding: utf-8 -*-
"""
===================================
通知渠道模块
===================================

包含各通知渠道的适配器实现。
"""

from crawlo.bot.channels.base import NotificationChannel

# 所有通知渠道类
ALL_CHANNELS = [
    # 在实际使用中可以添加具体的渠道类，如：
    # DingTalkChannel, FeishuChannel 等
]

__all__ = [
    'NotificationChannel',
    'ALL_CHANNELS',
]