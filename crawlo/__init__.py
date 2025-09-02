#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo - 一个异步爬虫框架
"""
from crawlo.spider import Spider
from crawlo.items.items import Item
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.downloader import DownloaderBase
from crawlo.middleware import BaseMiddleware


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
    'Request',
    'Response',
    'DownloaderBase',
    'BaseMiddleware',
    '__version__',
]