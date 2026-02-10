# -*- coding: utf-8 -*-
"""
===================================
企业微信通知渠道
===================================

处理向企业微信机器人发送通知消息。
"""

import hashlib
import hmac
import time
from typing import Dict, Any, Optional
import requests

from crawlo.logging import get_logger
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class WeComChannel(NotificationChannel):
    """
    企业微信通知渠道
    
    支持向企业微信群机器人发送通知消息。
    
    配置要求：
    - WECOM_WEBHOOK: 企业微信机器人 Webhook 地址
    - WECOM_SECRET: 企业微信机器人密钥（可选，用于验证）
    - WECOM_AGENT_ID: 企业微信应用 AgentId（可选）
    - WECOM_AT_USERS: 需要@的用户ID列表（可选）
    - WECOM_AT_MOBILE: 需要@的手机号列表（可选）
    - WECOM_IS_AT_ALL: 是否@所有人（可选，默认False）
    """
    
    def __init__(self):
        # 从配置中获取企业微信相关信息
        self.webhook_url = getattr(self, '_webhook_url', None)  # 可通过外部设置
        self.secret = getattr(self, '_secret', None)  # 可通过外部设置
        self.agent_id = getattr(self, '_agent_id', "")  # AgentId
        self.at_users = getattr(self, '_at_users', [])  # 需要@的用户ID列表
        self.at_mobile = getattr(self, '_at_mobile', [])  # 需要@的手机号列表
        self.is_at_all = getattr(self, '_is_at_all', False)  # 是否@所有人

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WECOM

    def set_config(self, webhook_url: str, secret: Optional[str] = None, agent_id: str = "",
                   at_users: Optional[list] = None, at_mobile: Optional[list] = None, 
                   is_at_all: bool = False):
        """
        设置企业微信机器人配置
        
        Args:
            webhook_url: 企业微信机器人 Webhook 地址
            secret: 企业微信机器人密钥（可选）
            agent_id: 企业微信应用 AgentId（可选）
            at_users: 需要@的用户ID列表（可选）
            at_mobile: 需要@的手机号列表（可选）
            is_at_all: 是否@所有人（可选，默认False）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.agent_id = agent_id
        self.at_users = at_users or []
        self.at_mobile = at_mobile or []
        self.is_at_all = is_at_all

    def _get_signature(self, timestamp: str) -> str:
        """
        生成签名（如果配置了密钥）
        
        Args:
            timestamp: 时间戳
            
        Returns:
            生成的签名
        """
        if not self.secret:
            return ""
        
        string_to_sign = f'{timestamp}\n{self.secret}'.encode('utf-8')
        signature = hmac.new(self.secret.encode('utf-8'), string_to_sign, digestmod=hashlib.sha256).digest()
        return signature.hex()

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知到企业微信
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        if not self.webhook_url:
            error_msg = "企业微信 Webhook URL 未配置"
            logger.error(f"[WeCom] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        try:
            # 构建企业微信消息格式
            wework_message = self._build_wework_message(message)
            
            # 发送请求
            response = requests.post(
                url=self.webhook_url,
                json=wework_message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info(f"[WeCom] 通知发送成功: {message.title}")
                    return NotificationResponse.success_response(
                        message="发送成功",
                        sent_count=1
                    )
                else:
                    error_msg = f"企业微信返回错误: {result.get('errmsg', '未知错误')}, 错误码: {result.get('errcode')}"
                    logger.error(f"[WeCom] {error_msg}")
                    return NotificationResponse.error_response(error_msg)
            else:
                error_msg = f"HTTP请求失败: {response.status_code}"
                logger.error(f"[WeCom] {error_msg}")
                return NotificationResponse.error_response(error_msg)
                
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.error(f"[WeCom] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)

    def _build_wework_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        构建企业微信消息格式
        
        Args:
            message: 通知消息
            
        Returns:
            企业微信格式的消息
        """
        # 构建@内容
        at_part = ""
        if self.is_at_all:
            at_part = "@all "
        elif self.at_users:
            for user in self.at_users:
                at_part += f"@{user} "
        elif self.at_mobile:
            for mobile in self.at_mobile:
                at_part += f"<@{mobile}> "

        # 根据通知类型选择消息格式
        type_emoji = {
            "alert": "🚨",
            "progress": "📊",
            "status": "🚀",
            "data": "📦",
        }.get(message.notification_type.value, "📢")
        
        type_label = message.notification_type.value.title()
        
        if message.notification_type.value in ("alert", "progress"):
            # 告警和进度类型使用 markdown 格式
            content = f"{at_part}**{message.title}**\n\n{message.content}"
            return {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
        else:
            # 其他类型使用文本格式
            content = f"{at_part}{message.title}\n\n{message.content}"
            return {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }


# 全局实例
_wecom_channel = None


def get_wecom_channel() -> WeComChannel:
    """
    获取企业微信通知渠道实例
    """
    global _wecom_channel
    if _wecom_channel is None:
        _wecom_channel = WeComChannel()
    return _wecom_channel