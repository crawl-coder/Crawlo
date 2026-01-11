#!/usr/bin/env python3
"""
测试调度器行为
"""
import time
from datetime import datetime
from crawlo.scheduling.job import ScheduledJob


def test_scheduled_job_behavior():
    """测试ScheduledJob的行为"""
    # 创建一个定时任务，每2分钟执行一次
    job = ScheduledJob(
        spider_name='test_spider',
        cron='*/2 * * * *'  # 每2分钟执行一次
    )
    
    print(f"任务初始化完成")
    print(f"初始下次执行时间: {datetime.fromtimestamp(job.next_execution_time)}")
    
    # 模拟调度器的检查循环
    base_time = time.mktime(datetime(2026, 1, 11, 18, 34, 0).timetuple())  # 18:34:00
    
    print(f"\n模拟调度器检查循环 (从 {datetime.fromtimestamp(base_time)} 开始):")
    
    for i in range(20):  # 模拟20秒的检查
        current_time = base_time + i
        current_dt = datetime.fromtimestamp(current_time)
        
        should_execute = job.should_execute(current_time)
        if should_execute:
            print(f"  {current_dt} - 应该执行任务! 下次执行时间更新为: {datetime.fromtimestamp(job.next_execution_time)}")
        else:
            print(f"  {current_dt} - 不执行")
    
    print(f"\n最终下次执行时间: {datetime.fromtimestamp(job.next_execution_time)}")


def test_multiple_initializations():
    """测试多次初始化的情况"""
    print("\n测试多次创建ScheduledJob对象:")
    
    # 模拟在相同时间创建多个任务对象
    base_time = time.mktime(datetime(2026, 1, 11, 18, 34, 0).timetuple())
    
    jobs = []
    for i in range(3):
        job = ScheduledJob(
            spider_name=f'test_spider_{i}',
            cron='*/2 * * * *'
        )
        jobs.append(job)
        print(f"  Job {i}: next_execution_time = {datetime.fromtimestamp(job.next_execution_time)}")
    
    print(f"\n在相同时间点检查是否应该执行:")
    for i, job in enumerate(jobs):
        should_execute = job.should_execute(base_time + 60)  # 60秒后
        print(f"  Job {i}: should_execute = {should_execute}")
        if should_execute:
            print(f"    更新后下次执行时间: {datetime.fromtimestamp(job.next_execution_time)}")


if __name__ == "__main__":
    test_scheduled_job_behavior()
    test_multiple_initializations()