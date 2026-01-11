#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试定时任务配置加载
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
