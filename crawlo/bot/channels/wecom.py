# -*- coding: utf-8 -*-
"""
===================================
企业微信通知渠道
===================================

处理向企业微信机器人发送通知消息。
"""

import time
import logging
from typing import Dict, Any, Optional
import requests

from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = logging.getLogger(__name__)


class WeComChannel(NotificationChannel):
    """
    企业微信通知渠道
    
    支持向企业微信群机器人发送通知消息。
    
    配置要求：
    - WECOM_WEBHOOK: 企业微信机器人 Webhook 地址
    """
    
    def __init__(self):
        # 从配置中获取企业微信相关信息
        # 在实际应用中，这里应该从框架配置中读取
        self.webhook_url = getattr(self, '_webhook_url', None)  # 可通过外部设置
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WECOM

    def set_config(self, webhook_url: str):
        """
        设置企业微信机器人配置
        
        Args:
            webhook_url: 企业微信机器人 Webhook 地址
        """
        self.webhook_url = webhook_url

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
            wecom_message = self._build_wecom_message(message)
            
            # 发送请求
            response = requests.post(
                url=self.webhook_url,
                json=wecom_message,
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
                error_msg = f"HTTP请求失败: {response.status_code}, {response.text}"
                logger.error(f"[WeCom] {error_msg}")
                return NotificationResponse.error_response(error_msg)
                
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            logger.error(f"[WeCom] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)

    def _build_wecom_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        构建企业微信消息格式
        
        Args:
            message: 通知消息
            
        Returns:
            企业微信格式的消息
        """
        # 根据通知类型选择消息格式
        if message.notification_type.value == "alert":
            # 告警类型使用 markdown 格式突出显示
            content = f"🚨【告警】{message.title}\n\n{message.content}"
            return {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
        elif message.notification_type.value in ["progress", "status"]:
            # 状态和进度类型使用图文格式
            return {
                "msgtype": "news",
                "news": {
                    "articles": [
                        {
                            "title": f"📊 {message.title}",
                            "description": message.content,
                            "url": "https://example.com",  # 可以指向相关的详情页
                            "picurl": "https://example.com/pic.jpg"  # 可选的图片URL
                        }
                    ]
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
_wecom_channel = None


def get_wecom_channel() -> WeComChannel:
    """
    获取企业微信通知渠道实例
    """
    global _wecom_channel
    if _wecom_channel is None:
        _wecom_channel = WeComChannel()
    return _wecom_channel