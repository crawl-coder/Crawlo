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
from typing import Dict, Any, Optional
import requests

from crawlo.logging import get_logger
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.core.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class DingTalkChannel(NotificationChannel):
    """
    钉钉通知渠道
    
    支持向钉钉群机器人发送通知消息。
    
    配置要求：
    - DINGTALK_WEBHOOK: 钉钉机器人 Webhook 地址
    - DINGTALK_SECRET: 钉钉机器人密钥（可选，用于签名）
    - DINGTALK_KEYWORDS: 钉钉机器人关键词（可选，用于通过关键词验证）
    - DINGTALK_AT_MOBILES: 需要@的手机号列表（可选）
    - DINGTALK_AT_USERIDS: 需要@的用户ID列表（可选）
    - DINGTALK_IS_AT_ALL: 是否@所有人（可选，默认False）
    """
    
    def __init__(self):
        # 初始化配置为 None，通过 set_config() 或配置加载器设置
        self.webhook_url = None
        self.secret = None
        self.keywords = []
        self.at_mobiles = []
        self.at_userids = []
        self.is_at_all = False

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DINGTALK

    def set_config(self, webhook_url: str, secret: Optional[str] = None, keywords: Optional[list] = None, 
                   at_mobiles: Optional[list] = None, at_userids: Optional[list] = None, 
                   is_at_all: bool = False):
        """
        设置钉钉机器人配置
        
        Args:
            webhook_url: 钉钉机器人 Webhook 地址
            secret: 钉钉机器人密钥（可选）
            keywords: 钉钉机器人关键词列表（可选，用于通过关键词验证）
            at_mobiles: 需要@的手机号列表（可选）
            at_userids: 需要@的用户ID列表（可选）
            is_at_all: 是否@所有人（可选，默认False）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.keywords = keywords or []
        self.at_mobiles = at_mobiles or []
        self.at_userids = at_userids or []
        self.is_at_all = is_at_all

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
        string_to_sign = f"{timestamp}\n{self.secret}"
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
                    return NotificationResponse.success_response(
                        message="发送成功",
                        sent_count=1
                    )
                else:
                    error_msg = f"钉钉返回错误: {result.get('errmsg', '未知错误')}, 错误码: {result.get('errcode')}"
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
        # 确定关键词 - 如果设置了关键词，则使用第一个关键词作为前缀
        keyword_prefix = ""
        if self.keywords:
            keyword_prefix = f"{self.keywords[0]} "  # 使用第一个关键词
        
        # 根据通知类型选择消息格式
        type_emoji = {
            "alert": "🚨",
            "progress": "📊",
            "status": "🚀",
            "data": "📦",
        }.get(message.notification_type.value, "📢")
        
        type_label = message.notification_type.value.title()
        
        if message.notification_type.value == "alert":
            # 告警类型使用 markdown 格式突出显示
            content = f"{keyword_prefix}**{message.title}**\n\n{message.content}"
            msg_dict = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"{message.title}",
                    "text": content
                }
            }
        else:
            # 其他类型使用文本格式
            content = f"{keyword_prefix}{message.title}\n\n{message.content}"
            msg_dict = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
        
        # 添加@信息
        if self.at_mobiles or self.at_userids or self.is_at_all:
            msg_dict["at"] = {
                "atMobiles": self.at_mobiles,
                "atUserIds": self.at_userids,
                "isAtAll": self.is_at_all
            }
        
        return msg_dict


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