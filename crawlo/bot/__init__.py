# -*- coding: utf-8 -*-
"""
===================================
爬虫通知系统
===================================

用于爬虫框架的状态通知、异常告警、任务进度更新和数据推送。
支持多种消息渠道（钉钉、飞书、企业微信、邮件、短信）。

重构后的模块结构：
- core/: 核心功能（models, notifier, handlers）
- channels/: 消息渠道适配器
- templates/: 模板系统
- monitoring/: 资源监控
- utils/: 工具模块（config, deduplicator）

使用方式：
1. 在 settings.py 中配置通知渠道参数
2. 在爬虫中通过 handlers 发送通知
"""

# 核心模块
from crawlo.bot.core import (
    NotificationMessage,
    NotificationResponse,
    ChannelResponse,
    ChannelType,
    NotificationType,
    NotificationDispatcher,
    get_notifier,
    CrawlerNotificationHandler,
    get_notification_handler,
    send_crawler_status,
    send_crawler_alert,
    send_crawler_progress,
    send_template_notification,
    list_notification_templates,
    add_custom_notification_template,
)

# 模板系统
from crawlo.bot.templates import (
    MessageTemplateManager,
    get_template_manager,
    render_message,
    list_available_templates,
    get_template_parameters,
    COMMON_VARIABLES,
    TemplateVariable,
    TemplateVar,
    TemplateName,
    Template,
)

# 资源监控
from crawlo.bot.monitoring import (
    ResourceMonitorTemplateManager,
    get_resource_monitor_manager,
    render_resource_monitor_template,
    list_resource_monitor_templates,
    get_mysql_monitor_templates,
    get_redis_monitor_templates,
    get_mongodb_monitor_templates,
    get_resource_leak_monitor_templates,
    ResourceTemplate,
    ResourceMonitorVariable,
    ResourceMonitorCategory,
    get_mysql_resource_templates,
    get_redis_resource_templates,
    get_mongodb_resource_templates,
    get_resource_leak_templates,
)

# 工具模块
from crawlo.bot.utils import (
    MessageDeduplicator,
    get_deduplicator,
    reset_deduplicator,
    apply_settings_config,
    ensure_config_loaded,
)

__all__ = [
    # 模型
    'NotificationMessage',
    'NotificationResponse',
    'ChannelResponse',
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
    'get_template_parameters',
    'COMMON_VARIABLES',
    # 模板枚举
    'TemplateVariable',
    'TemplateVar',
    'TemplateName',
    'Template',
    # 资源监控
    'ResourceMonitorTemplateManager',
    'get_resource_monitor_manager',
    'render_resource_monitor_template',
    'list_resource_monitor_templates',
    'get_mysql_monitor_templates',
    'get_redis_monitor_templates',
    'get_mongodb_monitor_templates',
    'get_resource_leak_monitor_templates',
    # 资源监控枚举
    'ResourceTemplate',
    'ResourceMonitorVariable',
    'ResourceMonitorCategory',
    'get_mysql_resource_templates',
    'get_redis_resource_templates',
    'get_mongodb_resource_templates',
    'get_resource_leak_templates',
    # 去重管理器
    'MessageDeduplicator',
    'get_deduplicator',
    'reset_deduplicator',
    # 配置加载
    'apply_settings_config',
    'ensure_config_loaded',
]
