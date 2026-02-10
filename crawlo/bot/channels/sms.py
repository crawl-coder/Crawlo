# -*- coding: utf-8 -*-
"""
===================================
短信通知渠道
===================================

处理发送短信通知消息。
"""

from typing import Dict, Any, Optional

from crawlo.logging import get_logger
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class SmsChannel(NotificationChannel):
    """
    短信通知渠道
    
    支持发送短信通知消息。
    注意：实际使用时需要集成具体的短信服务商API（如阿里云、腾讯云等）
    """
    
    def __init__(self):
        # 从配置中获取短信相关信息
        # 在实际应用中，这里应该从框架配置中读取
        self.provider = getattr(self, '_provider', 'aliyun')  # 默认使用阿里云
        self.access_key_id = getattr(self, '_access_key_id', None)
        self.access_key_secret = getattr(self, '_access_key_secret', None)
        self.sign_name = getattr(self, '_sign_name', None)  # 短信签名
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.SMS

    def set_config(self, provider: str, access_key_id: str, 
                   access_key_secret: str, sign_name: str):
        """
        设置短信服务配置
        
        Args:
            provider: 短信服务商 ('aliyun', 'tencent', etc.)
            access_key_id: 访问密钥ID
            access_key_secret: 访问密钥Secret
            sign_name: 短信签名
        """
        self.provider = provider
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.sign_name = sign_name

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送短信通知
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        if not all([self.access_key_id, self.access_key_secret, self.sign_name]):
            error_msg = "短信服务配置不完整"
            logger.error(f"[SMS] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        if not message.recipients:
            error_msg = "未指定短信接收号码"
            logger.error(f"[SMS] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        try:
            # 在实际应用中，这里会调用具体的短信服务商API
            # 以下是模拟实现
            phone_numbers = message.recipients
            content = f"[{message.notification_type.value.upper()}] {message.title}: {message.content}"
            
            # 这里应该是实际的短信发送逻辑
            # 例如对于阿里云短信服务，会调用其SDK
            logger.info(f"[SMS] 准备发送短信到: {phone_numbers}")
            logger.info(f"[SMS] 短信内容: {content}")
            
            # 模拟发送成功（实际应用中需要替换为真实的API调用）
            success_count = len(phone_numbers)
            logger.info(f"[SMS] 短信发送成功: {success_count} 条")
            
            return NotificationResponse.success_response(
                message="短信发送成功",
                sent_count=success_count
            )
                
        except Exception as e:
            error_msg = f"短信发送异常: {str(e)}"
            logger.error(f"[SMS] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)


# 全局实例
_sms_channel = None


def get_sms_channel() -> SmsChannel:
    """
    获取短信通知渠道实例
    """
    global _sms_channel
    if _sms_channel is None:
        _sms_channel = SmsChannel()
    return _sms_channel