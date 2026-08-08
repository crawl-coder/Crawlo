#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""兼容存根：已合并入 crawlo.extensions.notifications.core。"""
import sys
import warnings
import importlib

_NEW = 'crawlo.extensions.notifications.core'

if __name__ != _NEW:
    if _NEW not in sys.modules:
        sys.modules[_NEW] = importlib.import_module(_NEW)
    sys.modules[__name__] = sys.modules[_NEW]
    warnings.warn(
        f"{__name__} is deprecated, use {_NEW} instead",
        DeprecationWarning,
        stacklevel=2,
    )
