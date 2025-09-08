"""
分布式部署脚本
在多个节点上启动分布式爬虫
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def deploy_node(node_name, concurrent_requests=20, redis_url="redis://localhost:6379/0"):
    """在指定节点部署爬虫"""
    
    print(f"正在节点 {node_name} 上启动分布式爬虫...")
    print(f"并发请求数: {concurrent_requests}")
    print(f"Redis连接: {redis_url}")
    
    # 设置环境变量
    env_vars = {
        'CRAWLO_NODE_NAME': node_name,
        'CRAWLO_CONCURRENT_REQUESTS': str(concurrent_requests),
        'CRAWLO_REDIS_URL': redis_url
    }
    
    # 构建命令
    cmd = [sys.executable, 'run.py']
    
    # 启动进程
    try:
        process = subprocess.Popen(
            cmd,
            env={**dict(os.environ), **env_vars},
            cwd=Path(__file__).parent
        )
        
        print(f"节点 {node_name} 启动成功，PID: {process.pid}")
        return process
        
    except Exception as e:
        print(f"启动节点 {node_name} 失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='分布式爬虫部署工具')
    parser.add_argument('node_name', help='节点名称')
    parser.add_argument('--concurrent', '-c', type=int, default=20, 
                       help='并发请求数 (default: 20)')
    parser.add_argument('--redis-url', '-r', default='redis://localhost:6379/0',
                       help='Redis连接URL (default: redis://localhost:6379/0)')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='后台运行模式')
    
    args = parser.parse_args()
    
    import os
    
    if args.daemon:
        # 后台运行模式
        process = deploy_node(args.node_name, args.concurrent, args.redis_url)
        if process:
            print(f"节点 {args.node_name} 已在后台启动")
            # 保存PID文件
            pid_file = f"{args.node_name}.pid"
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            print(f"PID已保存到 {pid_file}")
    else:
        # 前台运行模式
        process = deploy_node(args.node_name, args.concurrent, args.redis_url)
        if process:
            try:
                process.wait()  # 等待进程结束
            except KeyboardInterrupt:
                print(f"\n正在停止节点 {args.node_name}...")
                process.terminate()
                process.wait()
                print("节点已停止")


if __name__ == "__main__":
    main()