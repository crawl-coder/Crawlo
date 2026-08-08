#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
兼容存根：此模块已合并入 crawlo.extensions。
v2.0 前发出 DeprecationWarning，并通过 sys.modules + PEP 562 __getattr__ 导出原 extension 符号。
"""
import sys
import warnings
import importlib

_NEW_MODULE = 'crawlo.extensions'

# 文件名映射：旧路径 → 新路径
_FILE_MAP = {
    'memory_monitor': 'extensions.monitor.memory',
    'mysql_monitor': 'extensions.monitor.mysql',
    'redis_monitor': 'extensions.monitor.redis',
    'logging_extension': 'extensions.logging',
    'health_check': 'extensions.health_check',
    'log_stats': 'extensions.log_stats',
    'log_interval': 'extensions.log_interval',
    'request_recorder': 'extensions.request_recorder',
    'interfaces': 'extensions.interfaces',
    'monitor': 'extensions.monitor',
    'monitor.base': 'extensions.monitor.base',
    'monitor.monitor_manager': 'extensions.monitor.monitor_manager',
    'monitor.performance_monitor': 'extensions.monitor.performance_monitor',
}


def __getattr__(name):
    """PEP 562: 模块级别属性转发"""
    if name in _FILE_MAP:
        new_module_path = f'crawlo.{_FILE_MAP[name]}'
        mod = importlib.import_module(new_module_path)
        warnings.warn(
            f"crawlo.extension.{name} is deprecated, use {new_module_path} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return mod
    # 对于 __init__ 级别的符号（如 ExtensionManager 等），从 extensions 包转发
    if not name.startswith('_'):
        extensions_mod = importlib.import_module(_NEW_MODULE)
        if hasattr(extensions_mod, name):
            warnings.warn(
                f"crawlo.extension.{name} is deprecated, use {_NEW_MODULE}.{name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(extensions_mod, name)
    raise AttributeError(f"module 'crawlo.extension' has no attribute {name}")


# 注册子模块级别的 sys.modules 重定向
for _old_sub, _new_sub in _FILE_MAP.items():
    _old_path = f'crawlo.extension.{_old_sub}'
    _new_path = f'crawlo.{_new_sub}'
    if _old_path not in sys.modules:
        try:
            sys.modules[_old_path] = importlib.import_module(_new_path)
        except Exception:
            pass

warnings.warn(
    "crawlo.extension is deprecated, use crawlo.extensions instead",
    DeprecationWarning,
    stacklevel=2,
)
