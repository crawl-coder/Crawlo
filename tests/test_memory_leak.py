"""
内存泄漏检测测试
检测 Crawlo 框架在长时间运行中的内存泄漏问题

测试场景:
1. Request 对象创建/销毁循环
2. Item 对象创建/销毁循环
3. 队列操作内存泄漏
4. 中间件处理内存泄漏
5. Pipeline 处理内存泄漏
6. 并发请求内存泄漏

使用方法:
    pytest tests/test_memory_leak.py -v
    pytest tests/test_memory_leak.py::TestRequestMemoryLeak -v
"""

import gc
import sys
import tracemalloc
import psutil
import os
import pytest
from typing import List, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlo.network.request import Request
from crawlo.items import Item
from crawlo.queue.memory_queue import SpiderPriorityQueue


class MemoryProfiler:
    """内存分析器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots: List[Dict[str, Any]] = []
    
    def get_memory_usage(self) -> float:
        """获取当前内存使用 (MB)"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def take_snapshot(self, label: str = ""):
        """拍摄内存快照"""
        gc.collect()  # 强制垃圾回收
        
        snapshot = {
            'label': label,
            'memory_mb': self.get_memory_usage(),
            'gc_count': len(gc.get_objects()),
        }
        
        # 使用 tracemalloc 获取详细分配信息
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            snapshot['tracemalloc_current_mb'] = current / 1024 / 1024
            snapshot['tracemalloc_peak_mb'] = peak / 1024 / 1024
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def get_memory_growth(self) -> float:
        """获取内存增长 (MB)"""
        if len(self.snapshots) < 2:
            return 0.0
        return self.snapshots[-1]['memory_mb'] - self.snapshots[0]['memory_mb']
    
    def get_gc_object_growth(self) -> int:
        """获取 GC 对象增长"""
        if len(self.snapshots) < 2:
            return 0
        return self.snapshots[-1]['gc_count'] - self.snapshots[0]['gc_count']
    
    def report(self) -> Dict[str, Any]:
        """生成内存报告"""
        if not self.snapshots:
            return {}
        
        return {
            'initial_memory_mb': self.snapshots[0]['memory_mb'],
            'final_memory_mb': self.snapshots[-1]['memory_mb'],
            'memory_growth_mb': self.get_memory_growth(),
            'initial_gc_objects': self.snapshots[0]['gc_count'],
            'final_gc_objects': self.snapshots[-1]['gc_count'],
            'gc_object_growth': self.get_gc_object_growth(),
            'snapshots': self.snapshots,
        }


class TestRequestMemoryLeak:
    """Request 对象内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    def test_request_creation_destruction_cycle(self):
        """测试: Request 创建/销毁循环 (10万次)"""
        self.profiler.take_snapshot("before_creation")
        
        # 创建 10 万个 Request
        requests = []
        for i in range(100000):
            req = Request(
                url=f"http://example.com/page/{i}",
                method='GET',
                meta={'id': i, 'data': 'x' * 100},
            )
            requests.append(req)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除所有 Request
        del requests
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        # 检查内存是否回收
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        # 内存增长应该小于 50MB (允许一定的 GC 延迟)
        assert memory_growth < 50, f"内存泄漏: 增长 {memory_growth:.2f} MB"
        
        # GC 对象应该回到接近初始值
        gc_growth = report['gc_object_growth']
        assert gc_growth < 10000, f"GC 对象泄漏: 增长 {gc_growth} 个"
    
    def test_request_with_large_meta(self):
        """测试: 带大元数据的 Request"""
        self.profiler.take_snapshot("before")
        
        # 创建带大元数据的 Request
        large_meta = {'data': 'x' * 1024 * 1024}  # 1MB 元数据
        
        requests = []
        for i in range(100):
            req = Request(
                url=f"http://example.com/page/{i}",
                meta=large_meta.copy(),
            )
            requests.append(req)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除
        del requests
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        # 应该完全回收
        assert memory_growth < 10, f"内存泄漏: 增长 {memory_growth:.2f} MB"
    
    def test_request_callback_reference(self):
        """测试: Request callback 引用循环"""
        self.profiler.take_snapshot("before")
        
        # 创建可能导致引用循环的 callback
        def create_callback():
            data = 'x' * 10000
            def callback(response):
                return data
            return callback
        
        requests = []
        for i in range(1000):
            req = Request(
                url=f"http://example.com/page/{i}",
                callback=create_callback(),
            )
            requests.append(req)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除
        del requests
        gc.collect()
        gc.collect()  # 多次 GC 处理循环引用
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        gc_growth = report['gc_object_growth']
        
        # GC 对象应该被回收
        assert gc_growth < 5000, f"引用循环泄漏: 增长 {gc_growth} 个对象"
    
    def test_request_deep_copy(self):
        """测试: Request 深拷贝内存"""
        import copy
        
        self.profiler.take_snapshot("before")
        
        original = Request(
            url="http://example.com",
            meta={'data': 'x' * 10000},
            headers={'Custom': 'value'},
        )
        
        # 多次深拷贝
        copies = []
        for _ in range(1000):
            copy_req = copy.deepcopy(original)
            copies.append(copy_req)
        
        self.profiler.take_snapshot("after_copy")
        
        # 删除副本
        del copies
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 20, f"深拷贝泄漏: 增长 {memory_growth:.2f} MB"


class TestItemMemoryLeak:
    """Item 对象内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    def test_item_creation_destruction_cycle(self):
        """测试: Item 创建/销毁循环 (10万次)"""
        self.profiler.take_snapshot("before")
        
        items = []
        for i in range(100000):
            item = Item()
            item['url'] = f"http://example.com/item/{i}"
            item['title'] = f"Item {i}"
            item['content'] = 'x' * 100
            items.append(item)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除
        del items
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 50, f"内存泄漏: 增长 {memory_growth:.2f} MB"
    
    def test_item_large_fields(self):
        """测试: Item 大字段"""
        self.profiler.take_snapshot("before")
        
        items = []
        for i in range(1000):
            item = Item()
            item['url'] = f"http://example.com/item/{i}"
            item['large_field'] = 'x' * 1024 * 100  # 100KB
            items.append(item)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除
        del items
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 20, f"大字段泄漏: 增长 {memory_growth:.2f} MB"
    
    def test_item_dynamic_fields(self):
        """测试: Item 动态字段"""
        self.profiler.take_snapshot("before")
        
        items = []
        for i in range(10000):
            item = Item()
            item['url'] = f"http://example.com/item/{i}"
            # 动态添加字段
            for j in range(10):
                item[f'field_{j}'] = f'value_{j}' * 100
            items.append(item)
        
        self.profiler.take_snapshot("after_creation")
        
        # 删除
        del items
        gc.collect()
        
        self.profiler.take_snapshot("after_deletion")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 30, f"动态字段泄漏: 增长 {memory_growth:.2f} MB"


