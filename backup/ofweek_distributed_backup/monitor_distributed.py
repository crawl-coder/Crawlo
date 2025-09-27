#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
分布式采集监控脚本
实时监控Redis中的分布式采集状态
"""

import redis
import time
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def monitor_distributed_crawling():
    """监控分布式采集状态"""
    print("=== Crawlo分布式采集状态监控 ===")
    print("按 Ctrl+C 停止监控")
    print("=" * 50)
    
    try:
        # 连接Redis
        r = redis.Redis(host='localhost', port=6379, db=2, decode_responses=False)
        r.ping()
        print("✓ Redis连接成功")
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        return
    
    try:
        while True:
            # 获取队列状态
            queue_size = r.zcard("crawlo:ofweek_distributed:queue:requests")
            
            # 获取去重指纹数量
            request_fingerprints = r.scard("crawlo:ofweek_distributed:filter:fingerprint")
            item_fingerprints = r.scard("crawlo:ofweek_distributed:item:fingerprint")
            
            # 清屏并显示状态
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("=== Crawlo分布式采集实时状态 ===")
            print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            print(f"请求队列大小: {queue_size:,}")
            print(f"请求去重指纹: {request_fingerprints:,}")
            print(f"数据项去重指纹: {item_fingerprints:,}")
            print("=" * 50)
            print("说明:")
            print("- 请求队列大小: 等待处理的请求数量")
            print("- 请求去重指纹: 已处理的唯一请求数量")
            print("- 数据项去重指纹: 已保存的唯一数据项数量")
            print("=" * 50)
            print("按 Ctrl+C 停止监控")
            
            time.sleep(5)  # 每5秒更新一次
            
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"监控过程中发生错误: {e}")

def get_final_stats():
    """获取最终统计信息"""
    try:
        # 连接Redis
        r = redis.Redis(host='localhost', port=6379, db=2, decode_responses=False)
        r.ping()
        
        # 获取最终状态
        queue_size = r.zcard("crawlo:ofweek_distributed:queue:requests")
        request_fingerprints = r.scard("crawlo:ofweek_distributed:filter:fingerprint")
        item_fingerprints = r.scard("crawlo:ofweek_distributed:item:fingerprint")
        
        print("\n=== 分布式采集最终统计 ===")
        print(f"剩余请求队列: {queue_size:,}")
        print(f"总请求数: {request_fingerprints:,}")
        print(f"总数据项数: {item_fingerprints:,}")
        print("=" * 30)
        
        return {
            'queue_size': queue_size,
            'request_fingerprints': request_fingerprints,
            'item_fingerprints': item_fingerprints
        }
        
    except Exception as e:
        print(f"获取最终统计失败: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'final':
        # 显示最终统计
        get_final_stats()
    else:
        # 实时监控
        monitor_distributed_crawling()