#!/usr/bin/env python3
"""
定时任务监控脚本
用于监控定时爬虫任务的执行情况和资源使用情况
"""
import time
import psutil
import os
from datetime import datetime


def monitor_scheduler():
    """监控定时任务进程"""
    print(f"[{datetime.now()}] 开始监控定时任务进程...")
    
    # 查找定时任务进程
    target_process = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'start_scheduler()' in cmdline and 'python' in proc.info['name']:
                target_process = proc
                print(f"找到定时任务进程 PID: {proc.info['pid']}")
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not target_process:
        print("未找到定时任务进程")
        return
    
    # 监控循环
    initial_time = time.time()
    iterations = 0
    max_iterations = 10  # 监控10轮
    
    while iterations < max_iterations:
        try:
            # 获取进程信息
            cpu_percent = target_process.cpu_percent()
            memory_mb = target_process.memory_info().rss / 1024 / 1024
            num_threads = target_process.num_threads()
            
            # 获取父进程信息
            parent = target_process.parent()
            if parent:
                parent_info = f"Parent PID: {parent.pid}"
            else:
                parent_info = "No parent"
            
            print(f"\n[{datetime.now()}] 第 {iterations + 1} 轮监控:")
            print(f"  进程 PID: {target_process.pid}")
            print(f"  CPU 使用率: {cpu_percent}%")
            print(f"  内存使用: {memory_mb:.2f} MB")
            print(f"  线程数: {num_threads}")
            print(f"  {parent_info}")
            
            # 检查进程是否还在运行
            if not target_process.is_running():
                print("  进程已停止运行")
                break
            
            iterations += 1
            
            # 等待2分钟，模拟定时任务的执行间隔
            print(f"  等待2分钟进行下一轮监控...")
            time.sleep(120)
            
        except psutil.NoSuchProcess:
            print(f"[{datetime.now()}] 进程已终止")
            break
        except Exception as e:
            print(f"[{datetime.now()}] 监控出错: {e}")
            break
    
    total_duration = time.time() - initial_time
    print(f"\n[{datetime.now()}] 监控结束，总时长: {total_duration/60:.2f} 分钟")


if __name__ == "__main__":
    monitor_scheduler()