#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试定时任务调度器启动
"""

import os
import sys
import asyncio

# 切换到项目目录
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

print(f"切换到项目目录: {project_root}")
print(f"当前工作目录: {os.getcwd()}")

from crawlo.project import get_settings
from crawlo.scheduling.scheduler_daemon import SchedulerDaemon

print("正在加载项目配置...")
settings = get_settings()

print(f"SCHEDULER_ENABLED: {settings.get_bool('SCHEDULER_ENABLED', False)}")
print(f"SCHEDULER_JOBS: {settings.get('SCHEDULER_JOBS', [])}")

if not settings.get_bool('SCHEDULER_ENABLED', False):
    print("\n❌ 定时任务未启用")
    sys.exit(1)

print("\n✅ 定时任务已启用！")
print(f"定时任务配置: {settings.get('SCHEDULER_JOBS', [])}")

daemon = SchedulerDaemon(settings)

print(f"\n调度器已创建，任务数量: {len(daemon.jobs)}")
for job in daemon.jobs:
    print(f"  - {job.spider_name}: {job.trigger}")

print("\n正在启动调度器...")

async def test_run():
    daemon.running = True
    max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
    daemon._semaphore = asyncio.Semaphore(max_concurrent)
    
    # 模拟运行 10 秒
    task = asyncio.create_task(daemon._run_scheduler())
    
    print("调度器主循环已启动，等待 10 秒...")
    await asyncio.sleep(10)
    
    print("停止调度器...")
    daemon.running = False
    await asyncio.sleep(1)
    
    # 打印统计信息
    stats = daemon.get_stats()
    print(f"\n统计信息: {stats}")

asyncio.run(test_run())
