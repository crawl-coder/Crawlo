#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
兼容存根：scheduling/ 模块已迁移到 commands/。
v2.0 前发出 DeprecationWarning，通过 PEP 562 __getattr__ + sys.modules 保持向后兼容。

迁移映射：
  scheduling.job          → commands.job
  scheduling.registry     → commands.registry
  scheduling.trigger      → commands.trigger
  scheduling.daemon.scheduler → commands.scheduler
  scheduling.daemon.cleanup   → commands.cleanup
"""
import sys
import warnings
import importlib

# 子模块映射
_MODULE_MAP = {
    'job': 'crawlo.commands.job',
    'registry': 'crawlo.commands.registry',
    'trigger': 'crawlo.commands.trigger',
    'daemon.scheduler': 'crawlo.commands.scheduler',
    'daemon.cleanup': 'crawlo.commands.cleanup',
}

# 顶层符号映射（用于 from crawlo.scheduling import xxx）
_SYMBOL_MAP = {
    'SchedulerDaemon': 'crawlo.commands.scheduler',
    'start_scheduler': 'crawlo.commands.scheduler',
    'get_job_registry': 'crawlo.commands.registry',
    'ScheduledJob': 'crawlo.commands.job',
    'JobRegistry': 'crawlo.commands.registry',
    'TimeTrigger': 'crawlo.commands.trigger',
}

def __getattr__(name):
    """PEP 562: 顶层属性转发"""
    if name in _SYMBOL_MAP:
        mod = importlib.import_module(_SYMBOL_MAP[name])
        if hasattr(mod, name):
            warnings.warn(
                f"crawlo.scheduling.{name} is deprecated, use {_SYMBOL_MAP[name]}.{name} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(mod, name)
    raise AttributeError(f"module 'crawlo.scheduling' has no attribute {name}")

# 注册子模块 sys.modules 重定向
for _old_sub, _new_path in _MODULE_MAP.items():
    _old_full = f'crawlo.scheduling.{_old_sub}'
    if _old_full not in sys.modules:
        try:
            sys.modules[_old_full] = importlib.import_module(_new_path)
        except Exception:
            pass

# daemon 子包重定向
_daemon_old = 'crawlo.scheduling.daemon'
_daemon_new = 'crawlo.commands'  # daemon.scheduler → commands.scheduler, daemon.cleanup → commands.cleanup
if _daemon_old not in sys.modules:
    # 创建一个虚拟模块作为 daemon 包的替身
    import types
    _daemon_mod = types.ModuleType(_daemon_old)
    _daemon_mod.__path__ = []  # 标记为包
    sys.modules[_daemon_old] = _daemon_mod

warnings.warn(
    "crawlo.scheduling is deprecated, use crawlo.commands instead",
    DeprecationWarning,
    stacklevel=2,
)
