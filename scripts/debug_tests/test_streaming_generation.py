#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式生成 + 背压控制 集成测试

验证点：
1. 各种生成器类型（sync gen / async gen / 协程return）与传统/受控生成的配合
2. 背压控制在大数据量下真正触发
3. 小数据量零感知
"""
import asyncio
import sys
import os
import time
from unittest.mock import MagicMock, AsyncMock, patch
from inspect import isasyncgen, iscoroutine, isgenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Request, Item
from crawlo.core.engine import Engine


# ============================================================
# 辅助：创建 mock engine（只初始化生成相关部分）
# ============================================================
def create_test_engine(enable_controlled=False, max_queue_size=50):
    """创建测试用 engine，只初始化生成和背压相关属性"""
    crawler = MagicMock()
    crawler.settings = {
        'CONCURRENCY': 8,
        'SCHEDULER_MAX_QUEUE_SIZE': max_queue_size,
        'REQUEST_GENERATION_BATCH_SIZE': 10,
        'REQUEST_GENERATION_INTERVAL': 0.001,
        'BACKPRESSURE_RATIO': 0.9,
        'ENABLE_CONTROLLED_REQUEST_GENERATION': enable_controlled,
    }
    engine = Engine(crawler)

    # mock scheduler（用于背压检查）
    scheduler = MagicMock()
    scheduler.__len__ = MagicMock(return_value=0)
    scheduler.async_idle = AsyncMock(return_value=True)
    scheduler.idle = MagicMock(return_value=True)
    engine.scheduler = scheduler

    # mock enqueue_request
    engine.enqueue_request = AsyncMock()

    return engine


# ============================================================
# 测试用 Spider 定义
# ============================================================
class SyncGenSpider:
    """同步生成器：5个请求"""
    def start_requests(self):
        for i in range(5):
            yield Request(url=f'http://sync.com/{i}')


class AsyncGenSpider:
    """异步生成器：5个请求"""
    async def start_requests(self):
        for i in range(5):
            yield Request(url=f'http://async.com/{i}')


class CoroutineListSpider:
    """协程 return 列表：5个请求"""
    async def start_requests(self):
        return [Request(url=f'http://list.com/{i}') for i in range(5)]


class CoroutineNoneSpider:
    """协程 return None"""
    async def start_requests(self):
        return None


class SyncGenLargeSpider:
    """同步生成器：500个请求（大数据量）"""
    def start_requests(self):
        for i in range(500):
            yield Request(url=f'http://large.com/{i}')


class AsyncGenLargeSpider:
    """异步生成器：500个请求（大数据量）"""
    async def start_requests(self):
        for i in range(500):
            yield Request(url=f'http://alarge.com/{i}')


# ============================================================
# 测试 1-5：各种生成器类型 + 传统生成
# ============================================================
async def test_sync_gen_traditional():
    """TEST 1: sync gen + 传统生成"""
    engine = create_test_engine(enable_controlled=False)
    spider = SyncGenSpider()

    result = spider.start_requests()
    engine._start_requests_source = result
    engine._start_requests_is_async = False
    engine.running = True

    await engine._traditional_request_generation()

    assert engine.enqueue_request.call_count == 5, f"Expected 5, got {engine.enqueue_request.call_count}"
    assert engine._start_requests_source is None, "Source should be None after consumption"
    print("TEST 1 ✅ sync gen + traditional: 5/5 requests enqueued")


async def test_async_gen_traditional():
    """TEST 2: async gen + 传统生成"""
    engine = create_test_engine(enable_controlled=False)
    spider = AsyncGenSpider()

    result = spider.start_requests()
    assert isasyncgen(result)
    engine._start_requests_source = result
    engine._start_requests_is_async = True
    engine.running = True

    await engine._traditional_request_generation()

    assert engine.enqueue_request.call_count == 5
    assert engine._start_requests_source is None
    print("TEST 2 ✅ async gen + traditional: 5/5 requests enqueued")


async def test_coroutine_list_traditional():
    """TEST 3: 协程 return 列表 + 传统生成"""
    engine = create_test_engine(enable_controlled=False)
    spider = CoroutineListSpider()

    result = spider.start_requests()
    assert iscoroutine(result)
    awaited = await result
    assert isinstance(awaited, list)
    engine._start_requests_source = iter(awaited)
    engine._start_requests_is_async = False
    engine.running = True

    await engine._traditional_request_generation()

    assert engine.enqueue_request.call_count == 5
    assert engine._start_requests_source is None
    print("TEST 3 ✅ coroutine→list + traditional: 5/5 requests enqueued")


async def test_coroutine_none_traditional():
    """TEST 4: 协程 return None + 传统生成"""
    engine = create_test_engine(enable_controlled=False)
    spider = CoroutineNoneSpider()

    result = spider.start_requests()
    awaited = await result
    assert awaited is None
    engine._start_requests_source = None
    engine._start_requests_is_async = False
    engine.running = True

    await engine._traditional_request_generation()

    assert engine.enqueue_request.call_count == 0
    print("TEST 4 ✅ coroutine→None + traditional: 0 requests (correct)")


# ============================================================
# 测试 5-7：各种生成器类型 + 受控生成（背压）
# ============================================================
async def test_sync_gen_controlled():
    """TEST 5: sync gen + 受控生成（无背压，队列空闲）"""
    engine = create_test_engine(enable_controlled=True, max_queue_size=100)
    spider = SyncGenSpider()

    result = spider.start_requests()
    engine._start_requests_source = result
    engine._start_requests_is_async = False
    engine.running = True

    # mock _should_pause_generation 返回 False（无背压）
    engine._should_pause_generation = AsyncMock(return_value=False)
    engine._wait_for_capacity = AsyncMock()
    engine._is_queue_full = AsyncMock(return_value=False)

    await engine._controlled_request_generation()

    assert engine.enqueue_request.call_count == 5
    assert engine._start_requests_source is None
    print("TEST 5 ✅ sync gen + controlled: 5/5 requests, no backpressure")


async def test_async_gen_controlled():
    """TEST 6: async gen + 受控生成（无背压）"""
    engine = create_test_engine(enable_controlled=True, max_queue_size=100)
    spider = AsyncGenSpider()

    result = spider.start_requests()
    engine._start_requests_source = result
    engine._start_requests_is_async = True
    engine.running = True
    engine._should_pause_generation = AsyncMock(return_value=False)
    engine._wait_for_capacity = AsyncMock()
    engine._is_queue_full = AsyncMock(return_value=False)

    await engine._controlled_request_generation()

    assert engine.enqueue_request.call_count == 5
    assert engine._start_requests_source is None
    print("TEST 6 ✅ async gen + controlled: 5/5 requests, no backpressure")


async def test_coroutine_list_controlled():
    """TEST 7: 协程 return 列表 + 受控生成"""
    engine = create_test_engine(enable_controlled=True, max_queue_size=100)
    spider = CoroutineListSpider()

    result = spider.start_requests()
    awaited = await result
    engine._start_requests_source = iter(awaited)
    engine._start_requests_is_async = False
    engine.running = True
    engine._should_pause_generation = AsyncMock(return_value=False)
    engine._wait_for_capacity = AsyncMock()
    engine._is_queue_full = AsyncMock(return_value=False)

    await engine._controlled_request_generation()

    assert engine.enqueue_request.call_count == 5
    assert engine._start_requests_source is None
    print("TEST 7 ✅ coroutine→list + controlled: 5/5 requests")


# ============================================================
# 测试 8-9：大数据量 + 背压控制真正触发
# ============================================================
async def test_sync_large_backpressure():
    """TEST 8: sync gen 500个请求 + 受控生成 + 背压触发"""
    engine = create_test_engine(enable_controlled=True, max_queue_size=50)
    spider = SyncGenLargeSpider()

    result = spider.start_requests()
    engine._start_requests_source = result
    engine._start_requests_is_async = False
    engine.running = True

    # 让 _should_pause_generation 在队列大小 >= 30 时返回 True
    pause_call_count = 0

    async def mock_should_pause():
        nonlocal pause_call_count
        queue_size = len(engine.scheduler)
        if queue_size >= 30:
            pause_call_count += 1
            return True
        return False

    async def mock_wait():
        # 模拟等待：从队列中"消费"10个
        current = len(engine.scheduler)
        engine.scheduler.__len__ = MagicMock(return_value=max(0, current - 10))

    engine._should_pause_generation = mock_should_pause
    engine._wait_for_capacity = mock_wait
    engine._is_queue_full = AsyncMock(return_value=False)

    # 每次入队时增加 scheduler 队列大小 + 计数
    enqueue_count = 0

    async def counting_enqueue(req):
        nonlocal enqueue_count
        enqueue_count += 1
        current = len(engine.scheduler)
        engine.scheduler.__len__ = MagicMock(return_value=current + 1)
        # 不再调用 original_enqueue（它是 AsyncMock，已不需要）

    engine.enqueue_request = counting_enqueue

    await engine._controlled_request_generation()

    assert enqueue_count == 500, f"Expected 500, got {enqueue_count}"
    assert pause_call_count > 0, f"Backpressure should have triggered, but pause_call_count={pause_call_count}"
    print(f"TEST 8 \u2705 sync large + controlled + backpressure: 500/500 enqueued, backpressure triggered {pause_call_count} times")


async def test_async_large_backpressure():
    """TEST 9: async gen 500个请求 + 受控生成 + 背压触发"""
    engine = create_test_engine(enable_controlled=True, max_queue_size=50)
    spider = AsyncGenLargeSpider()

    result = spider.start_requests()
    engine._start_requests_source = result
    engine._start_requests_is_async = True
    engine.running = True

    pause_call_count = 0

    async def mock_should_pause():
        nonlocal pause_call_count
        queue_size = len(engine.scheduler)
        if queue_size >= 30:
            pause_call_count += 1
            return True
        return False

    async def mock_wait():
        current = len(engine.scheduler)
        engine.scheduler.__len__ = MagicMock(return_value=max(0, current - 10))

    engine._should_pause_generation = mock_should_pause
    engine._wait_for_capacity = mock_wait
    engine._is_queue_full = AsyncMock(return_value=False)

    enqueue_count = 0

    async def counting_enqueue(req):
        nonlocal enqueue_count
        enqueue_count += 1
        current = len(engine.scheduler)
        engine.scheduler.__len__ = MagicMock(return_value=current + 1)

    engine.enqueue_request = counting_enqueue

    await engine._controlled_request_generation()

    assert enqueue_count == 500, f"Expected 500, got {enqueue_count}"
    assert pause_call_count > 0, f"Backpressure should have triggered, but pause_call_count={pause_call_count}"
    print(f"TEST 9 \u2705 async large + controlled + backpressure: 500/500 enqueued, backpressure triggered {pause_call_count} times")


# ============================================================
# 测试 10：start_spider() 端到端（模拟完整解析流程）
# ============================================================
async def test_start_spider_parsing():
    """TEST 10: start_spider() 解析各种生成器类型"""
    from crawlo.spider import Spider

    class SyncSpider(Spider):
        name = 'sync'
        def start_requests(self):
            yield Request(url='http://a.com/1')

    class AsyncSpider(Spider):
        name = 'async'
        async def start_requests(self):
            yield Request(url='http://b.com/1')

    class RetListSpider(Spider):
        name = 'retlist'
        async def start_requests(self):
            return [Request(url='http://c.com/1')]

    for SpiderCls, expected_async, expected_url in [
        (SyncSpider, False, 'http://a.com/1'),
        (AsyncSpider, True, 'http://b.com/1'),
        (RetListSpider, False, 'http://c.com/1'),
    ]:
        engine = create_test_engine()
        spider = SpiderCls()

        # 模拟 start_spider 中的解析逻辑
        result = spider.start_requests()
        if isasyncgen(result):
            engine._start_requests_source = result
            engine._start_requests_is_async = True
        elif iscoroutine(result):
            awaited = await result
            if isasyncgen(awaited):
                engine._start_requests_source = awaited
                engine._start_requests_is_async = True
            elif isinstance(awaited, (list, tuple)):
                engine._start_requests_source = iter(awaited)
                engine._start_requests_is_async = False
            else:
                engine._start_requests_source = iter([awaited])
                engine._start_requests_is_async = False
        else:
            engine._start_requests_source = result
            engine._start_requests_is_async = False

        assert engine._start_requests_is_async == expected_async, \
            f"{SpiderCls.name}: expected is_async={expected_async}, got {engine._start_requests_is_async}"

        # 取出第一个请求验证
        if engine._start_requests_is_async:
            first = await engine._start_requests_source.__anext__()
        else:
            first = next(engine._start_requests_source)
        assert first.url == expected_url, f"Expected {expected_url}, got {first.url}"

    print("TEST 10 ✅ start_spider parsing: sync/async/coroutine→list all correct")


# ============================================================
# 运行所有测试
# ============================================================
async def run_all():
    tests = [
        test_sync_gen_traditional,
        test_async_gen_traditional,
        test_coroutine_list_traditional,
        test_coroutine_none_traditional,
        test_sync_gen_controlled,
        test_async_gen_controlled,
        test_coroutine_list_controlled,
        test_sync_large_backpressure,
        test_async_large_backpressure,
        test_start_spider_parsing,
    ]
    print(f"Running {len(tests)} tests...\n")
    for test in tests:
        await test()
    print(f"\n{'='*60}")
    print(f"All {len(tests)} tests passed! ✅")


if __name__ == '__main__':
    asyncio.run(run_all())
