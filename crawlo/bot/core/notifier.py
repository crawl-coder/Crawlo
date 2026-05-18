# -*- coding: utf-8 -*-
"""
===================================
通知分发器
===================================

负责分发通知到对应的渠道处理器。
"""

from typing import Dict, List, Optional, Type, Callable
import threading

from crawlo.logging import get_logger
from crawlo.bot.core.models import NotificationMessage, NotificationResponse, ChannelType


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
        发送通知到指定渠道（同步）
        
        Args:
            message: 通知消息对象
            
        Returns:
            通知响应对象
        """
        channel = self.get_channel(message.channel)
        
        if channel is None:
            error_msg = f"未知的通知渠道: {message.channel}"
            logger.error(error_msg)
            return NotificationResponse.error_response(error_msg)
        
        try:
            response = channel.send(message)
            return response
        except Exception as e:
            error_msg = f"通知发送失败: {str(e)[:100]}"
            return NotificationResponse.error_response(error_msg)

    async def async_send_notification(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知到指定渠道（异步，在 executor 中运行同步 send）
        
        避免在 asyncio 事件循环中阻塞。适用于爬虫框架的异步上下文。
        
        Args:
            message: 通知消息对象
            
        Returns:
            通知响应对象
        """
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.send_notification, message)


def get_notifier() -> NotificationDispatcher:
    """
    获取全局通知器实例（存储于 ApplicationContext，DCL 线程安全）
    """
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    
    if ctx.notifier is None:
        with ctx.notifier_lock:
            if ctx.notifier is None:
                ctx.notifier = NotificationDispatcher()
                
                from crawlo.bot.channels import (
                    get_dingtalk_channel,
                    get_feishu_channel,
                    get_wecom_channel,
                    get_email_channel,
                    get_sms_channel,
                )
                
                ctx.notifier.register_channel(get_dingtalk_channel())
                ctx.notifier.register_channel(get_feishu_channel())
                ctx.notifier.register_channel(get_wecom_channel())
                ctx.notifier.register_channel(get_email_channel())
                ctx.notifier.register_channel(get_sms_channel())
    
    return ctx.notifier


def reset_notifier() -> None:
    """重置全局通知器（主要用于测试）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    ctx.notifier = None


