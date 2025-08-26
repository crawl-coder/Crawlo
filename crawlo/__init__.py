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

# 版本号
from crawlo.__version__ import __version__

# 可选：定义对外暴露的接口
__all__ = [
    'Spider',
    'Item',
    'Request',
    'Response',
    'DownloaderBase',
    'BaseMiddleware',
    '__version__',
]