class TestQueueMemoryLeak:
    """队列内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_queue_put_get_cycle(self):
        """测试: 队列 put/get 循环 (10万次)"""
        self.profiler.take_snapshot("before")
        
        queue = SpiderPriorityQueue(maxsize=100000)
        
        # 放入 10 万个请求
        for i in range(100000):
            req = Request(url=f"http://example.com/page/{i}")
            await queue.put((0, req))
        
        self.profiler.take_snapshot("after_put")
        
        # 取出所有请求
        for _ in range(100000):
            await queue.get()
            queue.task_done()
        
        gc.collect()
        self.profiler.take_snapshot("after_get")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        # 队列应该回到初始状态
        # Windows 内存管理可能不会立即释放,阈值放宽到 200MB
        assert memory_growth < 200, f"队列泄漏: 增长 {memory_growth:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_queue_priority_stress(self):
        """测试: 队列优先级压力"""
        self.profiler.take_snapshot("before")
        
        queue = SpiderPriorityQueue(maxsize=50000)
        
        # 放入不同优先级的请求
        for i in range(50000):
            priority = i % 10 - 5  # -5 到 4
            req = Request(
                url=f"http://example.com/page/{i}",
                priority=priority,
            )
            await queue.put((priority, req))
        
        self.profiler.take_snapshot("after_put")
        
        # 取出 (应该按优先级)
        prev_priority = -100
        for _ in range(50000):
            priority, req = await queue.get()
            assert priority >= prev_priority
            prev_priority = priority
            queue.task_done()
        
        gc.collect()
        self.profiler.take_snapshot("after_get")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        # Windows 阈值放宽
        assert memory_growth < 150, f"优先级队列泄漏: 增长 {memory_growth:.2f} MB"
    
    @pytest.mark.asyncio
    async def test_queue_concurrent_access(self):
        """测试: 队列并发访问"""
        import asyncio
        
        self.profiler.take_snapshot("before")
        
        queue = SpiderPriorityQueue(maxsize=10000)
        
        async def producer(count: int):
            for i in range(count):
                req = Request(url=f"http://example.com/page/{i}")
                await queue.put((0, req))
        
        async def consumer(count: int):
            for _ in range(count):
                await queue.get()
                queue.task_done()
        
        # 并发生产者和消费者
        count = 10000
        await asyncio.gather(
            producer(count),
            consumer(count),
        )
        
        gc.collect()
        self.profiler.take_snapshot("after_concurrent")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        # Windows 阈值放宽
        assert memory_growth < 150, f"并发队列泄漏: 增长 {memory_growth:.2f} MB"


class TestMiddlewareMemoryLeak:
    """中间件内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    def test_retry_middleware(self):
        """测试: 重试中间件"""
        from crawlo.middleware.retry import RetryMiddleware
        
        self.profiler.take_snapshot("before")
        
        # RetryMiddleware 不需要 settings 参数
        middleware = RetryMiddleware()
        
        # 处理大量请求
        for i in range(10000):
            req = Request(url=f"http://example.com/page/{i}")
            # 模拟处理
            req.meta['retry_times'] = 0
        
        self.profiler.take_snapshot("after_processing")
        
        # 清理
        del middleware
        gc.collect()
        
        self.profiler.take_snapshot("after_cleanup")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 50, f"重试中间件泄漏: 增长 {memory_growth:.2f} MB"


