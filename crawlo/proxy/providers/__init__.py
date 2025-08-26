#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:10
# @Author  :   crawl-coder
# @Desc    :   None
"""
from .base import BaseProxyProvider
from .static import StaticProxyProvider
from .api import APIProxyProvider
from .file import FileProxyProvider
from .redis import RedisProxyProvider

__all__ = [
    'BaseProxyProvider',
    'StaticProxyProvider',
    'APIProxyProvider',
    'FileProxyProvider',
    'RedisProxyProvider'
]