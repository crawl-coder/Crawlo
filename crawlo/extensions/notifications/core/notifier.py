# -*- coding: utf-8 -*-
"""
===================================
通知分发器
===================================

负责分发通知到对应的渠道处理器。
"""

from typing import Dict, Optional

from crawlo.logging import get_logger
from crawlo.extensions.notifications.core.models import NotificationMessage, NotificationResponse


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


def _resolve_notification_context():
    """优先从容器拿 NotificationContext，否则 fallback ctx.notifications。"""
    try:
        from crawlo.container import default_container
        from crawlo.core.application import NotificationContext
        if default_container.is_registered(NotificationContext):
            return default_container.resolve(NotificationContext)
    except Exception as e:
        logger.debug("Suppressed exception: %s", e)
    from crawlo.core.application import get_global_context
    return get_global_context().notifications


def get_notifier() -> NotificationDispatcher:
    """
    获取全局通知器实例（DI 容器优先 + DCL NotificationContext fallback）。
    """
    try:
        from crawlo.container import default_container
        if default_container.is_registered(NotificationDispatcher):
            return default_container.resolve(NotificationDispatcher)
    except Exception as e:
        logger.debug("Suppressed exception: %s", e)
    nctx = _resolve_notification_context()

    if nctx.notifier is None:
        with nctx.notifier_lock:
            if nctx.notifier is None:
                inst = NotificationDispatcher()

                from crawlo.extensions.notifications.channels import (
                    get_dingtalk_channel,
                    get_feishu_channel,
                    get_wecom_channel,
                    get_email_channel,
                    get_sms_channel,
                )

                inst.register_channel(get_dingtalk_channel())
                inst.register_channel(get_feishu_channel())
                inst.register_channel(get_wecom_channel())
                inst.register_channel(get_email_channel())
                inst.register_channel(get_sms_channel())
                nctx.notifier = inst
                try:
                    from crawlo.container import default_container as _c
                    _c.register_instance(NotificationDispatcher, inst)
                except Exception as e:
                    logger.debug("Suppressed exception: %s", e)

    return nctx.notifier


def reset_notifier() -> None:
    """重置全局通知器（通过 NotificationContext 属性操作）。"""
    nctx = _resolve_notification_context()
    nctx.notifier = None


