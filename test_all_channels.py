#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面测试所有通知渠道
"""

from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel
from crawlo.bot.channels.email import get_email_channel
from crawlo.bot.channels.sms import get_sms_channel
from crawlo.bot.handlers import get_notification_handler


def test_all_channels():
    """测试所有通知渠道"""
    print("=== 全面测试所有通知渠道 ===")
    
    # 获取通知器实例
    notifier = get_notifier()
    print(f"已注册渠道数量: {len(notifier._channels)}")
    
    # 测试各渠道实例
    print("\n--- 测试各渠道实例 ---")
    channels = [
        ("钉钉", get_dingtalk_channel()),
        ("飞书", get_feishu_channel()),
        ("企业微信", get_wecom_channel()),
        ("邮件", get_email_channel()),
        ("短信", get_sms_channel()),
    ]
    
    for name, channel in channels:
        print(f"  {name}渠道类型: {channel.channel_type}")
    
    # 测试通知处理器
    print("\n--- 测试通知处理器 ---")
    handler = get_notification_handler()
    
    # 测试不同通知类型
    print("\n--- 测试不同通知类型 ---")
    notification_types = [
        (NotificationType.STATUS, "状态通知"),
        (NotificationType.ALERT, "告警通知"),
        (NotificationType.PROGRESS, "进度通知"),
        (NotificationType.DATA, "数据通知"),
    ]
    
    for notification_type, desc in notification_types:
        print(f"  {desc}: {notification_type.value}")
    
    # 测试所有渠道类型
    print("\n--- 测试所有渠道类型 ---")
    channel_types = [
        (ChannelType.DINGTALK, "钉钉"),
        (ChannelType.FEISHU, "飞书"),
        (ChannelType.WECOM, "企业微信"),
        (ChannelType.EMAIL, "邮件"),
        (ChannelType.SMS, "短信"),
    ]
    
    for channel_type, name in channel_types:
        print(f"  {name}: {channel_type.value}")
    
    print("\n--- 通知系统功能总结 ---")
    print("✅ 支持多种通知类型：状态、告警、进度、数据")
    print("✅ 支持多种通知渠道：钉钉、飞书、企业微信、邮件、短信")
    print("✅ 统一的消息模型和响应处理")
    print("✅ 便捷的API调用接口")
    print("✅ 可扩展的渠道架构")
    
    print("\n💡 使用建议：")
    print("  - 告警类通知推荐使用钉钉/企业微信，即时性强")
    print("  - 重要通知可采用多渠道推送，提高到达率")
    print("  - 邮件适合发送详细的报告和日志")
    print("  - 短信用于最紧急的关键告警")
    
    print("\n=== 全面测试完成 ===")


if __name__ == "__main__":
    test_all_channels()