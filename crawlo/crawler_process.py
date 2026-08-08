#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
兼容存根：此模块已合并入 crawlo.crawler。
v2.0 前发出 DeprecationWarning，并通过 sys.modules 导出 CrawlerProcess。
"""
import sys
import warnings
import importlib

_NEW_MODULE = 'crawlo.crawler'

if __name__ != _NEW_MODULE:
    if _NEW_MODULE not in sys.modules:
        sys.modules[_NEW_MODULE] = importlib.import_module(_NEW_MODULE)
    _new = sys.modules[_NEW_MODULE]
    # 重新注册本模块 → 指向新模块（使 from crawlo.crawler_process import CrawlerProcess 等价）
    sys.modules[__name__] = _new
    warnings.warn(
        f"{__name__} is deprecated, use {_NEW_MODULE} instead (CrawlerProcess now lives in crawlo.crawler)",
        DeprecationWarning,
        stacklevel=2,
    )
