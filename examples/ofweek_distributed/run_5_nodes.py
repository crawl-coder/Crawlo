#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
启动5个分布式爬虫节点进行测试
"""

import subprocess
import time
import os
import sys
import signal
from typing import List

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 存储所有启动的进程
processes: List[subprocess.Popen] = []

def signal_handler(sig, frame):
    """信号处理函数，用于优雅关闭所有进程"""
    print("\n收到中断信号，正在关闭所有节点...")
    for process in processes:
        if process.poll() is None:  # 进程仍在运行
            process.terminate()
    
    # 等待所有进程结束
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    print("所有节点已关闭")
    sys.exit(0)

def start_node(node_id: int) -> subprocess.Popen:
    """启动单个节点"""
    # 设置环境变量
    env = os.environ.copy()
    env['NODE_ID'] = str(node_id)
    env['PYTHONPATH'] = project_root
    
    # 切换到项目目录
    cwd = project_root
    
    # 启动进程
    process = subprocess.Popen(
        [sys.executable, 'run.py'],
        env=env,
        cwd=cwd,
        stdout=open(f'node_{node_id}_stdout.log', 'w'),
        stderr=open(f'node_{node_id}_stderr.log', 'w'),
        text=True
    )
    
    return process

def monitor_nodes():
    """监控节点运行状态"""
    print("监控节点运行状态 (按 Ctrl+C 停止所有节点):")
    print("-" * 50)
    
    try:
        while True:
            running_count = 0
            for i, process in enumerate(processes):
                if process.poll() is None:  # 进程仍在运行
                    running_count += 1
                    print(f"节点 {i+1}: 运行中 (PID: {process.pid})")
                else:
                    print(f"节点 {i+1}: 已结束 (退出码: {process.returncode})")
            
            print(f"活动节点数: {running_count}/{len(processes)}")
            print("-" * 50)
            
            # 检查是否所有节点都已完成
            if running_count == 0:
                print("所有节点已完成任务")
                break
            
            time.sleep(10)  # 每10秒检查一次
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

def main():
    """主函数"""
    print("=== Crawlo 5节点分布式采集测试 ===")
    print(f"项目路径: {project_root}")
    print("启动5个分布式爬虫节点...")
    print("=" * 50)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动5个节点
    for i in range(5):
        print(f"启动节点 {i+1}...")
        process = start_node(i + 1)
        processes.append(process)
        print(f"节点 {i+1} 已启动 (PID: {process.pid})")
        # 稍微延迟启动，避免同时启动造成冲突
        time.sleep(2)
    
    print("=" * 50)
    print("所有5个节点已启动，开始监控...")
    
    # 监控节点
    monitor_nodes()
    
    print("5节点分布式采集测试完成")

if __name__ == '__main__':
    main()