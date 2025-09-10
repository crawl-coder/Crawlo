#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo - 一个异步爬虫框架
"""
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
from crawlo import cleaners
from crawlo import tools

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
    '__version__',
]