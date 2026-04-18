#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
背压功能有效性测试

验证背压系统是否真正能够：
1. 在队列使用率达到阈值时触发延迟
2. 延迟随使用率增加而增加
3. 背压状态正确反映系统负载
"""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.queue.memory_queue import MemoryQueue
from crawlo.backpressure import BackpressureController, QueueSizeStrategy
from crawlo.network.request import Request


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_header(title):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{title.center(70)}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.RESET}")


async def test_backpressure_triggers_correctly():
    """测试背压是否正确触发"""
    print_header("测试1: 背压触发机制")
    
    # 创建小队列以便快速达到阈值
    queue = MemoryQueue(
        max_size=100,
        backpressure_enabled=True,
        backpressure_threshold=0.8
    )
    await queue.open()
    
    # 填充队列到不同使用率级别
    test_cases = [
        (50, "50%使用率", False, 0),   # 低于阈值，不应触发
        (85, "85%使用率", True, 0.1),  # 超过阈值，应触发
        (95, "95%使用率", True, 0.5),  # 高使用率，应触发更高延迟
    ]
    
    controller = BackpressureController(strategy=QueueSizeStrategy())
    
    for count, label, should_trigger, min_delay in test_cases:
        # 清空队列
        await queue.clear()
        
        # 填充到指定数量
        for i in range(count):
            await queue.put(Request(url=f"http://test.com/{i}"))
        
        size = await queue.size()
        utilization = size / queue.max_size
        
        # 检查背压是否应该触发
        should_apply = await controller.should_apply(queue)
        delay = await controller.calculate_delay(queue)
        
        print_info(f"{label}: 大小={size}, 使用率={utilization:.0%}")
        print_info(f"  背压应触发: {should_trigger}, 实际: {should_apply}")
        print_info(f"  延迟: {delay:.3f}s (期望最小: {min_delay}s)")
        
        if should_trigger != should_apply:
            print_error(f"背压触发状态不匹配！")
            await queue.close()
            return False
        
        if should_trigger and delay < min_delay:
            print_error(f"延迟不足！期望至少 {min_delay}s，实际 {delay:.3f}s")
            await queue.close()
            return False
    
    await queue.close()
    print_success("背压触发机制测试通过")
    return True


async def test_backpressure_delay_increases_with_utilization():
    """测试延迟是否随使用率增加而增加"""
    print_header("测试2: 延迟递增性")
    
    queue = MemoryQueue(
        max_size=100,
        backpressure_enabled=True,
        backpressure_threshold=0.8
    )
    await queue.open()
    
    controller = BackpressureController(strategy=QueueSizeStrategy())
    
    delays = []
    utilization_levels = [0.80, 0.85, 0.90, 0.95, 0.99]
    
    for util in utilization_levels:
        await queue.clear()
        count = int(queue.max_size * util)
        
        for i in range(count):
            await queue.put(Request(url=f"http://test.com/{i}"))
        
        delay = await controller.calculate_delay(queue)
        delays.append((util, delay))
        print_info(f"使用率 {util:.0%}: 延迟 {delay:.3f}s")
    
    # 验证延迟递增
    increasing = all(delays[i][1] <= delays[i+1][1] for i in range(len(delays)-1))
    
    if not increasing:
        print_error("延迟未随使用率单调递增！")
        await queue.close()
        return False
    
    await queue.close()
    print_success("延迟递增性测试通过")
    return True


async def test_backpressure_reduces_request_rate():
    """测试背压是否真正降低请求处理速率"""
    print_header("测试3: 背压对请求速率的影响")
    
    # 测试无背压时的速率
    queue_no_bp = MemoryQueue(
        max_size=1000,
        backpressure_enabled=False
    )
    await queue_no_bp.open()
    
    start_time = time.time()
    for i in range(100):
        await queue_no_bp.put(Request(url=f"http://test.com/{i}"))
    no_bp_time = time.time() - start_time
    
    await queue_no_bp.close()
    
    # 测试有背压时的速率（高负载）
    queue_with_bp = MemoryQueue(
        max_size=100,
        backpressure_enabled=True,
        backpressure_threshold=0.8
    )
    await queue_with_bp.open()
    
    # 先填充到高使用率
    for i in range(90):
        await queue_with_bp.put(Request(url=f"http://test.com/{i}"))
    
    controller = BackpressureController(strategy=QueueSizeStrategy())
    
    start_time = time.time()
    for i in range(10):
        # 检查背压并应用延迟
        if await controller.should_apply(queue_with_bp):
            delay = await controller.calculate_delay(queue_with_bp)
            await asyncio.sleep(delay)
        await queue_with_bp.put(Request(url=f"http://test.com/{100+i}"))
    with_bp_time = time.time() - start_time
    
    await queue_with_bp.close()
    
    print_info(f"无背压时100次入队耗时: {no_bp_time:.3f}s")
    print_info(f"有背压时10次入队耗时: {with_bp_time:.3f}s")
    
    # 有背压时应该明显更慢
    if with_bp_time < no_bp_time / 5:  # 至少应该有显著差异
        print_error("背压未显著降低请求速率！")
        return False
    
    print_success("背压对请求速率的影响测试通过")
    return True


async def test_backpressure_state_consistency():
    """测试背压状态一致性"""
    print_header("测试4: 背压状态一致性")
    
    queue = MemoryQueue(
        max_size=100,
        backpressure_enabled=True,
        backpressure_threshold=0.8
    )
    await queue.open()
    
    controller = BackpressureController(strategy=QueueSizeStrategy())
    
    # 填充队列到触发背压
    for i in range(90):
        await queue.put(Request(url=f"http://test.com/{i}"))
    
    # 多次检查状态一致性
    states = []
    for _ in range(5):
        should_apply = await controller.should_apply(queue)
        delay = await controller.calculate_delay(queue)
        stats = controller.get_stats()
        states.append((should_apply, delay, stats))
        await asyncio.sleep(0.01)  # 短暂间隔
    
    # 验证状态一致性
    first_state = states[0]
    consistent = all(
        s[0] == first_state[0] and  # should_apply 应该一致
        abs(s[1] - first_state[1]) < 0.001  # delay 应该几乎相同
        for s in states
    )
    
    if not consistent:
        print_error("背压状态不一致！")
        for i, s in enumerate(states):
            print_info(f"  检查 {i+1}: should_apply={s[0]}, delay={s[1]:.3f}s")
        await queue.close()
        return False
    
    await queue.close()
    print_success("背压状态一致性测试通过")
    return True


async def run_all_tests():
    """运行所有测试"""
    print_header("背压功能有效性测试")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "背压触发机制": await test_backpressure_triggers_correctly(),
        "延迟递增性": await test_backpressure_delay_increases_with_utilization(),
        "请求速率影响": await test_backpressure_reduces_request_rate(),
        "状态一致性": await test_backpressure_state_consistency(),
    }
    
    print_header("测试总结")
    
    passed = sum(1 for r in results.values() if r)
    failed = sum(1 for r in results.values() if not r)
    
    for name, result in results.items():
        if result:
            print_success(f"{name}: 通过")
        else:
            print_error(f"{name}: 失败")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print_success("所有背压功能测试通过！背压系统工作正常。")
        return 0
    else:
        print_error(f"有 {failed} 个测试失败，背压功能可能存在问题。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
