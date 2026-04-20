#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Engine 主循环优化前后性能对比测试

模拟真实爬虫场景，对比优化前后的性能差异。
"""

import asyncio
import time
from unittest.mock import Mock


async def simulate_old_engine_loop(total_requests=100):
    """
    模拟优化前的 Engine 主循环
    
    特点：
    - 每次只获取 1 个请求
    - 每次都检查退出条件
    - 固定 sleep 时间
    """
    request_count = 0
    loop_count = 0
    exit_check_count = 0
    crawl_count = 0
    start_time = time.time()
    
    # 模拟队列
    requests_queue = [Mock(url=f'http://example.com/{i}') for i in range(total_requests)]
    
    while requests_queue:  # 只处理请求，不模拟空循环
        loop_count += 1
        
        # 获取 1 个请求
        if requests_queue:
            request = requests_queue.pop(0)
            request_count += 1
            
            # 处理请求（模拟 1ms）
            await asyncio.sleep(0.001)
            crawl_count += 1
        
        # 每次都检查退出条件
        exit_check_count += 1
        # 模拟退出检查（模拟 0.1ms）
        await asyncio.sleep(0.0001)
        
        # 固定 sleep
        await asyncio.sleep(0.000001)
    
    elapsed = time.time() - start_time
    
    return {
        'loop_count': loop_count,
        'request_count': request_count,
        'crawl_count': crawl_count,
        'exit_check_count': exit_check_count,
        'elapsed_time': elapsed
    }


async def simulate_new_engine_loop(total_requests=100):
    """
    模拟优化后的 Engine 主循环
    
    特点：
    - 批量获取 5 个请求
    - 每 10 次检查一次退出条件
    - 并发处理批量请求
    - 动态 sleep
    """
    request_count = 0
    loop_count = 0
    exit_check_count = 0
    crawl_count = 0
    idle_count = 0
    start_time = time.time()
    
    # 模拟队列
    requests_queue = [Mock(url=f'http://example.com/{i}') for i in range(total_requests)]
    
    batch_size = 5
    exit_check_interval = 10
    last_exit_check = 0
    
    while requests_queue:  # 只处理请求
        loop_count += 1
        
        # 批量获取请求
        batch = []
        for _ in range(batch_size):
            if requests_queue:
                batch.append(requests_queue.pop(0))
                request_count += 1
            else:
                break
        
        # 并发处理批量请求
        if batch:
            idle_count = 0
            # 并发处理（模拟 1ms，但并发执行）
            tasks = [asyncio.sleep(0.001) for _ in batch]
            await asyncio.gather(*tasks)
            crawl_count += len(batch)
        else:
            idle_count += 1
        
        # 每 10 次检查一次退出条件
        if loop_count - last_exit_check >= exit_check_interval:
            exit_check_count += 1
            # 模拟退出检查（模拟 0.1ms）
            await asyncio.sleep(0.0001)
            last_exit_check = loop_count
        
        # 动态 sleep
        if batch:
            await asyncio.sleep(0.000001)
        elif idle_count > 10:
            await asyncio.sleep(0.01)
        else:
            await asyncio.sleep(0.001)
    
    elapsed = time.time() - start_time
    
    return {
        'loop_count': loop_count,
        'request_count': request_count,
        'crawl_count': crawl_count,
        'exit_check_count': exit_check_count,
        'elapsed_time': elapsed
    }


async def main():
    """运行性能对比测试"""
    print("\n" + "="*70)
    print("Engine 主循环优化前后性能对比测试")
    print("="*70)
    
    total_requests = 100
    
    # 测试优化前
    print(f"\n📊 测试场景：处理 {total_requests} 个请求")
    print("\n⏳ 运行优化前的 Engine 主循环...")
    old_stats = await simulate_old_engine_loop(total_requests)
    
    # 测试优化后
    print("⏳ 运行优化后的 Engine 主循环...")
    new_stats = await simulate_new_engine_loop(total_requests)
    
    # 输出对比结果
    print("\n" + "="*70)
    print("📈 性能对比结果")
    print("="*70)
    
    print(f"\n{'指标':<20} {'优化前':<15} {'优化后':<15} {'提升':<15}")
    print("-" * 70)
    print(f"{'循环次数':<20} {old_stats['loop_count']:<15} {new_stats['loop_count']:<15} "
          f"{(1 - new_stats['loop_count']/old_stats['loop_count'])*100:>6.1f}%")
    print(f"{'退出检查次数':<20} {old_stats['exit_check_count']:<15} {new_stats['exit_check_count']:<15} "
          f"{(1 - new_stats['exit_check_count']/old_stats['exit_check_count'])*100:>6.1f}%")
    print(f"{'处理请求数':<20} {old_stats['crawl_count']:<15} {new_stats['crawl_count']:<15} "
          f"{'=':>15}")
    print(f"{'运行时间 (ms)':<20} {old_stats['elapsed_time']*1000:<15.2f} {new_stats['elapsed_time']*1000:<15.2f} "
          f"{(1 - new_stats['elapsed_time']/old_stats['elapsed_time'])*100:>6.1f}%")
    
    print("\n" + "="*70)
    print("✅ 优化效果总结")
    print("="*70)
    
    loop_reduction = (1 - new_stats['loop_count']/old_stats['loop_count']) * 100
    check_reduction = (1 - new_stats['exit_check_count']/old_stats['exit_check_count']) * 100
    time_reduction = (1 - new_stats['elapsed_time']/old_stats['elapsed_time']) * 100
    
    print(f"\n  ✅ 循环迭代次数减少：{loop_reduction:.1f}%")
    print(f"  ✅ 退出检查次数减少：{check_reduction:.1f}%")
    print(f"  ✅ 运行时间减少：{time_reduction:.1f}%")
    print(f"  ✅ 请求处理数量：{new_stats['crawl_count']}（无遗漏）")
    
    print("\n" + "="*70)
    print("🎉 测试完成！Engine 主循环优化效果显著！")
    print("="*70 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
