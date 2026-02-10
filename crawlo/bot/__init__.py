# -*- coding: utf-8 -*-
"""
===================================
爬虫通知系统
===================================

用于爬虫框架的状态通知、异常告警、任务进度更新和数据推送。
支持多种消息渠道（钉钉、飞书、企业微信、邮件、短信）。

模块结构：
- models.py: 统一的通知消息模型
- notifier.py: 通知分发器
- channels/: 消息渠道适配器
- handlers.py: 通知处理器
- config_loader.py: 配置加载器

使用方式：
1. 在 settings.py 中配置通知渠道参数
2. 在爬虫中通过 handlers 发送通知
"""

from crawlo.bot.models import NotificationMessage, NotificationResponse, ChannelType, NotificationType
from crawlo.bot.notifier import NotificationDispatcher, get_notifier
from crawlo.bot.handlers import (
    CrawlerNotificationHandler,
    get_notification_handler,
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress,
    send_template_notification,
    list_notification_templates,
    add_custom_notification_template,
)
from crawlo.bot.duplicate_manager import (
    MessageDeduplicator,
    get_deduplicator,
    reset_deduplicator
)
from crawlo.bot.template_manager import (
    MessageTemplateManager,
    get_template_manager,
    render_message,
    list_available_templates,
    get_template_parameters,  # 新增函数
    COMMON_VARIABLES
)
from crawlo.bot.template_enums import (
    TemplateVariable,
    TemplateVar,
    TemplateName,
    Template
)
from crawlo.bot.resource_monitor_templates import (
    ResourceMonitorTemplateManager,
    get_resource_monitor_manager,
    render_resource_monitor_template,
    list_resource_monitor_templates,
    get_mysql_monitor_templates,
    get_redis_monitor_templates,
    get_mongodb_monitor_templates,
    get_resource_leak_monitor_templates
)
from crawlo.bot.resource_monitor_enums import (
    ResourceTemplate,
    ResourceMonitorVariable,
    ResourceMonitorCategory,
    get_mysql_resource_templates,
    get_redis_resource_templates,
    get_mongodb_resource_templates,
    get_resource_leak_templates
)

__all__ = [
    # 模型
    'NotificationMessage',
    'NotificationResponse',
    'ChannelType',
    'NotificationType',
    # 通知器
    'NotificationDispatcher',
    'get_notifier',
    # 处理器
    'CrawlerNotificationHandler',
    'get_notification_handler',
    'send_crawler_status',
    'send_crawler_alert',
    'send_crawler_progress',
    'send_template_notification',
    'list_notification_templates',
    'add_custom_notification_template',
    # 模板管理器
    'MessageTemplateManager',
    'get_template_manager',
    'render_message',
    'list_available_templates',
    'get_template_parameters',  # 新增函数
    'COMMON_VARIABLES',
    # 去重管理器
    'MessageDeduplicator',
    'get_deduplicator',
    'reset_deduplicator',
    # 资源监控模板
    'ResourceMonitorTemplateManager',
    'get_resource_monitor_manager',
    'render_resource_monitor_template',
    'list_resource_monitor_templates',
    'get_mysql_monitor_templates',
    'get_redis_monitor_templates',
    'get_mongodb_monitor_templates',
    'get_resource_leak_monitor_templates',
    # 模板枚举
    'TemplateVariable',
    'TemplateVar',
    'TemplateName',
    'Template',
    # 资源监控枚举
    'ResourceTemplate',
    'ResourceMonitorVariable',
    'ResourceMonitorCategory',
    'get_mysql_resource_templates',
    'get_redis_resource_templates',
    'get_mongodb_resource_templates',
    'get_resource_leak_templates'
]
