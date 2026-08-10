#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
兼容存根：此模块已合并入 crawlo.extensions.notifications。
v2.0 前发出 DeprecationWarning，并保持旧路径全部导入可用。

子模块身份保证：旧路径 ``crawlo.bot.core.models`` 等导入返回的模块/类对象
必须与新路径 ``crawlo.extensions.notifications.core.models`` 完全一致。
实现：本模块保持"真实包"身份（sys.modules 中始终是 bot 包），子模块属性
通过 ``__getattr__`` 转发到新路径模块；深路径导入由 walk 预注册覆盖。
"""
import sys
import warnings
import importlib
import pkgutil

_NEW_MODULE = 'crawlo.extensions.notifications'
_SUB_MODULES = {
    'channels': 'channels',
    'core': 'core',
    'monitoring': 'monitoring',
    'templates': 'templates',
    'utils': 'utils',
}

# 子模块全量预注册：旧路径 sys.modules 条目直接指向新路径模块对象。
# 必须先于父包 alias 完成——否则 import 机制会按父包 __path__ 重新加载，
# 产生第二份类对象副本。
for sub in _SUB_MODULES.values():
    new_sub_name = f'{_NEW_MODULE}.{sub}'
    if new_sub_name not in sys.modules:
        sys.modules[new_sub_name] = importlib.import_module(new_sub_name)
    new_sub = sys.modules[new_sub_name]
    sys.modules[f'crawlo.bot.{sub}'] = new_sub
    for mod_info in pkgutil.walk_packages(
        new_sub.__path__,
        prefix=f'{new_sub_name}.',
    ):
        name = mod_info.name
        if name not in sys.modules:
            sys.modules[name] = importlib.import_module(name)
        old_name = 'crawlo.bot.' + name[len(f'{_NEW_MODULE}.'):]
        sys.modules[old_name] = sys.modules[name]


def __getattr__(name):
    """旧路径子包/符号转发到新路径（保持本模块真实包身份）。"""
    if name in _SUB_MODULES:
        return sys.modules[f'{_NEW_MODULE}.{name}']
    return getattr(sys.modules[_NEW_MODULE], name)


warnings.warn(
    f"{__name__} is deprecated, use {_NEW_MODULE} instead",
    DeprecationWarning,
    stacklevel=2,
)
