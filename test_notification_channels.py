#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通知渠道测试脚本
"""

from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel
from crawlo.bot.channels.email import get_email_channel
from crawlo.bot.handlers import get_notification_handler


def test_notification_channels():
    """测试通知渠道的基本功能"""
    print("=== 测试通知渠道 ===")
    
    # 获取通知器实例
    notifier = get_notifier()
    print(f"已注册渠道数量: {len(notifier._channels)}")
    
    # 测试钉钉渠道
    print("\n--- 测试钉钉渠道 ---")
    dingtalk_channel = get_dingtalk_channel()
    print(f"钉钉渠道类型: {dingtalk_channel.channel_type}")
    
    # 测试飞书渠道
    print("\n--- 测试飞书渠道 ---")
    feishu_channel = get_feishu_channel()
    print(f"飞书渠道类型: {feishu_channel.channel_type}")
    
    # 测试企业微信渠道
    print("\n--- 测试企业微信渠道 ---")
    wecom_channel = get_wecom_channel()
    print(f"企业微信渠道类型: {wecom_channel.channel_type}")
    
    # 测试邮件渠道
    print("\n--- 测试邮件渠道 ---")
    email_channel = get_email_channel()
    print(f"邮件渠道类型: {email_channel.channel_type}")
    
    # 测试通知处理器
    print("\n--- 测试通知处理器 ---")
    handler = get_notification_handler()
    
    # 测试不同类型的模拟通知（不会实际发送，因为没有配置 webhook）
    print("\n--- 测试通知类型 ---")
    
    # 模拟发送不同类型的通知
    test_types = [
        (NotificationType.STATUS, "爬虫状态通知"),
        (NotificationType.ALERT, "爬虫异常告警"),
        (NotificationType.PROGRESS, "爬虫进度更新"),
        (NotificationType.DATA, "数据推送通知")
    ]
    
    for notification_type, description in test_types:
        print(f"  {description}: {notification_type.value}")
    
    print("\n=== 通知渠道测试完成 ===")
    print("注意：实际发送通知需要配置相应的 Webhook 或 SMTP 信息")


if __name__ == "__main__":
    test_notification_channels()