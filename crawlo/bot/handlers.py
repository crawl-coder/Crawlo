# -*- coding: utf-8 -*-
"""
===================================
通知处理器
===================================

处理各种爬虫事件的通知需求。
"""

from typing import Dict, Any, Optional

from crawlo.logging import get_logger
from crawlo.bot.models import NotificationMessage, NotificationResponse, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.config_loader import apply_settings_config, ensure_config_loaded

logger = get_logger(__name__)


class CrawlerNotificationHandler:
    """
    爬虫通知处理器
    
    专门处理爬虫框架中的各类通知事件
    """
    
    def __init__(self):
        self.notifier = get_notifier()
    
    def send_status_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送状态通知
        
        Args:
            title: 通知标题
            content: 通知内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        # 确保配置已加载
        ensure_config_loaded()
        
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.STATUS,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self.notifier.send_notification(message)
    
    def send_alert_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "high",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送告警通知
        
        Args:
            title: 告警标题
            content: 告警内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        # 确保配置已加载
        ensure_config_loaded()
        
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.ALERT,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self.notifier.send_notification(message)
    
    def send_progress_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送进度通知
        
        Args:
            title: 进度标题
            content: 进度内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        # 确保配置已加载
        ensure_config_loaded()
        
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.PROGRESS,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self.notifier.send_notification(message)
    
    def send_data_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送数据推送通知
        
        Args:
            title: 数据标题
            content: 数据内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.DATA,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self.notifier.send_notification(message)


# 全局通知处理器实例
_notification_handler = None


def get_notification_handler() -> CrawlerNotificationHandler:
    """
    获取全局通知处理器实例
    """
    global _notification_handler
    
    if _notification_handler is None:
        _notification_handler = CrawlerNotificationHandler()
    
    return _notification_handler


def send_crawler_status(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫状态通知的便捷函数
    
    Args:
        title: 状态标题
        content: 状态内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_status_notification(title, content, channel)


def send_crawler_alert(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫告警通知的便捷函数
    
    Args:
        title: 告警标题
        content: 告警内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_alert_notification(title, content, channel)


def send_crawler_progress(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫进度通知的便捷函数
    
    Args:
        title: 进度标题
        content: 进度内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_progress_notification(title, content, channel)