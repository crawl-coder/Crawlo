# -*- coding: utf-8 -*-
"""
===================================
通知渠道模块
===================================

包含各通知渠道的适配器实现。
"""

from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.channels.dingtalk import DingTalkChannel, get_dingtalk_channel
from crawlo.bot.channels.feishu import FeishuChannel, get_feishu_channel
from crawlo.bot.channels.wecom import WeComChannel, get_wecom_channel
from crawlo.bot.channels.email import EmailChannel, get_email_channel
from crawlo.bot.channels.sms import SmsChannel, get_sms_channel

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