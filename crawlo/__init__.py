#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo - 一个异步爬虫框架
"""

# Windows 平台：自动修补 asyncio ProactorEventLoop 的析构警告
# 必须在所有其他导入之前执行，确保补丁在任何 asyncio transport 创建之前生效
import sys
if sys.platform == 'win32':
    from crawlo.utils.asyncio_utils import apply_windows_patches
    apply_windows_patches()


# 延迟导入的辅助函数
def _lazy_import(module_name, attr_name):
    """延迟导入以避免循环依赖"""
    import importlib
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def __getattr__(name):
    """实现模块级别的延迟导入（PEP 562）"""
    # 核心类延迟导入
    if name == 'Crawler':
        return _lazy_import('crawlo.crawler', 'Crawler')
    elif name == 'CrawlerProcess':
        return _lazy_import('crawlo.crawler_process', 'CrawlerProcess')
    elif name == 'DownloaderBase':
        return _lazy_import('crawlo.downloader', 'DownloaderBase')
    elif name == 'Item':
        return _lazy_import('crawlo.items', 'Item')
    elif name == 'Field':
        return _lazy_import('crawlo.items', 'Field')
    elif name == 'BaseMiddleware':
        return _lazy_import('crawlo.middleware', 'BaseMiddleware')
    elif name == 'Request':
        return _lazy_import('crawlo.network.request', 'Request')
    elif name == 'Response':
        return _lazy_import('crawlo.network.response', 'Response')
    elif name == 'Spider':
        return _lazy_import('crawlo.spider', 'Spider')
    elif name == 'Failure':
        return _lazy_import('crawlo.core.failure', 'Failure')
    elif name in ('cleaners', 'helpers'):
        import crawlo.helpers
        return crawlo.helpers
    # 时间工具 — 原 from crawlo.helpers.time_utils import ...
    elif name in ('TimeUtils', 'parse_time', 'format_time', 'time_diff',
                  'to_timestamp', 'to_datetime', 'now',
                  'to_timezone', 'to_utc', 'to_local',
                  'from_timestamp_with_tz'):
        from crawlo.helpers.time_utils import (
            TimeUtils, parse_time, format_time, time_diff,
            to_timestamp, to_datetime, now,
            to_timezone, to_utc, to_local,
            from_timestamp_with_tz,
        )
        _globals = globals()
        _globals['TimeUtils'] = TimeUtils
        _globals['parse_time'] = parse_time
        _globals['format_time'] = format_time
        _globals['time_diff'] = time_diff
        _globals['to_timestamp'] = to_timestamp
        _globals['to_datetime'] = to_datetime
        _globals['now'] = now
        _globals['to_timezone'] = to_timezone
        _globals['to_utc'] = to_utc
        _globals['to_local'] = to_local
        _globals['from_timestamp_with_tz'] = from_timestamp_with_tz
        return _globals[name]
    raise AttributeError(f"module 'crawlo' has no attribute '{name}'")


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
    try:
        from importlib.metadata import version
        __version__ = version("crawlo")
    except Exception:
        __version__ = "dev"

# 定义对外 API
__all__ = [
    'Spider', 'Item', 'Field', 'Request', 'Response',
    'DownloaderBase', 'BaseMiddleware',
    'TimeUtils', 'parse_time', 'format_time', 'time_diff',
    'to_timestamp', 'to_datetime', 'now',
    'to_timezone', 'to_utc', 'to_local', 'from_timestamp_with_tz',
    'cleaners', 'helpers',
    'Crawler', 'CrawlerProcess',
    'get_framework_initializer', 'get_bootstrap_manager', '__version__',
]
