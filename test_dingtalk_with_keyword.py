#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
钉钉通知功能测试脚本（带关键词）
使用 settings.py 中的钉钉机器人配置进行测试，并尝试匹配关键词
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert


def test_dingtalk_with_keyword():
    """配置带关键词的钉钉通知渠道并测试"""
    print("🔧 配置带关键词的钉钉通知渠道...")
    
    # 使用 settings.py 中的配置
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=f2b9ee74076d0525c392e9a4c2a021a0144d295ed7210f53fee402eb349e665f"
    secret = "SEC46ca0b774d564cedebc4761e23f158c20f6558ebed94b1bd18e2ba77259b0c40"
    
    # 假设关键词是 "爬虫" 或其他可能的关键词，我们先尝试一些常见的关键词
    # 根据钉钉机器人的常见设置，可能需要包含特定关键词才能发送成功
    possible_keywords = ["爬虫", "通知", "crawler", "status", "alert", "crawlo", "test"]
    
    # 获取钉钉渠道实例并配置
    dingtalk_channel = get_dingtalk_channel()
    
    # 先不设置关键词测试
    dingtalk_channel.set_config(webhook_url=webhook_url, secret=secret)
    
    # 注册到通知器
    notifier = get_notifier()
    notifier.unregister_channel('dingtalk')  # 先移除之前的实例
    notifier.register_channel(dingtalk_channel)
    
    print("✅ 钉钉通知渠道配置完成")
    print(f"钉钉 Webhook URL: {webhook_url[:50]}...")
    
    print("\n--- 测试不带关键词的通知 ---")
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
        print(f"不带关键词发送响应: success={response.success}, error='{response.error}'")
    except Exception as e:
        print(f"不带关键词发送异常: {e}")
    
    # 现在尝试设置关键词
    print("\n--- 尝试设置关键词 crawlo ---")
    dingtalk_channel.set_config(webhook_url=webhook_url, secret=secret, keywords=["crawlo"])
    
    print("\n--- 测试带关键词 crawlo 的通知 ---")
    try:
        # 创建一个通知消息
        message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.STATUS,
            title="Crawlo 钉钉通知测试",
            content="这是一条带关键词的测试通知，验证钉钉机器人是否能够正常接收消息。",
            priority="medium"
        )
        
        # 通过渠道直接发送
        response = dingtalk_channel.send(message)
        print(f"带关键词 crawlo 发送响应: success={response.success}, error='{response.error}'")
    except Exception as e:
        print(f"带关键词 crawlo 发送异常: {e}")
    
    # 尝试另一个可能的关键词
    print("\n--- 尝试设置关键词 爬虫 ---")
    dingtalk_channel.set_config(webhook_url=webhook_url, secret=secret, keywords=["爬虫"])
    
    print("\n--- 测试带关键词 爬虫 的通知 ---")
    try:
        # 创建一个告警消息
        alert_message = NotificationMessage(
            channel=ChannelType.DINGTALK.value,
            notification_type=NotificationType.ALERT,
            title="【测试】爬虫告警通知",
            content="这是一条带关键词的告警测试消息，验证告警通知功能。",
            priority="high"
        )
        
        # 通过渠道直接发送
        response = dingtalk_channel.send(alert_message)
        print(f"带关键词 爬虫 告警发送响应: success={response.success}, error='{response.error}'")
    except Exception as e:
        print(f"带关键词 爬虫 告警发送异常: {e}")
    
    # 尝试使用通知处理器
    print("\n--- 测试使用通知处理器发送（带关键词）---")
    try:
        dingtalk_channel.set_config(webhook_url=webhook_url, secret=secret, keywords=["test"])
        notifier.unregister_channel('dingtalk')  # 重新注册
        notifier.register_channel(dingtalk_channel)
        
        response = send_crawler_status(
            title="【处理器测试】Crawlo 测试通知",
            content="通过通知处理器发送的带关键词测试通知。",
            channel=ChannelType.DINGTALK
        )
        print(f"通知处理器发送响应: success={response.success}, error='{response.error}'")
    except Exception as e:
        print(f"通知处理器发送异常: {e}")
    
    print("\n💡 提示:")
    print("- 钉钉机器人可能设置了关键词验证")
    print("- 需要在发送的消息中包含指定的关键词")
    print("- 常见关键词：'爬虫', '通知', 'crawler', 'status', 'alert', 'crawlo'")
    print("- 如果仍有问题，可能需要联系群管理员确认具体关键词")
    
    print("\n=== 钉钉通知测试完成 ===")


if __name__ == "__main__":
    test_dingtalk_with_keyword()