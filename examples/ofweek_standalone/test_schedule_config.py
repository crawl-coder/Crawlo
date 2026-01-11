#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试定时任务配置加载
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
print(f"SCHEDULER_JOBS: {settings.get('SCHEDULER_JOBS', [])}")
print(f"SCHEDULER_CHECK_INTERVAL: {settings.get_int('SCHEDULER_CHECK_INTERVAL', 1)}")
print(f"SCHEDULER_MAX_CONCURRENT: {settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)}")
print(f"SCHEDULER_JOB_TIMEOUT: {settings.get_int('SCHEDULER_JOB_TIMEOUT', 3600)}")

if settings.get_bool('SCHEDULER_ENABLED', False):
    print("\n✅ 定时任务已启用！")
    print(f"定时任务配置: {settings.get('SCHEDULER_JOBS', [])}")
else:
    print("\n❌ 定时任务未启用")
