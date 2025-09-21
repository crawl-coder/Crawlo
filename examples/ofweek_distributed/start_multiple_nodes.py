#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
多节点分布式采集测试脚本
启动多个爬虫节点来测试分布式采集功能
"""

import asyncio
import subprocess
import time
import signal
import sys
import os
from typing import List

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def start_crawler_node(node_id: int) -> subprocess.Popen:
    """启动单个爬虫节点"""
    cmd = [
        sys.executable, 
        "-c", 
        f"""
import sys
import os
sys.path.insert(0, '{project_root}')
os.chdir('{project_root}')

from crawlo.crawler import CrawlerProcess

async def run_node():
    process = CrawlerProcess(spider_modules=['ofweek_distributed.spiders'])
    await process.crawl('of_week_distributed')

if __name__ == '__main__':
    import asyncio
    asyncio.run(run_node())
        """
    ]
    
    # 为每个节点设置不同的日志文件
    env = os.environ.copy()
    env['NODE_ID'] = str(node_id)
    
    print(f"启动节点 {node_id}...")
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return process

def monitor_processes(processes: List[subprocess.Popen]):
    """监控所有进程"""
    running_processes = processes.copy()
    
    try:
        while running_processes:
            for process in running_processes[:]:
                if process.poll() is not None:  # 进程已结束
                    print(f"节点进程 {process.pid} 已结束")
                    running_processes.remove(process)
            
            if not running_processes:
                break
                
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("收到中断信号，正在停止所有节点...")
        for process in processes:
            if process.poll() is None:  # 进程仍在运行
                process.terminate()
        
        # 等待所有进程结束
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

async def run_multiple_nodes(num_nodes: int = 5):
    """运行多个节点"""
    print(f"开始启动 {num_nodes} 个分布式爬虫节点...")
    
    processes = []
    
    # 启动多个节点
    for i in range(num_nodes):
        process = start_crawler_node(i + 1)
        processes.append(process)
        print(f"节点 {i+1} 已启动 (PID: {process.pid})")
        # 稍微延迟启动，避免同时启动造成冲突
        time.sleep(2)
    
    print(f"所有 {num_nodes} 个节点已启动，开始监控...")
    
    # 监控进程
    try:
        monitor_processes(processes)
    except Exception as e:
        print(f"监控过程中发生错误: {e}")
    finally:
        # 确保所有进程都已清理
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

def main():
    """主函数"""
    num_nodes = 5  # 默认5个节点
    
    # 如果提供了参数，则使用参数指定的节点数
    if len(sys.argv) > 1:
        try:
            num_nodes = int(sys.argv[1])
        except ValueError:
            print("参数必须是数字")
            sys.exit(1)
    
    print(f"=== Crawlo多节点分布式采集测试 ===")
    print(f"节点数量: {num_nodes}")
    print(f"项目路径: {project_root}")
    print("=" * 50)
    
    try:
        asyncio.run(run_multiple_nodes(num_nodes))
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        sys.exit(1)
    
    print("多节点测试完成")

if __name__ == '__main__':
    main()