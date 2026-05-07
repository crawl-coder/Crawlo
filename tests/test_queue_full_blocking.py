#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
测试队列满时的阻塞等待机制

验证：当队列满时，Scheduler 应该阻塞等待而不是丢弃请求
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from crawlo.core.scheduler import Scheduler
from crawlo import Request


class MockQueueManager:
    """模拟队列管理器"""
    
    def __init__(self, max_size=10):
        self.max_size = max_size
        self._size = 0
        self._requests = []
    
    async def size(self):
        return self._size
    
    async def put(self, request, priority=0):
        """模拟入队：如果队列满则拒绝"""
        if self._size >= self.max_size:
            return False
        
        self._requests.append((request, priority))
        self._size += 1
        return True
    
    async def consume(self, count=1):
        """模拟消费请求（释放队列空间）"""
        consumed = min(count, self._size)
        self._size -= consumed
        self._requests = self._requests[consumed:]
        return consumed


class MockDupeFilter:
    """模拟去重过滤器"""
    
    def __init__(self):
        self.seen = set()
    
    async def requested(self, request):
        if request.url in self.seen:
            return True
        self.seen.add(request.url)
        return False
    
    def log_stats(self, request):
        pass


@pytest.mark.asyncio
async def test_queue_full_blocks_and_retries():
    """测试队列满时阻塞等待，直到有空间后重试成功"""
    
    # 创建 Scheduler
    crawler = MagicMock()
    crawler.settings = {}
    crawler.spider = None
    
    scheduler = Scheduler(
        crawler=crawler,
        dupe_filter=MockDupeFilter(),
        stats=None,
        priority=0
    )
    
    # 设置队列管理器（最大容量 5）
    queue_mgr = MockQueueManager(max_size=5)
    scheduler.queue_manager = queue_mgr
    
    # 1. 填满队列（5 个请求）
    for i in range(5):
        req = Request(url=f"http://example.com/{i}")
        success = await scheduler.enqueue_request(req)
        assert success is True
    
    assert await queue_mgr.size() == 5
    
    # 2. 启动一个后台任务：2 秒后消费 3 个请求（释放空间）
    async def delayed_consume():
        await asyncio.sleep(2)
        await queue_mgr.consume(3)
    
    consume_task = asyncio.create_task(delayed_consume())
    
    # 3. 尝试入队第 6 个请求（应该阻塞等待，直到 2 秒后有空间）
    start_time = asyncio.get_event_loop().time()
    
    req6 = Request(url="http://example.com/6")
    success = await scheduler.enqueue_request(req6)
    
    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time
    
    # 验证：
    # - 入队成功
    assert success is True
    # - 阻塞等待了约 2 秒（允许误差 0.5s）
    assert elapsed >= 1.5, f"Expected to wait ~2s, but only waited {elapsed:.2f}s"
    assert elapsed < 3.0, f"Waited too long: {elapsed:.2f}s"
    # - 队列大小恢复到 5（3个被消费 + 1个新入队 = 3）
    assert await queue_mgr.size() == 3
    
    await consume_task
    
    print(f"✅ 队列满阻塞等待测试通过：等待了 {elapsed:.2f}s 后成功入队")


@pytest.mark.asyncio
async def test_queue_full_timeout_drops_request():
    """测试队列长时间满时，超过最大重试次数后丢弃请求"""
    
    crawler = MagicMock()
    crawler.settings = {}
    crawler.spider = None
    
    scheduler = Scheduler(
        crawler=crawler,
        dupe_filter=MockDupeFilter(),
        stats=None,
        priority=0
    )
    
    # 队列满了且不消费
    queue_mgr = MockQueueManager(max_size=5)
    scheduler.queue_manager = queue_mgr
    
    # 填满队列
    for i in range(5):
        req = Request(url=f"http://timeout.com/{i}")
        await scheduler.enqueue_request(req)
    
    # 尝试入队（应该等待 100 次 * 0.5s = 50s 后超时）
    # 为了测试速度，我们 mock asyncio.sleep 立即返回
    sleep_count = 0
    
    async def mock_sleep(delay):
        nonlocal sleep_count
        sleep_count += 1
        # 模拟快速等待（不真正sleep）
    
    with patch('crawlo.core.scheduler.asyncio.sleep', mock_sleep):
        req_timeout = Request(url="http://timeout.com/fail")
        success = await scheduler.enqueue_request(req_timeout)
        
        # 验证：
        # - 入队失败
        assert success is False
        # - 重试了 100 次
        assert sleep_count == 100, f"Expected 100 retries, got {sleep_count}"
    
    print("✅ 队列满超时丢弃测试通过：100 次重试后正确丢弃请求")


@pytest.mark.asyncio
async def test_queue_partial_full_with_backpressure():
    """测试队列未完全满时正常入队（不受阻塞影响）"""
    
    crawler = MagicMock()
    crawler.settings = {}
    crawler.spider = None
    
    scheduler = Scheduler(
        crawler=crawler,
        dupe_filter=MockDupeFilter(),
        stats=None,
        priority=0
    )
    
    queue_mgr = MockQueueManager(max_size=10)
    scheduler.queue_manager = queue_mgr
    
    # 填充一半（5/10）
    for i in range(5):
        req = Request(url=f"http://partial.com/{i}")
        await scheduler.enqueue_request(req)
    
    # 再入队 3 个（应该立即成功，不阻塞）
    start_time = asyncio.get_event_loop().time()
    
    for i in range(5, 8):
        req = Request(url=f"http://partial.com/{i}")
        success = await scheduler.enqueue_request(req)
        assert success is True
    
    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time
    
    # 验证：
    # - 没有阻塞（应该 < 0.1s）
    assert elapsed < 0.1, f"Should not block, but took {elapsed:.2f}s"
    # - 队列大小为 8
    assert await queue_mgr.size() == 8
    
    print(f"✅ 队列未满正常入队测试通过：耗时 {elapsed:.4f}s，无阻塞")


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("测试队列满时的阻塞等待机制")
    print("="*60 + "\n")
    
    try:
        await test_queue_full_blocks_and_retries()
    except Exception as e:
        print(f"❌ 测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        await test_queue_full_timeout_drops_request()
    except Exception as e:
        print(f"❌ 测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        await test_queue_partial_full_with_backpressure()
    except Exception as e:
        print(f"❌ 测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
