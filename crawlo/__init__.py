#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo - 一个异步爬虫框架
"""
from typing import TYPE_CHECKING

from crawlo.spider import Spider
from crawlo.items import Item, Field
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.middleware import BaseMiddleware
from crawlo.utils import (
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    to_timestamp,
    to_datetime,
    now,
    to_timezone,
    to_utc,
    to_local,
    from_timestamp_with_tz
)
from crawlo import tools

# 框架核心模块 - 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from crawlo.core.framework_initializer import get_framework_initializer, initialize_framework

# 为了向后兼容，从tools中导入cleaners相关的功能
import crawlo.tools as cleaners

# 延迟导入的辅助函数
def get_framework_initializer():
    """延迟导入get_framework_initializer以避免循环依赖"""
    from crawlo.core.framework_initializer import get_framework_initializer as _get_framework_initializer
    return _get_framework_initializer()

def initialize_framework(custom_settings=None):
    """延迟导入initialize_framework以避免循环依赖"""
    from crawlo.core.framework_initializer import initialize_framework as _initialize_framework
    return _initialize_framework(custom_settings)

# 向后兼容的别名
def get_bootstrap_manager():
    """向后兼容的别名"""
    return get_framework_initializer()

# 版本号：优先从元数据读取
try:
    from importlib.metadata import version
    __version__ = version("crawlo")
except Exception:
    # 开发模式下可能未安装，回退到 __version__.py 或 dev
    try:
        from crawlo.__version__ import __version__
    except ImportError:
        __version__ = "dev"

# 定义对外 API
__all__ = [
    'Spider',
    'Item',
    'Field',
    'Request',
    'Response',
    'DownloaderBase',
    'BaseMiddleware',
    'TimeUtils',
    'parse_time',
    'format_time',
    'time_diff',
    'to_timestamp',
    'to_datetime',
    'now',
    'to_timezone',
    'to_utc',
    'to_local',
    'from_timestamp_with_tz',
    'cleaners',
    'tools',
    'get_framework_initializer',
    'get_bootstrap_manager',
    '__version__',
]