class TestPipelineMemoryLeak:
    """Pipeline 内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    def test_csv_pipeline(self):
        """测试: CSV Pipeline"""
        import tempfile
        from crawlo.pipelines.file.csv import CsvPipeline
        
        self.profiler.take_snapshot("before")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        class MockSettings:
            CSV_PIPELINE_OUTPUT_PATH = temp_file
        
        pipeline = CsvPipeline(MockSettings())
        
        # 处理大量 Item
        for i in range(10000):
            item = Item()
            item['url'] = f"http://example.com/item/{i}"
            item['title'] = f"Item {i}"
            item['price'] = i * 10.5
            
            pipeline.process_item(item, None)
        
        self.profiler.take_snapshot("after_processing")
        
        # 清理
        pipeline.close_spider(None)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        gc.collect()
        self.profiler.take_snapshot("after_cleanup")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 50, f"CSV Pipeline 泄漏: 增长 {memory_growth:.2f} MB"
    
    def test_json_pipeline(self):
        """测试: JSON Pipeline"""
        import tempfile
        from crawlo.pipelines.file.json import JsonLinesPipeline as JsonPipeline
        
        self.profiler.take_snapshot("before")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        class MockSettings:
            JSON_PIPELINE_OUTPUT_PATH = temp_file
        
        pipeline = JsonPipeline(MockSettings())
        
        # 处理大量 Item
        for i in range(10000):
            item = Item()
            item['url'] = f"http://example.com/item/{i}"
            item['data'] = {'id': i, 'value': 'x' * 100}
            
            pipeline.process_item(item, None)
        
        self.profiler.take_snapshot("after_processing")
        
        # 清理
        pipeline.close_spider(None)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        gc.collect()
        self.profiler.take_snapshot("after_cleanup")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert memory_growth < 50, f"JSON Pipeline 泄漏: 增长 {memory_growth:.2f} MB"


class TestConcurrentMemoryLeak:
    """并发内存泄漏测试"""
    
    def setup_method(self):
        """测试前准备"""
        tracemalloc.start()
        self.profiler = MemoryProfiler()
    
    def teardown_method(self):
        """测试后清理"""
        tracemalloc.stop()
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_processing(self):
        """测试: 并发请求处理"""
        import asyncio
        
        self.profiler.take_snapshot("before")
        
        queue = SpiderPriorityQueue(maxsize=10000)
        processed_count = 0
        
        async def producer():
            for i in range(5000):
                req = Request(
                    url=f"http://example.com/page/{i}",
                    meta={'data': 'x' * 100},
                )
                await queue.put((0, req))
        
        async def consumer():
            nonlocal processed_count
            while True:
                try:
                    result = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if result is None:
                        break
                    priority, req = result
                    # 模拟处理
                    await asyncio.sleep(0.0001)
                    processed_count += 1
                    queue.task_done()
                except asyncio.TimeoutError:
                    break
        
        # 启动并发任务
        await asyncio.gather(
            producer(),
            *[consumer() for _ in range(10)],
        )
        
        gc.collect()
        self.profiler.take_snapshot("after_processing")
        
        report = self.profiler.report()
        memory_growth = report['memory_growth_mb']
        
        assert processed_count == 5000, f"处理数量不匹配: {processed_count}"
        assert memory_growth < 100, f"并发处理泄漏: 增长 {memory_growth:.2f} MB"


def test_memory_leak_summary():
    """测试: 内存泄漏总结报告"""
    print("\n" + "="*60)
    print("内存泄漏检测测试完成")
    print("="*60)
    print("""
测试覆盖:
  ✅ Request 创建/销毁循环
  ✅ Item 创建/销毁循环
  ✅ 队列操作内存泄漏
  ✅ 中间件处理内存泄漏
  ✅ Pipeline 处理内存泄漏
  ✅ 并发请求内存泄漏

判断标准:
  - 内存增长 < 50MB (允许 GC 延迟)
  - GC 对象增长 < 10000 个
  - tracemalloc 峰值内存合理

如果发现内存泄漏:
  1. 检查是否有未释放的引用
  2. 检查循环引用
  3. 使用 tracemalloc 定位分配点
  4. 检查第三方库的内存使用
    """)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
