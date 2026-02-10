# -*- coding: utf-8 -*-
"""
===================================
通知分发器
===================================

负责分发通知到对应的渠道处理器。
"""

from typing import Dict, List, Optional, Type, Callable

from crawlo.logging import get_logger
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class NotificationDispatcher:
    """
    通知分发器
    
    职责：
    1. 注册和管理通知渠道处理器
    2. 分发通知到对应渠道
    3. 处理发送失败和重试
    4. 管理通知优先级
    
    使用示例：
        notifier = NotificationDispatcher()
        notifier.register_channel(DingTalkChannel())
        notifier.register_channel(FeishuChannel())
        
        response = notifier.send_notification(notification_message)
    """
    
    def __init__(self):
        self._channels: Dict[str, 'NotificationChannel'] = {}
    
    def register_channel(self, channel: 'NotificationChannel') -> None:
        """
        注册通知渠道
        
        Args:
            channel: 通知渠道实例
        """
        name = channel.channel_type.value
        
        if name in self._channels:
            logger.warning(f"[Notifier] 渠道 '{name}' 已存在，将被覆盖")
        
        self._channels[name] = channel
        logger.debug(f"[Notifier] 注册渠道: {name}")
    
    def unregister_channel(self, channel_type: str) -> bool:
        """
        注销通知渠道
        
        Args:
            channel_type: 渠道类型
            
        Returns:
            是否成功注销
        """
        if channel_type not in self._channels:
            return False
        
        del self._channels[channel_type]
        logger.debug(f"[Notifier] 注销渠道: {channel_type}")
        return True
    
    def get_channel(self, channel_type: str) -> Optional['NotificationChannel']:
        """
        获取渠道处理器
        
        Args:
            channel_type: 渠道类型
            
        Returns:
            渠道实例，或 None
        """
        return self._channels.get(channel_type)
    
    def send_notification(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知到指定渠道
        
        Args:
            message: 通知消息对象
            
        Returns:
            通知响应对象
        """
        logger.info(f"[Notifier] 发送通知: type={message.notification_type}, channel={message.channel}, title={message.title}")
        
        # 获取渠道处理器
        channel = self.get_channel(message.channel)
        
        if channel is None:
            error_msg = f"未知的通知渠道: {message.channel}"
            logger.error(error_msg)
            return NotificationResponse.error_response(error_msg)
        
        # 发送通知
        try:
            response = channel.send(message)
            logger.info(f"[Notifier] 通知发送完成: {message.title}, success={response.success}")
            return response
        except Exception as e:
            error_msg = f"通知发送失败: {str(e)[:100]}"
            logger.error(f"[Notifier] 通知发送失败: {message.title}, error={e}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)


# 全局通知器实例
_notifier = None


def get_notifier() -> NotificationDispatcher:
    """
    获取全局通知器实例
    
    使用单例模式，首次调用时自动初始化并注册所有渠道。
    """
    global _notifier
    
    if _notifier is None:
        # 创建通知器
        _notifier = NotificationDispatcher()
        
        # 自动注册所有渠道（使用单例函数获取实例）
        from crawlo.bot.channels import (
            get_dingtalk_channel,
            get_feishu_channel,
            get_wecom_channel,
            get_email_channel,
            get_sms_channel,
        )
        
        _notifier.register_channel(get_dingtalk_channel())
        _notifier.register_channel(get_feishu_channel())
        _notifier.register_channel(get_wecom_channel())
        _notifier.register_channel(get_email_channel())
        _notifier.register_channel(get_sms_channel())
        
        logger.info(f"[Notifier] 初始化完成，已注册 {len(_notifier._channels)} 个渠道")
    
    return _notifier


def reset_notifier() -> None:
    """重置全局通知器（主要用于测试）"""
    global _notifier
    _notifier = None


class NotificationChannel:
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
    def channel_type(self) -> ChannelType:
        """
        渠道类型
        
        用于路由匹配和日志标识
        """
        raise NotImplementedError
    
    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        raise NotImplementedError