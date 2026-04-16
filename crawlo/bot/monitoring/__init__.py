# -*- coding: utf-8 -*-
"""
===================================
资源监控
===================================

资源监控模板和枚举
"""

from crawlo.bot.monitoring.templates import (
    ResourceMonitorTemplateManager,
    get_resource_monitor_manager,
    render_resource_monitor_template,
    list_resource_monitor_templates,
    get_mysql_monitor_templates,
    get_redis_monitor_templates,
    get_mongodb_monitor_templates,
    get_resource_leak_monitor_templates,
)
from crawlo.bot.monitoring.enums import (
    ResourceTemplate,
    ResourceMonitorVariable,
    ResourceMonitorCategory,
    get_mysql_resource_templates,
    get_redis_resource_templates,
    get_mongodb_resource_templates,
    get_resource_leak_templates,
)

__all__ = [
    # 监控模板
    'ResourceMonitorTemplateManager',
    'get_resource_monitor_manager',
    'render_resource_monitor_template',
    'list_resource_monitor_templates',
    'get_mysql_monitor_templates',
    'get_redis_monitor_templates',
    'get_mongodb_monitor_templates',
    'get_resource_leak_monitor_templates',
    # 监控枚举
    'ResourceTemplate',
    'ResourceMonitorVariable',
    'ResourceMonitorCategory',
    'get_mysql_resource_templates',
    'get_redis_resource_templates',
    'get_mongodb_resource_templates',
    'get_resource_leak_templates',
]
