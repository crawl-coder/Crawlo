#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo - 一个异步爬虫框架
"""

# 为了向后兼容，从tools中导入cleaners相关的功能
import crawlo.tools as cleaners
from crawlo import tools
from crawlo.crawler import Crawler, CrawlerProcess
from crawlo.downloader import DownloaderBase
from crawlo.items import Item, Field
from crawlo.middleware import BaseMiddleware
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.spider import Spider
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


# 延迟导入的辅助函数
def get_framework_initializer():
    """延迟导入CoreInitializer以避免循环依赖"""
    from crawlo.initialization import CoreInitializer
    return CoreInitializer()


def initialize_framework(custom_settings=None):
    """延迟导入initialize_framework以避免循环依赖"""
    from crawlo.initialization import initialize_framework as _initialize_framework
    return _initialize_framework(custom_settings)


# 向后兼容的别名
def get_bootstrap_manager():
    """向后兼容的别名"""
    return get_framework_initializer()


# 版本号：优先从 __version__.py 读取
try:
    from crawlo.__version__ import __version__
except ImportError:
    # 开发模式下可能未安装，回退到元数据或 dev
    try:
        from importlib.metadata import version
        __version__ = version("crawlo")
    except Exception:
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
    'Crawler',
    'CrawlerProcess',
    'get_framework_initializer',
    'get_bootstrap_manager',
    '__version__',
]
