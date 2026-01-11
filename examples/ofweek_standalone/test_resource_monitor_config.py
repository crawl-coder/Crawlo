#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试资源监控配置加载
"""

import os
import sys

# 切换到项目目录
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

print(f"切换到项目目录: {project_root}")
print(f"当前工作目录: {os.getcwd()}")

from crawlo.project import get_settings

print("正在加载项目配置...")
settings = get_settings()

print(f"SCHEDULER_ENABLED: {settings.get_bool('SCHEDULER_ENABLED', False)}")
print(f"SCHEDULER_RESOURCE_MONITOR_ENABLED: {settings.get_bool('SCHEDULER_RESOURCE_MONITOR_ENABLED', True)}")
print(f"SCHEDULER_RESOURCE_CHECK_INTERVAL: {settings.get_int('SCHEDULER_RESOURCE_CHECK_INTERVAL', 300)}")
print(f"SCHEDULER_RESOURCE_LEAK_THRESHOLD: {settings.get_int('SCHEDULER_RESOURCE_LEAK_THRESHOLD', 3600)}")
