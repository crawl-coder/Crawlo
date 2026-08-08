#!/usr/bin/env python
"""测试 event.py 中 asyncio.timeout() → wait_for() 的修复

验证：
1. wait_for 在普通 Task 上下文中正常工作
2. wait_for 在 fire-and-forget（回调/回调链）中不崩溃
3. 超时行为与旧版 timeout() 一致
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.event import Subscriber, CrawlerEvent


async def slow_receiver(_item=None, _spider=None):
    """模拟慢速订阅者"""
    await asyncio.sleep(10)
    return "slow_ok"


async def fast_receiver(_item=None, _spider=None):
    """模拟快速订阅者"""
    return "fast_ok"


async def error_receiver(_item=None, _spider=None):
    """模拟异常订阅者"""
    raise ValueError("业务异常")


async def test_notify_fast():
    """测试 notify 快速回调正常返回"""
    sub = Subscriber(timeout=5.0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    assert len(results) == 1
    assert results[0] == "fast_ok"
    nr = sub._last_notify_result
    assert nr is not None and not nr.has_errors
    print("[PASS] notify with fast receiver")


async def test_notify_timeout():
    """测试 notify 超时"""
    sub = Subscriber(timeout=1.0)
    sub.subscribe(slow_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    nr = sub._last_notify_result
    assert nr is not None and nr.has_errors
    error_name, error = nr.errors[0]
    assert isinstance(error, asyncio.TimeoutError), f"Expected TimeoutError, got {type(error)}"
    print(f"[PASS] notify timeout: {error_name} -> {error}")


async def test_notify_error():
    """测试 notify 遇到业务异常"""
    sub = Subscriber(timeout=5.0)
    sub.subscribe(error_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    nr = sub._last_notify_result
    assert nr is not None and nr.has_errors
    error_name, error = nr.errors[0]
    assert isinstance(error, ValueError)
    print(f"[PASS] notify error propagation: {error_name} -> {error}")


async def test_notify_multiple():
    """测试多个订阅者混合"""
    sub = Subscriber(timeout=3.0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL, priority=10)
    sub.subscribe(slow_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL, priority=20)

    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    assert len(results) == 2
    nr = sub._last_notify_result
    assert nr is not None and nr.has_errors
    assert results[0] == "fast_ok"
    print("[PASS] notify with multiple receivers (mixed fast + slow)")


async def test_notify_fire_and_forget():
    """模拟 fire-and-forget 场景：无 await 的背景 Task"""
    sub = Subscriber(timeout=5.0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    # 不 await，模拟 fire-and-forget
    task = asyncio.create_task(sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None))
    await asyncio.sleep(0.05)
    results = await task
    assert results == ["fast_ok"]
    print("[PASS] notify fire-and-forget: no crash")


async def test_notify_fire_and_forget_chain():
    """模拟链式 fire-and-forget"""
    sub = Subscriber(timeout=5.0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    # 模拟 20 个 item 并发处理
    tasks = []
    for i in range(20):
        t = asyncio.create_task(
            sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, f"item_{i}", None)
        )
        tasks.append(t)

    results_list = await asyncio.gather(*tasks)
    assert len(results_list) == 20
    for results in results_list:
        assert results == ["fast_ok"]
    print("[PASS] notify 20 concurrent fire-and-forget: no crash")


async def test_timeout_zero():
    """测试 timeout=0 时跳过超时逻辑"""
    sub = Subscriber(timeout=0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.ITEM_SUCCESSFUL)

    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    assert results == ["fast_ok"]
    print("[PASS] notify with timeout=0")


async def test_no_subscriber():
    """测试无订阅者"""
    sub = Subscriber(timeout=5.0)
    results = await sub.notify(CrawlerEvent.ITEM_SUCCESSFUL, None, None)
    assert results == []
    nr = sub._last_notify_result
    assert nr is not None and not nr.has_errors
    print("[PASS] notify with no subscribers")


async def test_request_scheduled():
    """测试 request_scheduled 事件"""
    sub = Subscriber(timeout=5.0)
    sub.subscribe(fast_receiver, event=CrawlerEvent.REQUEST_SCHEDULED)

    results = await sub.notify(CrawlerEvent.REQUEST_SCHEDULED, None, None)
    assert results == ["fast_ok"]
    print("[PASS] notify request_scheduled event")


async def main():
    print(f"Python {sys.version}")
    print("=" * 60)
    print(f"Testing asyncio.wait_for() fix ({'asyncio.timeout()' if hasattr(asyncio, 'timeout') else 'no timeout()'} available)")
    print("=" * 60)

    tests = [
        test_no_subscriber,
        test_notify_fast,
        test_notify_timeout,
        test_notify_error,
        test_notify_multiple,
        test_notify_fire_and_forget,
        test_notify_fire_and_forget_chain,
        test_timeout_zero,
        test_request_scheduled,
    ]

    passed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{len(tests)} passed")
    print(f"{'=' * 60}")
    return passed == len(tests)


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
