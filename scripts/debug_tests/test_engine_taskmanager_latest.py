#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Engine & TaskManager 最新修改测试
测试事件驱动、fire-and-forget 防护、并发派发等功能
"""
import os
import sys
import time
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import Mock, AsyncMock
from crawlo.core.engine import Engine
from crawlo.core.task_manager import TaskManager, DynamicSemaphore
from crawlo import Request, Response


def create_mock_crawler():
    """创建模拟 Crawler"""
    crawler = Mock()
    crawler.settings = {
        'CONCURRENCY': 5,
        'DOWNLOADER_TYPE': 'httpx',
        'SCHEDULER_MAX_QUEUE_SIZE': 10000,
        'BACKPRESSURE_RATIO': 0.9,
    }
    crawler.stats = Mock()
    crawler.stats.inc_value = Mock()
    crawler.subscriber = Mock()
    crawler.subscriber.notify = AsyncMock()
    return crawler


async def test_event_driven_latency():
    """测试 1：事件驱动响应延迟"""
    print("\n" + "=" * 60)
    print("测试 1：事件驱动响应延迟")
    print("=" * 60)
    
    crawler = create_mock_crawler()
    engine = Engine(crawler)
    
    # 测量事件响应时间
    latencies = []
    for i in range(10):
        start = time.time()
        engine._request_available.set()
        await engine._request_available.wait()
        engine._request_available.clear()
        latency = time.time() - start
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    print(f"  平均延迟: {avg_latency * 1000:.3f} ms")
    print(f"  最大延迟: {max_latency * 1000:.3f} ms")
    print(f"  最小延迟: {min(latencies) * 1000:.3f} ms")
    
    if avg_latency < 0.001:
        print("  ✅ PASS: 事件响应延迟 < 1ms")
    else:
        print(f"  ❌ FAIL: 事件响应延迟过高 {avg_latency * 1000:.3f}ms")
    
    return avg_latency < 0.001


async def test_background_task_tracking():
    """测试 2：Fire-and-Forget 任务追踪"""
    print("\n" + "=" * 60)
    print("测试 2：Fire-and-Forget 任务追踪")
    print("=" * 60)
    
    crawler = create_mock_crawler()
    engine = Engine(crawler)
    
    # 创建 50 个后台任务
    task_count = 50
    tasks = []
    for i in range(task_count):
        async def quick_task():
            await asyncio.sleep(0.01)
        
        task = engine._create_background_task(quick_task())
        tasks.append(task)
    
    # 等待所有任务完成
    await asyncio.gather(*tasks)
    await asyncio.sleep(0.1)  # 给 done_callback 时间执行
    
    remaining = len(engine._background_tasks)
    print(f"  创建任务数: {task_count}")
    print(f"  完成任务数: {task_count - remaining}")
    print(f"  残留任务数: {remaining}")
    
    if remaining == 0:
        print("  ✅ PASS: 无任务泄漏")
    else:
        print(f"  ❌ FAIL: 检测到 {remaining} 个任务泄漏")
    
    return remaining == 0


async def test_concurrent_dispatch():
    """测试 3：并发派发验证"""
    print("\n" + "=" * 60)
    print("测试 3：并发派发验证")
    print("=" * 60)
    
    crawler = create_mock_crawler()
    engine = Engine(crawler)
    engine.task_manager = TaskManager(total_concurrency=5)
    
    # 记录并发执行情况
    concurrent_count = 0
    max_concurrent = 0
    completed = 0
    
    async def mock_fetch(req):
        nonlocal concurrent_count, max_concurrent, completed
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.1)  # 模拟下载
        concurrent_count -= 1
        completed += 1
    
    # Mock downloader
    engine.downloader = Mock()
    engine.downloader.fetch = AsyncMock(side_effect=lambda req: mock_fetch(req))
    
    # Mock spider
    engine.spider = Mock()
    engine.spider.parse = Mock(return_value=None)
    
    # 派发 10 个请求
    print(f"  派发请求数: 10")
    print(f"  并发限制: 5")
    
    requests = [Request(url=f"http://test.com/{i}") for i in range(10)]
    for req in requests:
        # create_task_nowait 是 async 方法，需要 await
        await engine._crawl(req)
    
    # 等待完成
    await asyncio.sleep(2.0)
    
    print(f"  最大并发数: {max_concurrent}")
    print(f"  完成请求数: {completed}")
    
    if max_concurrent > 1:
        print(f"  ✅ PASS: 实现真正并发 (max={max_concurrent})")
    else:
        print(f"  ❌ FAIL: 未实现并发 (max={max_concurrent})")
    
    return max_concurrent > 1


async def test_task_manager_semaphore():
    """测试 4：TaskManager 信号量控制"""
    print("\n" + "=" * 60)
    print("测试 4：TaskManager 信号量控制")
    print("=" * 60)
    
    tm = TaskManager(total_concurrency=5)
    
    active = 0
    max_active = 0
    completed = 0
    
    async def task():
        nonlocal active, max_active, completed
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.1)
        active -= 1
        completed += 1
    
    # 创建 20 个任务
    print(f"  创建任务数: 20")
    print(f"  并发限制: 5")
    
    for _ in range(20):
        await tm.create_task_nowait(task())
    
    # 等待完成
    await asyncio.sleep(3.0)
    
    print(f"  最大并发数: {max_active}")
    print(f"  完成任务数: {completed}")
    
    if max_active <= 5:
        print(f"  ✅ PASS: 并发控制正常 (max={max_active})")
    else:
        print(f"  ❌ FAIL: 并发超过限制 (max={max_active})")
    
    return max_active <= 5


async def test_dynamic_semaphore_adjustment():
    """测试 5：动态信号量调整"""
    print("\n" + "=" * 60)
    print("测试 5：动态信号量调整")
    print("=" * 60)
    
    sem = DynamicSemaphore(initial_value=10)
    initial_value = sem._target_value
    
    # 测试 1：快速响应 -> 增加并发
    print(f"\n  [测试 1] 快速响应场景")
    # 需要先等待 > 1 秒才能调整
    sem._last_adjust_time = time.time() - 2.0
    
    for _ in range(10):
        sem.record_response_time(0.1)  # < 0.2s
    
    await sem.adjust_concurrency()
    fast_value = sem._target_value
    
    print(f"    初始并发: {initial_value}")
    print(f"    调整后并发: {fast_value}")
    
    if fast_value > initial_value:
        print(f"    ✅ PASS: 快速响应增加并发 (+{fast_value - initial_value})")
    else:
        print(f"    ❌ FAIL: 快速响应未增加并发")
    
    # 测试 2：慢速响应 -> 降低并发
    print(f"\n  [测试 2] 慢速响应场景")
    sem2 = DynamicSemaphore(initial_value=10)
    sem2._last_adjust_time = time.time() - 2.0  # 等待 > 1 秒
    
    for _ in range(10):
        sem2.record_response_time(2.0)  # > 1.0s
    
    await sem2.adjust_concurrency()
    slow_value = sem2._target_value
    
    print(f"    初始并发: {initial_value}")
    print(f"    调整后并发: {slow_value}")
    
    if slow_value < initial_value:
        print(f"    ✅ PASS: 慢速响应降低并发 (-{initial_value - slow_value})")
    else:
        print(f"    ❌ FAIL: 慢速响应未降低并发")
    
    return fast_value > initial_value and slow_value < initial_value


async def test_request_available_trigger():
    """测试 6：_request_available 事件触发"""
    print("\n" + "=" * 60)
    print("测试 6：_request_available 事件触发")
    print("=" * 60)
    
    crawler = create_mock_crawler()
    engine = Engine(crawler)
    
    # Mock scheduler
    engine.scheduler = Mock()
    engine.scheduler.enqueue_request = AsyncMock(return_value=True)
    
    # 测试事件是否被触发
    event_triggered = False
    
    async def wait_for_event():
        nonlocal event_triggered
        await engine._request_available.wait()
        event_triggered = True
    
    # 启动等待任务
    wait_task = asyncio.create_task(wait_for_event())
    
    # 模拟请求调度
    request = Request(url="http://test.com")
    await engine._schedule_request(request)
    
    # 等待事件触发
    await asyncio.wait_for(wait_task, timeout=1.0)
    
    if event_triggered:
        print("  ✅ PASS: _schedule_request 正确触发事件")
    else:
        print("  ❌ FAIL: 事件未触发")
    
    return event_triggered


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Engine & TaskManager 最新修改测试")
    print("=" * 60)
    
    tests = [
        ("事件驱动响应延迟", test_event_driven_latency),
        ("Fire-and-Forget 任务追踪", test_background_task_tracking),
        ("并发派发验证", test_concurrent_dispatch),
        ("TaskManager 信号量控制", test_task_manager_semaphore),
        ("动态信号量调整", test_dynamic_semaphore_adjustment),
        ("_request_available 事件触发", test_request_available_trigger),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
    
    return passed == total


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
