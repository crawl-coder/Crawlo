# -*- coding: utf-8 -*-
"""
===================================
工具模块
===================================

配置加载和消息去重功能
"""

from crawlo.bot.utils.config_loader import (
    apply_settings_config,
    ensure_config_loaded,
)
from crawlo.bot.utils.deduplicator import (
    MessageDeduplicator,
    get_deduplicator,
    reset_deduplicator,
)

__all__ = [
    # 配置加载
    'apply_settings_config',
    'ensure_config_loaded',
    # 消息去重
    'MessageDeduplicator',
    'get_deduplicator',
    'reset_deduplicator',
]
