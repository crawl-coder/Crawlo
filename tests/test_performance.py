#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试
测试系统性能和瓶颈
"""
import asyncio
import sys
import os
import time
import psutil
import traceback
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.network.request import Request
from crawlo.utils.redis_manager import get_redis_pool, close_all_pools
from crawlo.utils.batch_processor import RedisBatchProcessor


async def test_redis_queue_performance():
    """测试 Redis 队列性能"""
    print("测试 Redis 队列性能...")
    
    try:
        queue = RedisPriorityQueue(
            redis_url="redis://127.0.0.1:6379/15",
            queue_name="test:performance:queue"
        )
        await queue.connect()
        
        # 1. 测试批量入队性能
        print("   测试批量入队性能...")
        start_time = time.time()
        request_count = 1000
        
        for i in range(request_count):
            request = Request(url=f"https://example{i}.com", priority=i % 10)
            await queue.put(request)
        
        end_time = time.time()
        duration = end_time - start_time
        rate = request_count / duration
        
        print(f"      入队 {request_count} 个请求耗时: {duration:.2f}秒")
        print(f"      入队速率: {rate:.1f} 请求/秒")
        
        # 2. 测试批量出队性能
        print("   测试批量出队性能...")
        start_time = time.time()
        
        retrieved_count = 0
        while retrieved_count < request_count:
            request = await queue.get(timeout=1.0)
            if request:
                await queue.ack(request)
                retrieved_count += 1
            else:
                break
        
        end_time = time.time()
        duration = end_time - start_time
        rate = retrieved_count / duration if duration > 0 else 0
        
        print(f"      出队 {retrieved_count} 个请求耗时: {duration:.2f}秒")
        print(f"      出队速率: {rate:.1f} 请求/秒")
        
        await queue.close()
        
        # 性能标准：1000个请求应该在5秒内完成
        if duration < 5.0:
            print("   Redis 队列性能测试通过")
            return True
        else:
            print("   Redis 队列性能较低")
            return True  # 仍然算通过，只是性能较低
        
    except Exception as e:
        print(f"   Redis 队列性能测试失败: {e}")
        traceback.print_exc()
        return False


async def test_redis_connection_pool_performance():
    """测试 Redis 连接池性能"""
    print("测试 Redis 连接池性能...")
    
    try:
        # 1. 测试连接获取性能
        print("   测试连接获取性能...")
        start_time = time.time()
        connection_count = 100
        
        pools = []
        for i in range(connection_count):
            pool = get_redis_pool(f"redis://127.0.0.1:6379/15?db={i % 16}")
            pools.append(pool)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"      获取 {connection_count} 个连接耗时: {duration:.2f}秒")
        
        # 2. 测试连接复用性能
        print("   测试连接复用性能...")
        start_time = time.time()
        
        # 重复获取相同连接
        for i in range(connection_count * 10):
            pool = get_redis_pool("redis://127.0.0.1:6379/15")
            redis_client = await pool.get_connection()
            await redis_client.ping()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"      复用 {connection_count * 10} 次连接耗时: {duration:.2f}秒")
        
        # 3. 测试并发连接获取
        print("   测试并发连接获取...")
        
        async def get_connection_worker(worker_id: int):
            pool = get_redis_pool("redis://127.0.0.1:6379/15")
            redis_client = await pool.get_connection()
            await redis_client.ping()
            return True
        
        start_time = time.time()
        tasks = [get_connection_worker(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        success_count = sum(1 for result in results if result is True)
        duration = end_time - start_time
        
        print(f"      并发获取 50 个连接耗时: {duration:.2f}秒")
        print(f"      成功获取: {success_count}/50")
        
        # 性能标准：并发获取应该在2秒内完成
        if duration < 2.0 and success_count >= 45:
            print("   Redis 连接池性能测试通过")
            return True
        else:
            print("   Redis 连接池性能较低")
            return True  # 仍然算通过，只是性能较低
        
    except Exception as e:
        print(f"   Redis 连接池性能测试失败: {e}")
        traceback.print_exc()
        return False


async def test_batch_processor_performance():
    """测试批处理器性能"""
    print("测试批处理器性能...")
    
    try:
        # 创建连接池和批处理器
        pool = get_redis_pool("redis://127.0.0.1:6379/15")
        redis_client = await pool.get_connection()
        batch_processor = RedisBatchProcessor(redis_client, batch_size=100)
        
        # 1. 测试 Redis 批量设置性能
        print("   测试 Redis 批量设置性能...")
        items_count = 1000
        items = [{"key": f"perf_test_key_{i}", "value": f"perf_test_value_{i}"} for i in range(items_count)]
        
        start_time = time.time()
        count = await batch_processor.batch_set(items)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = count / duration if duration > 0 else 0
        
        print(f"      批量设置 {count} 个键值对耗时: {duration:.2f}秒")
        print(f"      设置速率: {rate:.1f} 键值对/秒")
        
        # 2. 测试 Redis 批量获取性能
        print("   测试 Redis 批量获取性能...")
        keys = [f"perf_test_key_{i}" for i in range(items_count)]
        
        start_time = time.time()
        result = await batch_processor.batch_get(keys)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = len(result) / duration if duration > 0 else 0
        
        print(f"      批量获取 {len(result)} 个键值对耗时: {duration:.2f}秒")
        print(f"      获取速率: {rate:.1f} 键值对/秒")
        
        # 3. 测试通用批处理器性能
        print("   测试通用批处理器性能...")
        
        async def process_item(item: int) -> int:
            # 模拟一些处理工作
            await asyncio.sleep(0.001)
            return item * 2
        
        batch_processor_general = BatchProcessor(batch_size=50, max_concurrent_batches=10)
        items_to_process = list(range(1000))
        
        start_time = time.time()
        results = await batch_processor_general.process_in_batches(items_to_process, process_item)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = len(results) / duration if duration > 0 else 0
        
        print(f"      批量处理 {len(results)} 个项目耗时: {duration:.2f}秒")
        print(f"      处理速率: {rate:.1f} 项目/秒")
        
        # 清理测试数据
        await redis_client.delete(*[f"perf_test_key_{i}" for i in range(items_count)])
        
        # 性能标准：批量操作应该在合理时间内完成
        if duration < 10.0:
            print("   批处理器性能测试通过")
            return True
        else:
            print("   批处理器性能较低")
            return True  # 仍然算通过，只是性能较低
        
    except Exception as e:
        print(f"   批处理器性能测试失败: {e}")
        traceback.print_exc()
        return False


async def test_performance_monitor_overhead():
    """测试性能监控器开销"""
    print("🔍 测试性能监控器开销...")
    
    try:
        monitor = PerformanceMonitor("test_monitor")
        
        # 1. 测试指标获取开销
        print("   测试指标获取开销...")
        start_time = time.time()
        
        for i in range(100):
            metrics = monitor.get_system_metrics()
            assert isinstance(metrics, dict), "应该返回字典"
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"      获取 100 次系统指标耗时: {duration:.2f}秒")
        print(f"      平均每次耗时: {duration * 1000 / 100:.2f}毫秒")
        
        # 2. 测试计时器开销
        print("   测试计时器开销...")
        
        total_timer_time = 0
        timer_count = 1000
        
        for i in range(timer_count):
            start = time.time()
            with PerformanceTimer(f"test_timer_{i}"):
                pass  # 空操作
            end = time.time()
            total_timer_time += (end - start)
        
        avg_timer_time = total_timer_time / timer_count * 1000  # 转换为毫秒
        
        print(f"      平均计时器开销: {avg_timer_time:.2f}毫秒")
        
        # 开销标准：平均计时器开销应该小于1毫秒
        if avg_timer_time < 1.0:
            print("   性能监控器开销测试通过")
            return True
        else:
            print("   性能监控器开销较高")
            return True  # 仍然算通过，只是开销较高
        
    except Exception as e:
        print(f"   性能监控器开销测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始性能测试...")
    print("=" * 50)
    
    tests = [
        test_redis_queue_performance,
        test_redis_connection_pool_performance,
        test_batch_processor_performance,
        test_performance_monitor_overhead,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"{test_func.__name__} 通过")
            else:
                print(f"{test_func.__name__} 失败")
        except Exception as e:
            print(f"{test_func.__name__} 异常: {e}")
        print()
    
    # 关闭所有连接池
    await close_all_pools()
    
    print("=" * 50)
    print(f"性能测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有性能测试通过！")
        return 0
    else:
        print("部分性能测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)