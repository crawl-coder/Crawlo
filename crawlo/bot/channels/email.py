# -*- coding: utf-8 -*-
"""
===================================
邮件通知渠道
===================================

处理发送邮件通知消息。
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, Any, Optional

from crawlo.logging import get_logger
from crawlo.bot.channels.base import NotificationChannel
from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType


logger = get_logger(__name__)


class EmailChannel(NotificationChannel):
    """
    邮件通知渠道
    
    支持发送邮件通知消息。
    
    配置要求：
    - SMTP_HOST: SMTP 服务器地址
    - SMTP_PORT: SMTP 服务器端口
    - SMTP_USER: SMTP 用户名
    - SMTP_PASSWORD: SMTP 密码或授权码
    - SENDER_EMAIL: 发送方邮箱地址
    """
    
    def __init__(self):
        # 从配置中获取邮件相关信息
        # 在实际应用中，这里应该从框架配置中读取
        self.smtp_host = getattr(self, '_smtp_host', None)
        self.smtp_port = getattr(self, '_smtp_port', 587)
        self.smtp_user = getattr(self, '_smtp_user', None)
        self.smtp_password = getattr(self, '_smtp_password', None)
        self.sender_email = getattr(self, '_sender_email', None)
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EMAIL

    def set_config(self, smtp_host: str, smtp_port: int, smtp_user: str, 
                   smtp_password: str, sender_email: str):
        """
        设置邮件服务器配置
        
        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 服务器端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码或授权码
            sender_email: 发送方邮箱地址
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_email = sender_email

    def send(self, message: NotificationMessage) -> NotificationResponse:
        """
        发送邮件通知
        
        Args:
            message: 通知消息
            
        Returns:
            通知响应
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.sender_email]):
            error_msg = "邮件服务器配置不完整"
            logger.error(f"[Email] {error_msg}")
            return NotificationResponse.error_response(error_msg)
        
        try:
            # 准备邮件内容
            recipients = message.recipients if message.recipients else ['default@example.com']
            subject = f"[{message.notification_type.value.upper()}] {message.title}"
            content = message.content
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 添加邮件正文
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接到SMTP服务器并发送邮件
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()  # 启用TLS加密
            server.login(self.smtp_user, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipients, text)
            server.quit()
            
            logger.info(f"[Email] 邮件发送成功: {subject}, 收件人: {recipients}")
            return NotificationResponse.success_response(
                message="邮件发送成功",
                sent_count=len(recipients)
            )
                
        except Exception as e:
            error_msg = f"邮件发送异常: {str(e)}"
            logger.error(f"[Email] {error_msg}")
            logger.exception(e)
            return NotificationResponse.error_response(error_msg)


# 全局实例
_email_channel = None


def get_email_channel() -> EmailChannel:
    """
    获取邮件通知渠道实例
    """
    global _email_channel
    if _email_channel is None:
        _email_channel = EmailChannel()
    return _email_channel