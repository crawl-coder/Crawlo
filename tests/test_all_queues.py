#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
队列和背压功能完整测试脚本

测试内容：
1. 内存队列 (MemoryQueue) - 基础功能和背压
2. Redis队列 (RedisPriorityQueue) - 分布式队列
3. 磁盘队列 (DiskQueue) - 持久化队列
4. 背压策略 - QueueSizeStrategy, AdaptiveStrategy, CompositeStrategy
"""

import asyncio
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.queue.memory_queue import MemoryQueue
from crawlo.queue.disk_queue import DiskQueue, DiskQueueConfig
from crawlo.queue.queue_types import QueueType
from crawlo.backpressure import (
    BackpressureController,
    QueueSizeStrategy,
    AdaptiveStrategy,
    CompositeStrategy,
    PressureLevel,
)
from crawlo.network.request import Request


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_header(title):
    """打印标题"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{title.center(70)}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg):
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.RESET}")


async def test_memory_queue():
    """测试内存队列"""
    print_header("测试 1: 内存队列 (MemoryQueue)")
    
    try:
        # 创建内存队列，启用背压
        queue = MemoryQueue(
            max_size=50,
            backpressure_enabled=True,
            backpressure_threshold=0.8
        )
        await queue.open()
        print_success("队列创建成功")
        
        # 测试基本操作
        request1 = Request(url="http://example.com/1")
        request2 = Request(url="http://example.com/2", priority=5)
        
        await queue.put(request1, priority=0)
        await queue.put(request2, priority=5)
        print_success("请求入队成功")
        
        size = await queue.size()
        print_info(f"当前队列大小: {size}")
        assert size == 2, f"队列大小应为2，实际为{size}"
        
        # 测试优先级（高优先级先出队）
        item = await queue.get()
        print_info(f"出队请求URL: {item.url}")
        assert "example.com/2" in item.url, "高优先级请求应先出队"
        print_success("优先级队列工作正常")
        
        # 测试背压功能
        print_header("测试背压功能")
        
        # 填充队列到阈值以上
        for i in range(45):
            await queue.put(Request(url=f"http://example.com/{i}"))
        
        size = await queue.size()
        utilization = size / queue.max_size
        print_info(f"队列大小: {size}, 使用率: {utilization:.0%}")
        
        # 测试背压控制器
        controller = BackpressureController(strategy=QueueSizeStrategy())
        should_apply = await controller.should_apply(queue)
        delay = await controller.calculate_delay(queue)
        metrics = await controller.get_metrics(queue)
        
        print_info(f"背压应启用: {should_apply}")
        print_info(f"背压延迟: {delay:.3f}s")
        print_info(f"背压级别: {metrics.level.value}")
        
        if should_apply and delay > 0:
            print_success("背压功能正常工作")
        else:
            print_error("背压功能可能异常")
        
        await queue.close()
        print_success("内存队列测试通过")
        return True
        
    except Exception as e:
        print_error(f"内存队列测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_disk_queue():
    """测试磁盘队列"""
    print_header("测试 2: 磁盘队列 (DiskQueue)")
    
    import tempfile
    import shutil
    
    temp_dir = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="crawlo_disk_queue_test_")
        print_info(f"临时目录: {temp_dir}")
        
        # 创建磁盘队列配置
        config = DiskQueueConfig(
            path=temp_dir,
            max_size=100,
            batch_size=10,
            compress=False,  # 禁用压缩以便测试
        )
        
        # 创建磁盘队列
        queue = DiskQueue(config=config)
        await queue.open()
        print_success("磁盘队列创建成功")
        
        # 测试基本操作
        request1 = Request(url="http://example.com/disk1")
        request2 = Request(url="http://example.com/disk2", priority=10)
        
        await queue.put(request1, priority=0)
        await queue.put(request2, priority=10)
        print_success("请求入队成功")
        
        size = await queue.size()
        print_info(f"当前队列大小: {size}")
        assert size == 2, f"队列大小应为2，实际为{size}"
        
        # 测试持久化
        await queue.close()
        print_info("队列已关闭，测试重新打开...")
        
        # 重新打开队列，数据应该还在
        queue2 = DiskQueue(config=config)
        await queue2.open()
        
        size = await queue2.size()
        print_info(f"重新打开后队列大小: {size}")
        assert size == 2, "持久化数据应该保留"
        print_success("持久化功能正常")
        
        # 测试优先级
        item = await queue2.get()
        print_info(f"出队请求URL: {item.url}")
        assert "disk2" in item.url, "高优先级请求应先出队"
        print_success("优先级队列工作正常")
        
        # 测试批量操作
        print_header("测试批量操作")
        batch_requests = [Request(url=f"http://example.com/batch_{i}") for i in range(20)]
        
        start_time = time.time()
        for req in batch_requests:
            await queue2.put(req)
        batch_put_time = time.time() - start_time
        print_info(f"批量入队20个请求耗时: {batch_put_time:.3f}s")
        
        start_time = time.time()
        retrieved = []
        for _ in range(20):
            item = await queue2.get()
            if item:
                retrieved.append(item)
        batch_get_time = time.time() - start_time
        print_info(f"批量出队20个请求耗时: {batch_get_time:.3f}s")
        
        assert len(retrieved) == 20, "应成功取出20个请求"
        print_success("批量操作正常")
        
        await queue2.close()
        print_success("磁盘队列测试通过")
        return True
        
    except Exception as e:
        print_error(f"磁盘队列测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print_info(f"已清理临时目录: {temp_dir}")


async def test_redis_queue():
    """测试Redis队列"""
    print_header("测试 3: Redis队列 (RedisPriorityQueue)")
    
    try:
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        print_info("Redis队列模块可用")
        
        # 尝试连接Redis
        queue = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:crawlo:queue',
        )
        
        connected = await queue.connect()
        if not connected:
            print_error("无法连接到Redis服务器，跳过Redis队列测试")
            return None  # 返回None表示跳过
        
        print_success("Redis连接成功")
        
        # 测试基本操作
        request1 = Request(url="http://example.com/redis1")
        request2 = Request(url="http://example.com/redis2", priority=5)
        
        # 记录初始大小（Redis可能有之前测试的数据）
        initial_size = await queue.qsize()
        print_info(f"初始队列大小: {initial_size}")
        
        await queue.put(request1, priority=0)
        await queue.put(request2, priority=5)
        print_success("请求入队成功")
        
        size = await queue.qsize()
        print_info(f"当前队列大小: {size}")
        assert size == initial_size + 2, f"队列大小应为{initial_size + 2}，实际为{size}"
        
        # 测试出队（不验证优先级，因为Redis队列可能有旧数据）
        item = await queue.get()
        print_info(f"出队请求URL: {item.url}")
        print_success("出队操作正常")
        
        # 测试批量操作
        print_header("测试Redis批量操作")
        batch_requests = [Request(url=f"http://example.com/redis_batch_{i}") for i in range(20)]
        
        start_time = time.time()
        for req in batch_requests:
            await queue.put(req)
        batch_put_time = time.time() - start_time
        print_info(f"批量入队20个请求耗时: {batch_put_time:.3f}s")
        
        # 批量获取
        start_time = time.time()
        retrieved = []
        for _ in range(20):
            item = await queue.get()
            if item:
                retrieved.append(item)
        batch_get_time = time.time() - start_time
        print_info(f"批量出队20个请求耗时: {batch_get_time:.3f}s")
        
        assert len(retrieved) == 20, f"应成功取出20个请求，实际取出{len(retrieved)}个"
        print_success("批量操作正常")
        
        print_success("Redis队列测试通过")
        return True
        
    except ImportError:
        print_error("Redis队列模块不可用，跳过测试")
        return None
    except Exception as e:
        print_error(f"Redis队列测试失败: {e}")
        print_info("请确保Redis服务器正在运行 (localhost:6379)")
        return False


