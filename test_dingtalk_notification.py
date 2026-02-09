#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
钉钉通知功能测试脚本
使用 settings.py 中的钉钉机器人配置进行测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert


def test_dingtalk_setup():
    """配置钉钉通知渠道"""
    print("🔧 配置钉钉通知渠道...")
    
    # 使用 settings.py 中的配置
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=f2b9ee74076d0525c392e9a4c2a021a0144d295ed7210f53fee402eb349e665f"
    secret = "SEC46ca0b774d564cedebc4761e23f158c20f6558ebed94b1bd18e2ba77259b0c40"
    
    # 获取钉钉渠道实例并配置
    dingtalk_channel = get_dingtalk_channel()
    dingtalk_channel.set_config(webhook_url=webhook_url, secret=secret)
    
    # 注册到通知器
    notifier = get_notifier()
    notifier.register_channel(dingtalk_channel)
    
    print("✅ 钉钉通知渠道配置完成")
    print(f"钉钉 Webhook URL: {webhook_url[:50]}...")
    print(f"钉钉 Secret: {secret[:20]}...")
    
    return dingtalk_channel


def test_dingtalk_notification():
    """测试钉钉通知发送功能"""
    print("\n=== 测试钉钉通知发送功能 ===")
    
    # 配置钉钉渠道
    dingtalk_channel = test_dingtalk_setup()
    
    print("\n--- 测试直接发送状态通知 ---")
    try:
        # 创建一个通知消息
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="Crawlo 钉钉通知测试",
            content="这是一条测试通知，验证钉钉机器人是否能够正常接收消息。",
            priority="medium"
        )
        
        # 通过渠道直接发送
        response = dingtalk_channel.send(message)
        print(f"直接发送响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"直接发送异常: {e}")
    
    print("\n--- 测试通过通知器发送告警通知 ---")
    try:
        # 使用通知器发送告警
        alert_message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.ALERT,
            title="【测试】爬虫告警通知",
            content="这是一条告警测试消息，验证告警通知功能。",
            priority="high"
        )
        
        notifier = get_notifier()
        response = notifier.send_notification(alert_message)
        print(f"通知器发送响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"通知器发送异常: {e}")
    
    print("\n--- 测试便捷函数发送 ---")
    try:
        # 测试便捷函数
        response = send_crawler_status(
            title="【便捷函数测试】Crawlo 测试通知",
            content="通过便捷函数发送的钉钉测试通知。",
            channel=ChannelType.DINGTALK
        )
        print(f"便捷函数发送响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"便捷函数发送异常: {e}")
    
    print("\n--- 测试告警便捷函数 ---")
    try:
        response = send_crawler_alert(
            title="【告警测试】Crawlo 告警通知",
            content="通过告警便捷函数发送的钉钉测试告警。",
            channel=ChannelType.DINGTALK
        )
        print(f"告警便捷函数发送响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"告警便捷函数发送异常: {e}")
    
    print("\n💡 提示:")
    print("- 如果通知成功发送，您应该能在钉钉群中看到消息")
    print("- 如果失败，请检查 Webhook URL 和密钥是否正确")
    print("- 确保钉钉机器人已添加到目标群聊中")
    
    print("\n=== 钉钉通知测试完成 ===")


if __name__ == "__main__":
    test_dingtalk_notification()