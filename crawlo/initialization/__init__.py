#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""兼容存根：initialization/ 已合并入 crawlo.core.application。
v2.0 前发出 DeprecationWarning，通过 PEP 562 __getattr__ + sys.modules 保持旧路径可用。"""
import sys
import warnings
import importlib

_NEW = 'crawlo.core.application'

_submodule_map = {
    'registry': _NEW,
    'context': _NEW,
    'core': _NEW,
    'phases': _NEW,
    'built_in': _NEW,
    'utils': _NEW,
}

_symbol_map = {
    'InitializerRegistry': _NEW,
    'InitializationContext': _NEW,
    'CoreInitializer': _NEW,
    'InitializationPhase': _NEW,
    'PhaseResult': _NEW,
    'initialize_framework': _NEW,
    'is_framework_ready': _NEW,
    'get_framework_context': _NEW,
    'get_framework_initializer': _NEW,
    'get_global_registry': _NEW,
    'register_built_in_initializers': _NEW,
}

def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    if name in _symbol_map:
        mod = importlib.import_module(_symbol_map[name])
        if hasattr(mod, name):
            warnings.warn(f"crawlo.initialization.{name} deprecated, use {_symbol_map[name]}.{name}", DeprecationWarning, stacklevel=2)
            return getattr(mod, name)
    raise AttributeError(f"module 'crawlo.initialization' has no attribute '{name}'")

for _old_sub in _submodule_map:
    _old = f'crawlo.initialization.{_old_sub}'
    if _old not in sys.modules:
        try:
            sys.modules[_old] = importlib.import_module(_NEW)
        except Exception:
            pass

warnings.warn("crawlo.initialization deprecated, use crawlo.core.application", DeprecationWarning, stacklevel=2)
