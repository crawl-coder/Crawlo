#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""兼容存根：scheduling.daemon 已拆分到 commands/scheduler.py 和 commands/cleanup.py"""
import sys
import warnings
import importlib

# 重定向子模块
sys.modules['crawlo.scheduling.daemon.scheduler'] = importlib.import_module('crawlo.commands.scheduler')
sys.modules['crawlo.scheduling.daemon.cleanup'] = importlib.import_module('crawlo.commands.cleanup')

warnings.warn(
    "crawlo.scheduling.daemon is deprecated, use crawlo.commands instead",
    DeprecationWarning,
    stacklevel=2,
)
