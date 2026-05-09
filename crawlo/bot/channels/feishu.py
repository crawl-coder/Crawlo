# -*- coding: utf-8 -*-
"""
===================================
飞书通知渠道
===================================

处理向飞书机器人发送通知消息。
"""

import json
import hashlib
import time
from typing import Dict, Any, Optional
import requests

from crawlo.logging import get_logger
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.core.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class FeishuChannel(NotificationChannel):
    """
    飞书通知渠道
    
    支持向飞书群机器人发送通知消息。
    
    配置要求：
    - FEISHU_WEBHOOK: 飞书机器人 Webhook 地址
    - FEISHU_SECRET: 飞书机器人密钥（可选，用于验证）
    - FEISHU_AT_USERS: 需要@的用户ID列表（可选）
    - FEISHU_AT_MOBILE: 需要@的手机号列表（可选）
    - FEISHU_IS_AT_ALL: 是否@所有人（可选，默认False）
    """
    
    def __init__(self):
        # 初始化配置为 None，通过 set_config() 或配置加载器设置
        self.webhook_url = None
        self.secret = None
        self.at_users = []
        self.at_mobile = []
        self.is_at_all = False

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.FEISHU

    def set_config(self, webhook_url: str, secret: Optional[str] = None, 
                   at_users: Optional[list] = None, at_mobile: Optional[list] = None, 
                   is_at_all: bool = False):
        """
        设置飞书机器人配置
        
        Args:
            webhook_url: 飞书机器人 Webhook 地址
            secret: 飞书机器人密钥（可选）
            at_users: 需要@的用户ID列表（可选）
            at_mobile: 需要@的手机号列表（可选）
            is_at_all: 是否@所有人（可选，默认False）
        """
        self.webhook_url = webhook_url
        self.secret = secret
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
        
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hashlib.new('sha256', string_to_sign.encode('utf-8')).digest()
        return hmac_code.hex()

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送通知到飞书
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        if not self.webhook_url:
            error_msg = "飞书 Webhook URL 未配置"
            logger.error(f"[Feishu] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        try:
            # 构建飞书消息格式
            feishu_message = self._build_feishu_message(message)
            
            # 准备请求参数
            params = {'timestamp': '', 'sign': ''}
            
            # 如果设置了密钥，则生成签名
            if self.secret:
                timestamp = str(int(time.time()))
                signature = self._get_signature(timestamp)
                params = {'timestamp': timestamp, 'sign': signature}
            
            # 发送请求
            response = requests.post(
                url=self.webhook_url,
                json=feishu_message,
                params=params,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    logger.info(f"[Feishu] 通知发送成功: {message.title}")
                    return NotificationResponse.success_response(
                        message="发送成功",
                        sent_count=1
                    )
                else:
                    error_msg = f"飞书返回错误: {result.get('msg', '未知错误')}, 代码: {result.get('code', result.get('StatusCode'))}"
                    logger.error(f"[Feishu] {error_msg}")
                    return NotificationResponse.error_response(error_msg)
            else:
                error_msg = f"HTTP请求失败: {response.status_code}, 响应: {response.text}"
                logger.error(f"[Feishu] {error_msg}")
                return NotificationResponse.error_response(error_msg)
                
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.error(f"[Feishu] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)

    def _build_feishu_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        构建飞书消息格式
        
        Args:
            message: 通知消息
            
        Returns:
            飞书格式的消息
        """
        # 构建@内容
        at_part = ""
        if self.is_at_all:
            at_part = "<at user_id=\"all\">所有人</at>\n"
        elif self.at_users:
            for user_id in self.at_users:
                at_part += f"<at user_id=\"{user_id}\">{user_id}</at> "
        elif self.at_mobile:
            for mobile in self.at_mobile:
                at_part += f"<at mobile=\"{mobile}\">{mobile}</at> "

        # 根据通知类型选择消息格式
        type_emoji = {
            "alert": "🚨",
            "progress": "📊",
            "status": "🚀",
            "data": "📦",
        }.get(message.notification_type.value, "📢")
        
        type_label = message.notification_type.value.title()
        
        if message.notification_type.value in ("alert", "progress"):
            # 告警和进度类型使用富文本格式
            content = f"{message.title}\n\n{message.content}"
            if at_part:
                content = at_part + content
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": f"{message.title}",
                            "content": [
                                [
                                    {
                                        "tag": "text",
                                        "text": content
                                    }
                                ]
                            ]
                        }
                    }
                }
            }
        else:
            # 其他类型使用文本格式
            content = f"{message.title}\n\n{message.content}"
            if at_part:
                content = at_part + content
            return {
                "msg_type": "text",
                "content": {
                    "text": content
                }
            }


# 全局实例
_feishu_channel = None


def get_feishu_channel() -> FeishuChannel:
    """
    获取飞书通知渠道实例
    """
    global _feishu_channel
    if _feishu_channel is None:
        _feishu_channel = FeishuChannel()
    return _feishu_channel