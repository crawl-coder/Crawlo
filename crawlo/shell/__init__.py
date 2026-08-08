#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
交互式终端（已迁移至 crawlo.commands.shell_core）

此模块为向后兼容层，CrawloShell 已迁移至 crawlo.commands.shell_core。
"""

import sys
import warnings
import importlib

# 注册旧子模块路径，使 from crawlo.shell.core import X 仍可用
_old = 'crawlo.shell.core'
if _old not in sys.modules:
    sys.modules[_old] = importlib.import_module('crawlo.commands.shell_core')

from crawlo.commands.shell_core import CrawloShell

warnings.warn(
    "crawlo.shell is deprecated, use crawlo.commands.shell_core instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ['CrawloShell']