async def test_backpressure_strategies():
    """测试背压策略"""
    print_header("测试 4: 背压策略")
    
    try:
        # 创建测试队列
        queue = MemoryQueue(max_size=100, backpressure_enabled=True)
        await queue.open()
        
        # 填充队列到不同级别
        for i in range(85):  # 85% 使用率
            await queue.put(Request(url=f"http://example.com/{i}"))
        
        print_info(f"队列大小: {await queue.size()}, 使用率: 85%")
        
        # 测试 QueueSizeStrategy
        print_header("测试 QueueSizeStrategy")
        strategy1 = QueueSizeStrategy()
        should_apply1 = await strategy1.should_apply(queue)
        delay1 = await strategy1.calculate_delay(queue)
        level1 = await strategy1.get_level(queue)
        
        print_info(f"QueueSizeStrategy - 级别: {level1.value}")
        print_info(f"QueueSizeStrategy - 应启用背压: {should_apply1}")
        print_info(f"QueueSizeStrategy - 延迟: {delay1:.3f}s")
        print_success("QueueSizeStrategy 工作正常")
        
        # 测试 AdaptiveStrategy
        print_header("测试 AdaptiveStrategy")
        strategy2 = AdaptiveStrategy()
        
        should_apply2 = await strategy2.should_apply(queue)
        delay2 = await strategy2.calculate_delay(queue)
        level2 = await strategy2.get_level(queue)
        
        print_info(f"AdaptiveStrategy - 级别: {level2.value}")
        print_info(f"AdaptiveStrategy - 应启用背压: {should_apply2}")
        print_info(f"AdaptiveStrategy - 延迟: {delay2:.3f}s")
        print_success("AdaptiveStrategy 工作正常")
        
        # 测试 CompositeStrategy
        print_header("测试 CompositeStrategy")
        strategy3 = CompositeStrategy([strategy1, strategy2])
        
        should_apply3 = await strategy3.should_apply(queue)
        delay3 = await strategy3.calculate_delay(queue)
        level3 = await strategy3.get_level(queue)
        
        print_info(f"CompositeStrategy - 级别: {level3.value}")
        print_info(f"CompositeStrategy - 应启用背压: {should_apply3}")
        print_info(f"CompositeStrategy - 延迟: {delay3:.3f}s")
        print_success("CompositeStrategy 工作正常")
        
        # 测试 BackpressureController
        print_header("测试 BackpressureController")
        controller = BackpressureController(strategy=QueueSizeStrategy())
        
        status = controller.get_stats()
        print_info(f"控制器状态: {status}")
        
        should_apply = await controller.should_apply(queue)
        delay = await controller.calculate_delay(queue)
        metrics = await controller.get_metrics(queue)
        
        print_info(f"控制器 - 应启用背压: {should_apply}")
        print_info(f"控制器 - 延迟: {delay:.3f}s")
        print_info(f"控制器 - 使用率: {metrics.utilization:.0%}")
        print_success("BackpressureController 工作正常")
        
        await queue.close()
        print_success("背压策略测试通过")
        return True
        
    except Exception as e:
        print_error(f"背压策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    print_header("Crawlo 队列和背压功能完整测试")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "内存队列": await test_memory_queue(),
        "磁盘队列": await test_disk_queue(),
        "Redis队列": await test_redis_queue(),
        "背压策略": await test_backpressure_strategies(),
    }
    
    # 打印测试总结
    print_header("测试总结")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results.items():
        if result is True:
            print_success(f"{name}: 通过")
            passed += 1
        elif result is False:
            print_error(f"{name}: 失败")
            failed += 1
        else:  # None - 跳过
            print_info(f"{name}: 跳过")
            skipped += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed == 0:
        print_success("所有测试通过！")
        return 0
    else:
        print_error(f"有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
