#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
错误处理工具子包
=================
提供统一的错误处理和日志记录机制。
"""
from .error_handler import (
    ErrorHandler,
    handle_exception,
    _get_global_error_handler,
)
# ErrorContext / DetailedException 从 crawlo.exceptions 间接导入，
# 保留导出以兼容旧路径 from crawlo.utils.error_handler import ErrorContext
from crawlo.core.errors import ErrorContext, DetailedException  # noqa: F401

__all__ = [
    'ErrorHandler',
    'handle_exception',
    '_get_global_error_handler',
    'ErrorContext',
    'DetailedException',
]
