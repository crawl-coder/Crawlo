#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo 爬虫通知系统使用示例
===================================

演示如何在 Crawlo 项目中集成和使用通知系统。
"""

from crawlo.bot.models import NotificationMessage, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationResponse
from crawlo.bot.handlers import (
    get_notification_handler, 
    send_crawler_status, 
    send_crawler_alert, 
    send_crawler_progress
)


class MockDingTalkChannel(NotificationChannel):
    """
    模拟钉钉通知渠道
    
    用于演示如何实现一个通知渠道。
    """
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DINGTALK

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """发送通知到钉钉"""
        print(f"📤 发送到钉钉: [{message.notification_type}] {message.title}")
        print(f"   内容: {message.content}")
        print(f"   优先级: {message.priority}")
        
        # 模拟发送成功
        return NotificationResponse.success_response(
            message="发送成功", 
            sent_count=len(message.recipients) if message.recipients else 1
        )


def main():
    """
    主函数：演示通知系统的使用
    """
    print("🚀 Crawlo 爬虫通知系统使用示例")
    print("=" * 50)
    
    # 获取通知器
    notifier = get_notifier()
    
    # 注册模拟的钉钉渠道
    notifier.register_channel(MockDingTalkChannel())
    print(f"✅ 已注册通知渠道: dingtalk")
    print(f"📋 当前已注册渠道数量: {len(notifier._channels)}")
    
    print("\n" + "=" * 50)
    print("🔍 测试各种通知类型:")
    
    # 测试状态通知
    print("\n📝 测试状态通知:")
    handler = get_notification_handler()
    status_resp = handler.send_status_notification(
        title="爬虫启动",
        content="数据采集任务已启动，预计运行2小时",
        channel=ChannelType.DINGTALK
    )
    print(f"   发送结果: {status_resp.message}")
    
    # 测试告警通知
    print("\n🚨 测试告警通知:")
    alert_resp = handler.send_alert_notification(
        title="网络异常",
        content="检测到网络连接不稳定，请求失败率上升至15%",
        channel=ChannelType.DINGTALK,
        priority="high"
    )
    print(f"   发送结果: {alert_resp.message}")
    
    # 测试进度通知
    print("\n📊 测试进度通知:")
    progress_resp = handler.send_progress_notification(
        title="采集进度",
        content="已完成5000/10000条数据采集，进度50%",
        channel=ChannelType.DINGTALK
    )
    print(f"   发送结果: {progress_resp.message}")
    
    # 测试便捷函数
    print("\n⚡ 测试便捷函数:")
    easy_resp = send_crawler_status(
        "便捷通知",
        "通过便捷函数发送的通知",
        ChannelType.DINGTALK
    )
    print(f"   发送结果: {easy_resp.message}")
    
    print("\n" + "=" * 50)
    print("🎯 通知系统特性:")
    print("   • 统一的通知消息模型 (NotificationMessage)")
    print("   • 统一的通知响应模型 (NotificationResponse)")
    print("   • 多渠道支持 (钉钉、飞书、企业微信等)")
    print("   • 通知类型分类 (状态、告警、进度、数据)")
    print("   • 优先级管理")
    print("   • 便捷的API调用")
    
    print("\n✨ 爬虫通知系统已成功集成到 Crawlo!")


if __name__ == "__main__":
    main()