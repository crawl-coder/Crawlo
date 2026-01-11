#!/usr/bin/env python3
"""
测试修复后的调度器行为
"""
import time
from datetime import datetime
from crawlo.scheduling.job import ScheduledJob


def test_fixed_scheduled_job():
    """测试修复后的ScheduledJob行为"""
    # 创建一个定时任务，每2分钟执行一次
    job = ScheduledJob(
        spider_name='test_spider',
        cron='*/2 * * * *',  # 每2分钟执行一次
        max_retries=2,
        retry_delay=1
    )
    
    print(f"任务初始化完成")
    print(f"初始下次执行时间: {datetime.fromtimestamp(job.next_execution_time)}")
    print(f"初始执行状态: {job.is_executing}")
    
    # 模拟调度器的检查循环
    base_time = time.mktime(datetime(2026, 1, 11, 18, 34, 0).timetuple())  # 18:34:00
    
    print(f"\n模拟调度器检查循环 (从 {datetime.fromtimestamp(base_time)} 开始):")
    
    # 第一次检查 - 应该执行
    current_time = base_time
    current_dt = datetime.fromtimestamp(current_time)
    should_execute = job.should_execute(current_time)
    print(f"  {current_dt} - should_execute = {should_execute}, is_executing = {job.is_executing}")
    
    # 多次检查 - 不应该执行，因为任务正在执行
    for i in range(1, 6):
        current_time = base_time + i
        current_dt = datetime.fromtimestamp(current_time)
        should_execute = job.should_execute(current_time)
        print(f"  {current_dt} - should_execute = {should_execute}, is_executing = {job.is_executing}")
    
    # 标记任务执行完成
    job.mark_execution_finished()
    print(f"\n标记任务执行完成后: is_executing = {job.is_executing}")
    
    # 再次检查 - 不应该执行，因为时间还没到下一个执行点
    current_time = base_time + 60  # 60秒后
    current_dt = datetime.fromtimestamp(current_time)
    should_execute = job.should_execute(current_time)
    print(f"  {current_dt} - should_execute = {should_execute}, is_executing = {job.is_executing}")
    
    # 检查下一个执行时间点
    current_time = base_time + 120  # 2分钟后，应该是下一个执行时间
    current_dt = datetime.fromtimestamp(current_time)
    should_execute = job.should_execute(current_time)
    print(f"  {current_dt} - should_execute = {should_execute}, is_executing = {job.is_executing}")
    
    if should_execute:
        print(f"  标记执行完成...")
        job.mark_execution_finished()
        print(f"  执行完成后的状态: is_executing = {job.is_executing}")


def test_concurrent_execution_prevention():
    """测试并发执行预防"""
    print(f"\n测试并发执行预防:")
    
    job = ScheduledJob(
        spider_name='test_spider',
        cron='*/2 * * * *'
    )
    
    # 获取下一个执行时间
    base_time = job.next_execution_time
    
    print(f"目标执行时间: {datetime.fromtimestamp(base_time)}")
    print(f"初始状态: is_executing = {job.is_executing}")
    
    # 模拟多个调度器检查同时发生
    for i in range(5):
        should_execute = job.should_execute(base_time + 1)  # 稍微超过执行时间
        print(f"  检查 {i+1}: should_execute = {should_execute}, is_executing = {job.is_executing}")
        
    print(f"\n标记执行完成...")
    job.mark_execution_finished()
    print(f"执行完成后的状态: is_executing = {job.is_executing}")
    
    # 再次检查，应该仍然不应该执行（因为时间还没到下一个cron点）
    should_execute = job.should_execute(base_time + 1)
    print(f"再次检查: should_execute = {should_execute}, is_executing = {job.is_executing}")


if __name__ == "__main__":
    test_fixed_scheduled_job()
    test_concurrent_execution_prevention()