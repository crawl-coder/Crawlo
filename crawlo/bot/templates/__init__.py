# -*- coding: utf-8 -*-
"""
===================================
模板系统
===================================

消息模板管理和渲染功能
"""

from crawlo.bot.templates.manager import (
    MessageTemplateManager,
    get_template_manager,
    render_message,
    list_available_templates,
    get_template_parameters,
    COMMON_VARIABLES,
)
from crawlo.bot.templates.enums import (
    TemplateVariable,
    TemplateVar,
    TemplateName,
    Template,
)

__all__ = [
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
]
