#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""兼容存根：factories/ 已合并入 crawlo.core.factories。
v2.0 前发出 DeprecationWarning，通过 PEP 562 __getattr__ + sys.modules 保持旧路径可用。"""
import sys
import warnings
import importlib

_NEW = 'crawlo.core.factories'

_submodule_map = {
    'registry': 'crawlo.core.factories',
    'utils': 'crawlo.core.factories',
    'base': 'crawlo.core.factories',
    'crawler': 'crawlo.core.factories',
}

def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    mod = importlib.import_module(_NEW)
    if hasattr(mod, name):
        warnings.warn(f"crawlo.factories.{name} deprecated, use {_NEW}.{name}", DeprecationWarning, stacklevel=2)
        return getattr(mod, name)
    raise AttributeError(name)

for _old_sub in _submodule_map:
    _old = f'crawlo.factories.{_old_sub}'
    if _old not in sys.modules:
        try:
            sys.modules[_old] = importlib.import_module(_NEW)
        except Exception:
            pass

warnings.warn("crawlo.factories deprecated, use crawlo.core.factories", DeprecationWarning, stacklevel=2)
