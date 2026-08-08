#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Python 版本兼容工具子包
========================
提供版本守卫的兼容层访问 Python 3.14+ 新特性。
"""
from .py314_compat import *  # noqa: F401,F403
from .py314_compat import __all__ as _py314_all  # noqa: F401

__all__ = list(_py314_all)
