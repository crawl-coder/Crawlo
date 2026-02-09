#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际通知发送测试脚本
"""

from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.channels.dingtalk import get_dingtalk_channel
from crawlo.bot.channels.feishu import get_feishu_channel
from crawlo.bot.channels.wecom import get_wecom_channel
from crawlo.bot.channels.email import get_email_channel
from crawlo.bot.handlers import get_notification_handler


def test_actual_notification():
    """测试实际通知发送功能"""
    print("=== 测试实际通知发送 ===")
    
    # 获取通知处理器
    handler = get_notification_handler()
    
    print("\n--- 测试状态通知 ---")
    try:
        # 这些测试会因缺少配置而失败，但会显示预期行为
        response = handler.send_status_notification(
            title="爬虫测试通知",
            content="这是一个测试通知，用于验证通知系统功能。",
            channel=ChannelType.DINGTALK
        )
        print(f"DingTalk 状态通知响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"DingTalk 状态通知异常: {e}")
    
    print("\n--- 测试告警通知 ---")
    try:
        response = handler.send_alert_notification(
            title="爬虫告警测试",
            content="这是一个告警测试，用于验证告警通知功能。",
            channel=ChannelType.FEISHU,
            priority="high"
        )
        print(f"Feishu 告警通知响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"Feishu 告警通知异常: {e}")
    
    print("\n--- 测试进度通知 ---")
    try:
        response = handler.send_progress_notification(
            title="进度更新测试",
            content="这是一个进度更新测试，用于验证进度通知功能。",
            channel=ChannelType.WECOM
        )
        print(f"WeCom 进度通知响应: success={response.success}, message='{response.message}', error='{response.error}'")
    except Exception as e:
        print(f"WeCom 进度通知异常: {e}")
    
    print("\n--- 测试便捷函数 ---")
    try:
        from crawlo.bot.handlers import send_crawler_status, send_crawler_alert
        status_resp = send_crawler_status(
            title="便捷函数测试",
            content="通过便捷函数发送的测试通知。",
            channel=ChannelType.DINGTALK
        )
        print(f"便捷状态通知响应: success={status_resp.success}")
    except Exception as e:
        print(f"便捷状态通知异常: {e}")
    
    print("\n--- 配置示例 ---")
    print("# 配置钉钉机器人示例:")
    print("dingtalk_channel = get_dingtalk_channel()")
    print("dingtalk_channel.set_config(webhook_url='YOUR_WEBHOOK_URL', secret='YOUR_SECRET')")
    
    print("\n# 配置飞书机器人示例:")
    print("feishu_channel = get_feishu_channel()")
    print("feishu_channel.set_config(webhook_url='YOUR_FEISHU_WEBHOOK_URL')")
    
    print("\n# 配置企业微信机器人示例:")
    print("wecom_channel = get_wecom_channel()")
    print("wecom_channel.set_config(webhook_url='YOUR_WECOM_WEBHOOK_URL')")
    
    print("\n# 配置邮件服务器示例:")
    print("email_channel = get_email_channel()")
    print("email_channel.set_config(smtp_host='smtp.example.com', smtp_port=587,")
    print("                    smtp_user='user@example.com', smtp_password='password',")
    print("                    sender_email='sender@example.com')")
    
    print("\n=== 实际通知发送测试完成 ===")
    print("注意：要实际发送通知，需要先配置相应的 Webhook 或 SMTP 信息")


if __name__ == "__main__":
    test_actual_notification()