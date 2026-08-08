#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
兼容存根：container.py 已合并入 core/application.py。
v2.0 前发出 DeprecationWarning，并通过 sys.modules 重定向导出同一对象。
"""
import sys
import warnings
import importlib

_NEW_MODULE = 'crawlo.core.application'

if __name__ != _NEW_MODULE:
    if _NEW_MODULE not in sys.modules:
        sys.modules[_NEW_MODULE] = importlib.import_module(_NEW_MODULE)
    sys.modules[__name__] = sys.modules[_NEW_MODULE]
    warnings.warn(
        "crawlo.container is deprecated, use crawlo.core.application instead",
        DeprecationWarning,
        stacklevel=2,
    )
