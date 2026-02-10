# -*- coding: utf-8 -*-
"""
===================================
通知处理器
===================================

处理各种爬虫事件的通知需求。
"""

from typing import Dict, Any, Optional

from crawlo.logging import get_logger
from crawlo.bot.models import NotificationMessage, NotificationResponse, NotificationType, ChannelType
from crawlo.bot.notifier import get_notifier
from crawlo.bot.config_loader import apply_settings_config, ensure_config_loaded
from crawlo.bot.template_manager import get_template_manager, render_message
from crawlo.bot.duplicate_manager import get_deduplicator  # 导入去重管理器


logger = get_logger(__name__)


class CrawlerNotificationHandler:
    """
    爬虫通知处理器
    
    专门处理爬虫框架中的各类通知事件
    """
    
    def __init__(self):
        self.notifier = get_notifier()
        self._enabled, self._channels = self._load_config()
        self._deduplicator = get_deduplicator()  # 添加去重器实例
    
    def _load_config(self) -> tuple:
        """加载通知配置并输出统一日志"""
        try:
            # 使用框架的配置加载机制获取项目配置
            from crawlo.project import get_settings
            settings = get_settings()
            
            # 从配置中读取启用状态和渠道列表
            enabled = settings.get('NOTIFICATION_ENABLED', False)
            channels = settings.get('NOTIFICATION_CHANNELS', [])
            
            # 如果未配置渠道，默认启用所有
            if not channels:
                channels = ['dingtalk', 'feishu', 'wecom', 'email', 'sms']
            
            # 输出统一的状态日志
            if enabled:
                logger.info(f"[Notification] 通知系统已启用 | 渠道: {', '.join(channels)}")
            else:
                logger.info("[Notification] 通知系统已禁用")
            
            return enabled, channels
        except Exception as e:
            logger.debug(f"[Notification] 配置加载异常: {e}")
            logger.info("[Notification] 通知系统已禁用")
            return False, []
    
    def _should_skip_duplicate(self, title: str, content: str, channel: str) -> bool:
        """
        检查是否应该跳过重复消息
        
        Args:
            title: 消息标题
            content: 消息内容
            channel: 消息渠道
            
        Returns:
            是否为重复消息
        """
        return self._deduplicator.is_duplicate(title, content, channel)
    
    def _send_if_enabled(self, message: NotificationMessage) -> NotificationResponse:
        """如果通知系统启用则发送，否则返回跳过的响应"""
        if not self._enabled:
            return NotificationResponse.success_response("通知系统已禁用")
        
        # 检查渠道是否在启用列表中
        if message.channel not in self._channels:
            return NotificationResponse.success_response(f"渠道 {message.channel} 未启用")
        
        # 检查是否为重复消息
        if self._should_skip_duplicate(message.title, message.content, message.channel):
            logger.debug(f"[Notification] 跳过重复消息: {message.title[:50]}...")
            return NotificationResponse.success_response("消息重复，已跳过发送")
        
        # 确保配置已加载
        ensure_config_loaded()
        return self.notifier.send_notification(message)
    
    def send_status_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送状态通知
        
        Args:
            title: 通知标题
            content: 通知内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.STATUS,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self._send_if_enabled(message)
    
    def send_alert_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "high",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送告警通知
        
        Args:
            title: 告警标题
            content: 告警内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.ALERT,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self._send_if_enabled(message)
    
    def send_progress_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送进度通知
        
        Args:
            title: 进度标题
            content: 进度内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.PROGRESS,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self._send_if_enabled(message)
    
    def send_data_notification(
        self, 
        title: str, 
        content: str, 
        channel: ChannelType = ChannelType.DINGTALK,
        priority: str = "medium",
        recipients: Optional[list] = None
    ) -> NotificationResponse:
        """
        发送数据推送通知
        
        Args:
            title: 数据标题
            content: 数据内容
            channel: 通知渠道
            priority: 优先级
            recipients: 接收者列表
            
        Returns:
            通知响应
        """
        message = NotificationMessage(
            channel=channel.value,
            notification_type=NotificationType.DATA,
            title=title,
            content=content,
            priority=priority,
            recipients=recipients or [],
        )
        
        return self._send_if_enabled(message)
    
    def send_template_notification(self, template_name: str, channel: ChannelType = ChannelType.DINGTALK, **kwargs) -> NotificationResponse:
        """
        使用模板发送通知
        
        Args:
            template_name: 模板名称
            channel: 通知渠道
            **kwargs: 模板变量
            
        Returns:
            通知响应
        """
        # 渲染模板
        message = render_message(template_name, **kwargs)
        if not message:
            return NotificationResponse.error_response(f"模板渲染失败: {template_name}")
        
        # 发送通知
        return self.send_status_notification(
            title=message['title'],
            content=message['content'],
            channel=channel
        )
    
    def list_templates(self) -> Dict[str, str]:
        """
        列出所有可用模板
        
        Returns:
            模板名称和描述的字典
        """
        manager = get_template_manager()
        return manager.list_templates()
    
    def add_custom_template(self, name: str, title: str, content: str):
        """
        添加自定义模板
        
        Args:
            name: 模板名称
            title: 标题模板
            content: 内容模板
        """
        manager = get_template_manager()
        manager.add_template(name, title, content)
        logger.info(f"[Handler] 添加自定义模板: {name}")


# 全局通知处理器实例
_notification_handler = None


def get_notification_handler() -> CrawlerNotificationHandler:
    """
    获取全局通知处理器实例
    """
    global _notification_handler
    
    if _notification_handler is None:
        _notification_handler = CrawlerNotificationHandler()
    
    return _notification_handler


def send_crawler_status(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫状态通知的便捷函数
    
    Args:
        title: 状态标题
        content: 状态内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_status_notification(title, content, channel)


def send_crawler_alert(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫告警通知的便捷函数
    
    Args:
        title: 告警标题
        content: 告警内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_alert_notification(title, content, channel)


def send_crawler_progress(title: str, content: str, channel: ChannelType = ChannelType.DINGTALK) -> NotificationResponse:
    """
    发送爬虫进度通知的便捷函数
    
    Args:
        title: 进度标题
        content: 进度内容
        channel: 通知渠道
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_progress_notification(title, content, channel)


# 模板相关便捷函数
def send_template_notification(template_name: str, channel: ChannelType = ChannelType.DINGTALK, **kwargs) -> NotificationResponse:
    """
    使用模板发送通知的便捷函数
    
    Args:
        template_name: 模板名称
        channel: 通知渠道
        **kwargs: 模板变量
        
    Returns:
        通知响应
    """
    handler = get_notification_handler()
    return handler.send_template_notification(template_name, channel, **kwargs)


def list_notification_templates() -> Dict[str, str]:
    """
    列出所有可用的通知模板
    
    Returns:
        模板名称和描述的字典
    """
    handler = get_notification_handler()
    return handler.list_templates()


def add_custom_notification_template(name: str, title: str, content: str):
    """
    添加自定义通知模板
    
    Args:
        name: 模板名称
        title: 标题模板
        content: 内容模板
    """
    handler = get_notification_handler()
    handler.add_custom_template(name, title, content)