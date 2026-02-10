# -*- coding: utf-8 -*-
"""
===================================
通知渠道基类
===================================

定义通知渠道的抽象基类，各渠道必须继承此类。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType, ChannelResponse


class NotificationChannel(ABC):
    """
    通知渠道抽象基类
    
    负责：
    1. 发送通知到特定渠道
    2. 处理渠道特定的认证
    3. 格式化消息为渠道特定格式
    
    使用示例：
        class DingTalkChannel(NotificationChannel):
            @property
            def channel_type(self) -> ChannelType:
                return ChannelType.DINGTALK
            
            def send(self, message: NotificationMessage) -> NotificationResponse:
                # 发送逻辑
                pass
    """
    
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """
        渠道类型
        
        用于路由匹配和日志标识
        """
        pass
    
    @abstractmethod
    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        pass
    
    def format_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        格式化消息为渠道特定格式
        
        Args:
            message: 通知消息
            
        Returns:
            渠道特定的消息格式
        """
        # 默认实现：返回基本的消息格式
        return {
            'title': message.title,
            'content': message.content,
            'type': message.notification_type.value,
            'priority': message.priority,
            'timestamp': message.timestamp.isoformat(),
        }
    
    def verify_config(self) -> bool:
        """
        验证渠道配置是否正确
        
        Returns:
            配置是否有效
        """
        # 默认实现：假设配置有效
        return True
