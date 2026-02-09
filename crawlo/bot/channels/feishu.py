# -*- coding: utf-8 -*-
"""
===================================
飞书通知渠道
===================================

处理向飞书机器人发送通知消息。
"""

import json
import time
import logging
from typing import Dict, Any, Optional
import requests

from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = logging.getLogger(__name__)


class FeishuChannel(NotificationChannel):
    """
    飞书通知渠道
    
    支持向飞书群机器人发送通知消息。
    
    配置要求：
    - FEISHU_WEBHOOK: 飞书机器人 Webhook 地址
    """
    
    def __init__(self):
        # 从配置中获取飞书相关信息
        # 在实际应用中，这里应该从框架配置中读取
        self.webhook_url = getattr(self, '_webhook_url', None)  # 可通过外部设置
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.FEISHU

    def set_config(self, webhook_url: str):
        """
        设置飞书机器人配置
        
        Args:
            webhook_url: 飞书机器人 Webhook 地址
        """
        self.webhook_url = webhook_url

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
            
            # 发送请求
            response = requests.post(
                url=self.webhook_url,
                json=feishu_message,
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
                    error_msg = f"飞书返回错误: {result.get('msg', result.get('message', '未知错误'))}"
                    logger.error(f"[Feishu] {error_msg}")
                    return NotificationResponse.error_response(error_msg)
            else:
                error_msg = f"HTTP请求失败: {response.status_code}, {response.text}"
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
        # 根据通知类型选择消息格式
        if message.notification_type.value == "alert":
            # 告警类型使用富文本格式突出显示
            content = f"🚨【告警】{message.title}\n\n{message.content}"
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": f"🚨 {message.title}",
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
        elif message.notification_type.value == "progress":
            # 进度类型使用富文本格式
            return {
                "msg_type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"📊 **{message.title}**\n\n{message.content}"
                            }
                        }
                    ],
                    "header": {
                        "template": "blue",
                        "title": {
                            "content": "进度更新",
                            "tag": "plain_text"
                        }
                    }
                }
            }
        else:
            # 其他类型使用文本格式
            content = f"【{message.notification_type.value.upper()}】{message.title}\n\n{message.content}"
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