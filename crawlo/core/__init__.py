#!/usr/bin/python
# -*- coding:UTF-8 -*-

# Crawlo核心模块
# 提供框架的核心组件和初始化功能

# 使用新的初始化系统
from ..initialization import (
    initialize_framework,
    is_framework_ready
)


# 向后兼容的别名
def async_initialize_framework(*args, **kwargs):
    """Async wrapper for framework initialization"""
    return initialize_framework(*args, **kwargs)


def get_framework_initializer():
    """Get framework initializer - compatibility function"""
    from ..initialization.core import CoreInitializer
    return CoreInitializer()


def get_framework_logger(name='crawlo.core'):
    """Get framework logger - compatibility function"""
    from ..logging import get_logger
    return get_logger(name)


# 向后兼容
def bootstrap_framework(*args, **kwargs):
    """Bootstrap framework - compatibility function"""
    return initialize_framework(*args, **kwargs)


def get_bootstrap_manager():
    """Get bootstrap manager - compatibility function"""
    return get_framework_initializer()


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
