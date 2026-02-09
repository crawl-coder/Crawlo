# -*- coding: utf-8 -*-
"""
===================================
钉钉通知渠道
===================================

处理向钉钉机器人发送通知消息。
"""

import hashlib
import hmac
import base64
import time
import logging
from typing import Dict, Any, Optional
import requests

from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = logging.getLogger(__name__)


class DingTalkChannel(NotificationChannel):
    """
    钉钉通知渠道
    
    支持向钉钉群机器人发送通知消息。
    
    配置要求：
    - DINGTALK_WEBHOOK: 钉钉机器人 Webhook 地址
    - DINGTALK_SECRET: 钉钉机器人密钥（可选，用于签名）
    """
    
    def __init__(self):
        # 从配置中获取钉钉相关信息
        # 在实际应用中，这里应该从框架配置中读取
        self.webhook_url = getattr(self, '_webhook_url', None)  # 可通过外部设置
        self.secret = getattr(self, '_secret', None)  # 可通过外部设置
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DINGTALK

    def set_config(self, webhook_url: str, secret: Optional[str] = None):
        """
        设置钉钉机器人配置
        
        Args:
            webhook_url: 钉钉机器人 Webhook 地址
            secret: 钉钉机器人密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret

    def _get_signed_url(self) -> str:
        """
        获取带签名的 URL（如果配置了密钥）
        
        Returns:
            带签名的 Webhook URL
        """
        if not self.secret:
            return self.webhook_url
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知到钉钉
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        if not self.webhook_url:
            error_msg = "钉钉 Webhook URL 未配置"
            logger.error(f"[DingTalk] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        try:
            # 构建钉钉消息格式
            dingtalk_message = self._build_dingtalk_message(message)
            
            # 获取带签名的 URL
            url = self._get_signed_url()
            
            # 发送请求
            response = requests.post(
                url=url,
                json=dingtalk_message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info(f"[DingTalk] 通知发送成功: {message.title}")
                    return NotificationResponse.success_response(
                        message="发送成功",
                        sent_count=1
                    )
                else:
                    error_msg = f"钉钉返回错误: {result.get('errmsg', '未知错误')}"
                    logger.error(f"[DingTalk] {error_msg}")
                    return NotificationResponse.error_response(error_msg)
            else:
                error_msg = f"HTTP请求失败: {response.status_code}"
                logger.error(f"[DingTalk] {error_msg}")
                return NotificationResponse.error_response(error_msg)
                
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.error(f"[DingTalk] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)

    def _build_dingtalk_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        构建钉钉消息格式
        
        Args:
            message: 通知消息
            
        Returns:
            钉钉格式的消息
        """
        # 根据通知类型选择消息格式
        if message.notification_type == "alert":
            # 告警类型使用 markdown 格式突出显示
            content = f"🚨 **{message.title}**\n\n{message.content}"
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"告警: {message.title}",
                    "text": content
                }
            }
        else:
            # 其他类型使用文本格式
            content = f"【{message.notification_type.value.upper()}】{message.title}\n\n{message.content}"
            return {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }


# 全局实例
_dingtalk_channel = None


def get_dingtalk_channel() -> DingTalkChannel:
    """
    获取钉钉通知渠道实例
    """
    global _dingtalk_channel
    if _dingtalk_channel is None:
        _dingtalk_channel = DingTalkChannel()
    return _dingtalk_channel