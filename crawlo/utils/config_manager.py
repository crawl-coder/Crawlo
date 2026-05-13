#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置管理模块（向后兼容重导出层）
===========
⚠️ 本模块已弃用，将在下一主版本中移除。
ConfigUtils → crawlo.utils.misc
EnvConfigManager → crawlo.settings.setting_manager

新增代码请直接导入新位置。
"""

import warnings

warnings.warn(
    "crawlo.utils.config_manager is deprecated. "
    "Use crawlo.utils.misc.ConfigUtils or "
    "crawlo.settings.setting_manager.EnvConfigManager instead.",
    DeprecationWarning,
    stacklevel=2,
)

# 向后兼容导入
from crawlo.utils.misc import ConfigUtils
from crawlo.settings.setting_manager import EnvConfigManager

# 导出所有公共 API（保持向后兼容）
__all__ = [
    'ConfigUtils',
    'EnvConfigManager',
]
