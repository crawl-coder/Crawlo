# -*- coding: utf-8 -*-
"""
===================================
通知渠道模块
===================================

包含各通知渠道的适配器实现。
"""

from crawlo.extensions.notifications.channels.base import NotificationChannel
from crawlo.extensions.notifications.channels.dingtalk import DingTalkChannel, get_dingtalk_channel
from crawlo.extensions.notifications.channels.feishu import FeishuChannel, get_feishu_channel
from crawlo.extensions.notifications.channels.wecom import WeComChannel, get_wecom_channel
from crawlo.extensions.notifications.channels.email import EmailChannel, get_email_channel
from crawlo.extensions.notifications.channels.sms import SmsChannel, get_sms_channel

# 所有通知渠道类
ALL_CHANNELS = [
    DingTalkChannel,
    FeishuChannel,
    WeComChannel,
    EmailChannel,
    SmsChannel,
]

__all__ = [
    'NotificationChannel',
    'DingTalkChannel',
    'FeishuChannel', 
    'WeComChannel',
    'EmailChannel',
    'SmsChannel',
    'get_dingtalk_channel',
    'get_feishu_channel',
    'get_wecom_channel',
    'get_email_channel',
    'get_sms_channel',
    'ALL_CHANNELS',
]