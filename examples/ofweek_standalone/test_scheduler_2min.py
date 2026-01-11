#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试定时任务调度器是否真的在运行
"""

import os
import sys
import asyncio
import time
from datetime import datetime

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
    print(f"    下次执行时间: {datetime.fromtimestamp(job.next_execution_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    当前时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    是否应该执行: {job.should_execute(time.time())}")

print("\n正在启动调度器...")

async def test_run():
    daemon.running = True
    max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
    daemon._semaphore = asyncio.Semaphore(max_concurrent)
    
    # 模拟运行 120 秒（2分钟）
    task = asyncio.create_task(daemon._run_scheduler())
    
    print("调度器主循环已启动，等待 120 秒（2分钟）...")
    start_time = time.time()
    
    # 每 10 秒打印一次状态
    for i in range(12):
        await asyncio.sleep(10)
        elapsed = time.time() - start_time
        print(f"\n已运行 {elapsed:.0f} 秒，当前时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
        for job in daemon.jobs:
            print(f"  任务 {job.spider_name}: 下次执行时间 {datetime.fromtimestamp(job.next_execution_time).strftime('%Y-%m-%d %H:%M:%S')}, 是否应该执行: {job.should_execute(time.time())}")
    
    print("\n停止调度器...")
    daemon.running = False
    await asyncio.sleep(1)
    
    # 打印统计信息
    stats = daemon.get_stats()
    print(f"\n统计信息: {stats}")

asyncio.run(test_run())
