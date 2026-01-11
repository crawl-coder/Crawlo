#!/usr/bin/env python3
"""
测试cron表达式解析
"""
import time
from datetime import datetime
from crawlo.scheduling.trigger import TimeTrigger

def test_cron_expression():
    """测试cron表达式的解析和执行时间计算"""
    # 测试每2分钟执行一次的cron表达式
    cron_expr = "*/2 * * * *"
    trigger = TimeTrigger(cron=cron_expr)
    
    print(f"测试cron表达式: {cron_expr}")
    print(f"解析后的cron_parts: {trigger._cron_parts}")
    
    # 测试几个时间点
    base_time = time.mktime(datetime(2026, 1, 11, 18, 34, 0).timetuple())  # 18:34:00
    
    print(f"\n从时间 {datetime.fromtimestamp(base_time)} 开始测试:")
    
    # 检查接下来10分钟内的匹配情况
    for i in range(60):  # 检查60秒
        test_time = base_time + i
        test_dt = datetime.fromtimestamp(test_time)
        is_match = trigger._match_cron(test_dt)
        if is_match:
            print(f"  {test_dt} - 匹配")
    
    # 计算下一个执行时间
    next_time = trigger.get_next_time(base_time)
    print(f"\n从 {datetime.fromtimestamp(base_time)} 开始的下一个执行时间: {datetime.fromtimestamp(next_time)}")
    
    # 再测试下一个时间点
    next_next_time = trigger.get_next_time(next_time)
    print(f"再下一个执行时间: {datetime.fromtimestamp(next_next_time)}")

def test_time_trigger_behavior():
    """测试TimeTrigger的完整行为"""
    cron_expr = "*/2 * * * *"
    trigger = TimeTrigger(cron=cron_expr)
    
    print(f"\n测试TimeTrigger的完整行为:")
    print(f"Cron表达式: {cron_expr}")
    
    # 从一个时间点开始，测试连续调用get_next_time的行为
    current_time = time.mktime(datetime(2026, 1, 11, 18, 0, 0).timetuple())
    
    for i in range(10):
        next_time = trigger.get_next_time(current_time)
        next_dt = datetime.fromtimestamp(next_time)
        print(f"  {i+1:2d}. 从 {datetime.fromtimestamp(current_time)} 开始，下次执行: {next_dt}")
        current_time = next_time + 1  # 模拟时间前进

if __name__ == "__main__":
    test_cron_expression()
    test_time_trigger_behavior()