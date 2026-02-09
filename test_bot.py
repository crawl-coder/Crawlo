#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫通知系统测试脚本
"""

from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.handlers import get_notification_handler

def test_notification_system():
    """测试通知系统的基本功能"""
    print("=== 测试爬虫通知系统 ===")
    
    # 获取通知器实例
    notifier = get_notifier()
    print(f"已注册渠道数量: {len(notifier._channels)}")
    
    # 获取通知处理器
    handler = get_notification_handler()
    
    # 测试状态通知
    print("\n--- 测试状态通知 ---")
    status_response = handler.send_status_notification(
        title="爬虫启动通知",
        content="爬虫任务已成功启动，开始抓取数据...",
        channel=ChannelType.DINGTALK
    )
    print(f"状态通知结果: success={status_response.success}, message='{status_response.message}', error='{status_response.error}'")
    
    # 测试告警通知
    print("\n--- 测试告警通知 ---")
    alert_response = handler.send_alert_notification(
        title="爬虫异常告警",
        content="检测到爬虫出现异常，请求失败率超过阈值，请及时处理。",
        channel=ChannelType.DINGTALK,
        priority="high"
    )
    print(f"告警通知结果: success={status_response.success}, message='{status_response.message}', error='{status_response.error}'")
    
    # 测试进度通知
    print("\n--- 测试进度通知 ---")
    progress_response = handler.send_progress_notification(
        title="爬虫进度更新",
        content="数据抓取进度: 50%，已处理 5000 条记录，剩余约 2 小时完成。",
        channel=ChannelType.DINGTALK
    )
    print(f"进度通知结果: success={status_response.success}, message='{status_response.message}', error='{status_response.error}'")
    
    # 测试直接使用通知器发送
    print("\n--- 测试直接使用通知器 ---")
    message = NotificationMessage(
        channel=ChannelType.DINGTALK.value,
        notification_type=NotificationType.STATUS,
        title="测试通知",
        content="这是一条测试通知消息",
        priority="medium"
    )
    
    direct_response = notifier.send_notification(message)
    print(f"直接发送结果: success={direct_response.success}, message='{direct_response.message}', error='{direct_response.error}'")
    
    print("\n=== 通知系统测试完成 ===")


if __name__ == "__main__":
    test_notification_system()