#!/usr/bin/python
# -*- coding:UTF-8 -*-

# Crawlo核心模块
# 提供框架的核心组件和初始化功能

from .framework_initializer import (
    initialize_framework,
    async_initialize_framework,
    get_framework_initializer,
    is_framework_ready,
    get_framework_logger
)

# 向后兼容的别名
from .framework_initializer import (
    bootstrap_framework,
    get_bootstrap_manager
)

__all__ = [
    'initialize_framework',
    'async_initialize_framework', 
    'get_framework_initializer',
    'is_framework_ready',
    'get_framework_logger',
    # 向后兼容
    'bootstrap_framework',
    'get_bootstrap_manager'
]