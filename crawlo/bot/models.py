# -*- coding: utf-8 -*-
"""
===================================
通知消息模型
===================================

定义统一的通知消息和响应模型，屏蔽各渠道差异。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class NotificationType(str, Enum):
    """通知类型"""
    STATUS = "status"          # 状态通知
    ALERT = "alert"            # 异常告警
    PROGRESS = "progress"      # 进度更新
    DATA = "data"              # 数据推送
    TASK = "task"              # 任务通知


class ChannelType(str, Enum):
    """消息渠道类型"""
    DINGTALK = "dingtalk"      # 钉钉
    FEISHU = "feishu"          # 飞书
    WECOM = "wecom"            # 企业微信
    EMAIL = "email"            # 邮件
    SMS = "sms"                # 短信


@dataclass
class NotificationMessage:
    """
    统一的通知消息模型
    
    将各渠道的消息格式统一为此模型，便于通知分发器处理。
    
    Attributes:
        channel: 消息渠道标识
        notification_type: 通知类型
        title: 通知标题
        content: 通知内容
        priority: 优先级 (low, medium, high, urgent)
        recipients: 接收者列表
        metadata: 额外元数据
        timestamp: 消息时间戳
        raw_data: 原始请求数据（渠道特定，用于调试）
    """
    channel: str
    notification_type: NotificationType
    title: str
    content: str
    priority: str = "medium"
    recipients: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationResponse:
    """
    统一的通知响应模型
    
    通知分发器返回此模型，由渠道适配器转换为渠道特定格式。
    
    Attributes:
        success: 是否发送成功
        message: 响应消息
        error: 错误信息（如果有）
        sent_count: 成功发送的数量
        failed_count: 发送失败的数量
        extra: 额外数据（渠道特定）
    """
    success: bool
    message: str = ""
    error: str = ""
    sent_count: int = 0
    failed_count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_response(cls, message: str = "发送成功", sent_count: int = 1) -> 'NotificationResponse':
        """创建成功响应"""
        return cls(success=True, message=message, sent_count=sent_count)
    
    @classmethod
    def error_response(cls, error: str, failed_count: int = 1) -> 'NotificationResponse':
        """创建错误响应"""
        return cls(success=False, error=error, failed_count=failed_count)


@dataclass
class ChannelResponse:
    """
    渠道响应模型
    
    渠道适配器返回此模型，包含 HTTP 响应内容或其他渠道特定响应。
    
    Attributes:
        status_code: HTTP 状态码或渠道特定状态
        body: 响应体（字典，将被序列化）
        headers: 额外的响应头
        success: 渠道层面的成功状态
    """
    status_code: int = 200
    body: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    success: bool = True
    
    @classmethod
    def success(cls, body: Optional[Dict] = None) -> 'ChannelResponse':
        """创建成功响应"""
        return cls(status_code=200, body=body or {}, success=True)
    
    @classmethod
    def error(cls, message: str, status_code: int = 400) -> 'ChannelResponse':
        """创建错误响应"""
        return cls(status_code=status_code, body={"error": message}, success=False)