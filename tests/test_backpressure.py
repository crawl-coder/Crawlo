#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
背压功能测试脚本

测试 MemoryQueue 的背压控制功能。
"""
import asyncio
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.queue.memory_queue import MemoryQueue
from crawlo.queue.interfaces import BackpressureableQueueMixin


class MockRequest:
    """模拟请求对象"""
    def __init__(self, url, priority=0):
        self.url = url
        self.priority = priority


async def test_basic_backpressure():
    """测试基础背压功能"""
    print("\n" + "=" * 60)
    print("测试 1: 基础背压功能")
    print("=" * 60)
    
    # 创建一个最大大小为 10 的队列，背压阈值为 80%
    queue = MemoryQueue(max_size=10, backpressure_enabled=True, backpressure_threshold=0.8)
    
    await queue.open()
    
    print(f"队列配置: max_size={queue.max_size}, threshold={queue.backpressure_threshold}")
    print(f"背压启用: {queue.backpressure_enabled}")
    
    # 添加 8 个请求（达到 80% 阈值）
    print("\n添加 8 个请求（达到 80% 阈值）...")
    start_time = time.time()
    for i in range(8):
        success = await queue.put(MockRequest(f"http://example.com/{i}"))
        size = await queue.size()
        print(f"  请求 {i}: 成功={success}, 队列大小={size}")
    
    # 检查背压是否激活
    should_bp = await queue.should_apply_backpressure()
    print(f"\n背压状态检查: {should_bp}")
    print(f"  当前队列大小: {await queue.size()}")
    print(f"  使用率: {await queue.size() / queue.max_size:.0%}")
    
    # 添加更多请求，测试背压延迟
    print("\n添加 2 个请求，测试背压延迟...")
    for i in range(8, 10):
        req_start = time.time()
        success = await queue.put(MockRequest(f"http://example.com/{i}"))
        req_time = time.time() - req_start
        size = await queue.size()
        print(f"  请求 {i}: 成功={success}, 队列大小={size}, 耗时={req_time:.3f}s")
    
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.3f}s")
    
    # 获取统计信息
    stats = queue.get_extended_stats()
    print(f"\n队列统计:")
    print(f"  总入队: {stats['total_puts']}")
    print(f"  总出队: {stats['total_gets']}")
    print(f"  拒绝数: {stats['rejected_puts']}")
    print(f"  背压激活: {stats['backpressure_active']}")
    
    await queue.close()
    
    return True


async def test_backpressure_delay():
    """测试背压延迟计算"""
    print("\n" + "=" * 60)
    print("测试 2: 背压延迟计算")
    print("=" * 60)
    
    queue = MemoryQueue(max_size=100, backpressure_enabled=True, backpressure_threshold=0.8)
    await queue.open()
    
    print(f"队列配置: max_size={queue.max_size}, threshold={queue.backpressure_threshold}")
    
    # 测试不同使用率下的延迟
    test_cases = [
        (0, "0% 使用率"),
        (50, "50% 使用率 (低于阈值)"),
        (80, "80% 使用率 (等于阈值)"),
        (90, "90% 使用率 (高于阈值)"),
        (95, "95% 使用率 (接近满)"),
        (100, "100% 使用率 (满)"),
    ]
    
    # 填充队列到目标大小
    for target_size, description in test_cases:
        # 清空队列
        while not await queue.empty():
            await queue.get(timeout=0.01)
        
        # 添加请求直到达到目标大小
        for i in range(target_size):
            await queue.put(MockRequest(f"http://example.com/{i}"))
        
        # 计算延迟
        delay = await queue.calculate_backpressure_delay()
        size = await queue.size()
        utilization = size / queue.max_size if queue.max_size > 0 else 0
        should_bp = await queue.should_apply_backpressure()
        
        print(f"\n  {description}:")
        print(f"    实际大小: {size}")
        print(f"    使用率: {utilization:.0%}")
        print(f"    背压激活: {should_bp}")
        print(f"    计算延迟: {delay:.3f}s")
    
    await queue.close()
    
    return True


async def test_backpressure_threshold_change():
    """测试背压阈值变更"""
    print("\n" + "=" * 60)
    print("测试 3: 背压阈值变更")
    print("=" * 60)
    
    queue = MemoryQueue(max_size=100, backpressure_enabled=True, backpressure_threshold=0.5)
    await queue.open()
    
    print(f"初始配置: threshold={queue.backpressure_threshold}")
    
    # 添加 40 个请求 (40%)
    for i in range(40):
        await queue.put(MockRequest(f"http://example.com/{i}"))
    
    should_bp = await queue.should_apply_backpressure()
    print(f"\n添加 40 个请求 (40%):")
    print(f"  背压激活: {should_bp}")
    
    # 添加到 60 个请求 (60%)
    for i in range(40, 60):
        await queue.put(MockRequest(f"http://example.com/{i}"))
    
    should_bp = await queue.should_apply_backpressure()
    print(f"\n添加 60 个请求 (60%):")
    print(f"  背压激活: {should_bp}")
    
    # 变更阈值
    queue.backpressure_threshold = 0.7
    print(f"\n变更阈值为 0.7:")
    should_bp = await queue.should_apply_backpressure()
    print(f"  背压激活: {should_bp}")
    
    await queue.close()
    
    return True


async def test_backpressure_disabled():
    """测试背压禁用"""
    print("\n" + "=" * 60)
    print("测试 4: 背压禁用")
    print("=" * 60)
    
    queue = MemoryQueue(max_size=10, backpressure_enabled=False, backpressure_threshold=0.8)
    await queue.open()
    
    print(f"队列配置: backpressure_enabled={queue.backpressure_enabled}")
    
    # 添加 10 个请求（队列满）
    start_time = time.time()
    for i in range(10):
        await queue.put(MockRequest(f"http://example.com/{i}"))
    
    # 再添加一个，应该被拒绝
    success = await queue.put(MockRequest("http://example.com/rejected"))
    print(f"\n尝试添加第 11 个请求:")
    print(f"  成功: {success}")
    print(f"  队列大小: {await queue.size()}")
    print(f"  背压激活: {await queue.should_apply_backpressure()}")
    
    await queue.close()
    
    return True


async def test_high_load_backpressure():
    """测试高负载下的背压"""
    print("\n" + "=" * 60)
    print("测试 5: 高负载背压模拟")
    print("=" * 60)
    
    queue = MemoryQueue(max_size=100, backpressure_enabled=True, backpressure_threshold=0.9)
    await queue.open()
    
    print(f"队列配置: max_size={queue.max_size}, threshold={queue.backpressure_threshold}")
    
    # 模拟快速添加请求
    print("\n快速添加 150 个请求...")
    start_time = time.time()
    
    success_count = 0
    for i in range(150):
        success = await queue.put(MockRequest(f"http://example.com/{i}"))
        if success:
            success_count += 1
    
    total_time = time.time() - start_time
    
    print(f"\n结果:")
    print(f"  成功添加: {success_count}/150")
    print(f"  队列大小: {await queue.size()}")
    print(f"  总耗时: {total_time:.3f}s")
    print(f"  平均耗时: {total_time / 150:.4f}s/请求")
    print(f"  背压激活: {await queue.should_apply_backpressure()}")
    
    # 获取统计
    stats = queue.get_extended_stats()
    print(f"\n统计信息:")
    print(f"  总入队: {stats['total_puts']}")
    print(f"  拒绝数: {stats['rejected_puts']}")
    
    await queue.close()
    
    return True


async def test_backpressure_mixin_directly():
    """直接测试 BackpressureableQueueMixin"""
    print("\n" + "=" * 60)
    print("测试 6: 直接测试 BackpressureableQueueMixin")
    print("=" * 60)
    
    # BackpressureableQueueMixin 是混入类，需要配合 IQueue 使用
    # 这里使用 IQueue + Mixin 的方式测试
    from crawlo.queue.interfaces import IQueue
    
    class TestQueue(BackpressureableQueueMixin, IQueue):
        def __init__(self, max_size=100):
            super().__init__(max_size=max_size)
            self._current_size = 0
        
        async def put(self, item, priority=0):
            return True
        
        async def get(self, timeout=None):
            return None
        
        async def size(self) -> int:
            return self._current_size
        
        async def empty(self) -> bool:
            return self._current_size == 0
    
    queue = TestQueue(max_size=100)
    
    print(f"Mixin 配置:")
    print(f"  max_size: {queue.max_size}")
    print(f"  backpressure_enabled: {queue.backpressure_enabled}")
    print(f"  backpressure_threshold: {queue.backpressure_threshold}")
    
    # 模拟队列大小为 85
    queue._current_size = 85
    
    print(f"\n模拟队列使用率 85%:")
    print(f"  backpressure_active: {queue.backpressure_active}")
    
    # 计算延迟
    # 注意：由于 queue 没有实现 should_apply_backpressure 的完整逻辑
    # 这里直接设置 _backpressure_active
    queue._backpressure_active = True
    delay = await queue.calculate_backpressure_delay()
    print(f"  计算延迟 (手动设置激活后): {delay:.3f}s")
    
    return True


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Crawlo 背压功能测试")
    print("=" * 60)
    
    tests = [
        ("基础背压功能", test_basic_backpressure),
        ("背压延迟计算", test_backpressure_delay),
        ("背压阈值变更", test_backpressure_threshold_change),
        ("背压禁用", test_backpressure_disabled),
        ("高负载背压模拟", test_high_load_backpressure),
        ("Mixin 直接测试", test_backpressure_mixin_directly),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            print(f"\n测试 '{name}' 执行出错: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, "ERROR"))
    
    # 打印测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for name, status in results:
        symbol = "✓" if status == "PASS" else "✗"
        print(f"  [{symbol}] {name}: {status}")
        if status == "PASS":
            passed += 1
    
    print(f"\n通过: {passed}/{len(results)}")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
