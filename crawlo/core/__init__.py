#!/usr/bin/python
# -*- coding:UTF-8 -*-

# Crawlo core modules
# Provides core components and initialization functionality of the framework
import warnings

# Use new initialization system
from ..initialization import (
    initialize_framework,
    is_framework_ready
)


# 向后兼容的别名
def async_initialize_framework(*args, **kwargs):
    """Async wrapper for framework initialization (deprecated)"""
    warnings.warn(
        "async_initialize_framework is deprecated, use initialize_framework instead",
        DeprecationWarning,
        stacklevel=2
    )
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
    """Bootstrap framework - compatibility function (deprecated)"""
    warnings.warn(
        "bootstrap_framework is deprecated, use initialize_framework instead",
        DeprecationWarning,
        stacklevel=2
    )
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
