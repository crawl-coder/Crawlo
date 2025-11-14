#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的 Scheduler 分布式队列功能
"""
import asyncio
import sys
from unittest.mock import Mock
from crawlo.core.scheduler import Scheduler
from crawlo.network.request import Request
from crawlo.logging import get_logger


class MockCrawler:
    """模拟 Crawler 对象"""
    def __init__(self, use_redis=True):
        self.settings = MockSettings(use_redis)
        self.stats = Mock()


class MockSettings:
    """模拟 Settings 对象"""
    def __init__(self, use_redis=True):
        self.use_redis = use_redis
        
    def get(self, key, default=None):
        config = {
            'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
            'LOG_LEVEL': 'INFO',
            'DEPTH_PRIORITY': 1,
            'SCHEDULER_MAX_QUEUE_SIZE': 100,
            'SCHEDULER_QUEUE_NAME': 'test:crawlo:requests',
            'FILTER_DEBUG': False,
            'PROJECT_NAME': 'test',
            'QUEUE_TYPE': 'memory',
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
        }
        if self.use_redis:
            config.update({
                'REDIS_URL': 'redis://localhost:6379/0',
                'QUEUE_TYPE': 'redis',
                'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
                'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
            })
        
        return config.get(key, default)
    
    def get_int(self, key, default=0):
        value = self.get(key, default)
        return int(value) if value is not None else default
        
    def get_bool(self, key, default=False):
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value) if value is not None else default

    def get_float(self, key, default=0.0):
        value = self.get(key, default)
        return float(value) if value is not None else default


class MockFilter:
    """模拟去重过滤器"""
    def __init__(self):
        self.seen = set()
        
    @classmethod
    def create_instance(cls, crawler):
        return cls()
    
    async def requested(self, request):
        if request.url in self.seen:
            return True
        self.seen.add(request.url)
        return False
    
    def log_stats(self, request):
        pass


async def test_memory_scheduler():
    """测试内存调度器"""
    print("🔍 测试内存调度器...")
    
    crawler = MockCrawler(use_redis=False)
    scheduler = Scheduler.create_instance(crawler)
    
    # 模拟去重过滤器
    scheduler.dupe_filter = MockFilter()
    
    await scheduler.open()
    
    # 测试入队
    request1 = Request(url="https://example1.com")
    request2 = Request(url="https://example2.com")
    
    success1 = await scheduler.enqueue_request(request1)
    success2 = await scheduler.enqueue_request(request2)
    
    print(f"   📤 入队结果: {success1}, {success2}")
    print(f"   队列大小: {len(scheduler)}")
    
    # 测试出队
    req1 = await scheduler.next_request()
    req2 = await scheduler.next_request()
    
    print(f"   📥 出队结果: {req1.url if req1 else None}, {req2.url if req2 else None}")
    print(f"   剩余大小: {len(scheduler)}")
    
    await scheduler.close()
    print("   内存调度器测试完成")


async def test_redis_scheduler():
    """测试 Redis 调度器"""
    print("🔍 测试 Redis 调度器...")
    
    try:
        crawler = MockCrawler(use_redis=True)
        scheduler = Scheduler.create_instance(crawler)
        
        # 模拟去重过滤器
        scheduler.dupe_filter = MockFilter()
        
        await scheduler.open()
        
        # 测试入队
        request1 = Request(url="https://redis-test1.com", priority=5)
        request2 = Request(url="https://redis-test2.com", priority=3)
        request3 = Request(url="https://redis-test3.com", priority=8)
        
        success1 = await scheduler.enqueue_request(request1)
        success2 = await scheduler.enqueue_request(request2)
        success3 = await scheduler.enqueue_request(request3)
        
        print(f"   入队结果: {success1}, {success2}, {success3}")
        print(f"   队列大小: {len(scheduler)}")
        
        # 等待一小段时间让 Redis 操作完成
        await asyncio.sleep(0.5)
        
        # 测试出队（应该按优先级排序）
        req1 = await scheduler.next_request()
        req2 = await scheduler.next_request()
        req3 = await scheduler.next_request()
        
        print("   📥 出队结果（按优先级）:")
        if req1:
            print(f"      {req1.url} (优先级: {getattr(req1, 'priority', 0)})")
        if req2:
            print(f"      {req2.url} (优先级: {getattr(req2, 'priority', 0)})")
        if req3:
            print(f"      {req3.url} (优先级: {getattr(req3, 'priority', 0)})")
            
        print(f"   剩余大小: {len(scheduler)}")
        
        await scheduler.close()
        print("   Redis 调度器测试完成")
        
    except Exception as e:
        print(f"   Redis 调度器测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_concurrent_redis():
    """测试并发 Redis 操作"""
    print("🔍 测试并发 Redis 操作...")
    
    async def producer(scheduler, name, count):
        """生产者"""
        for i in range(count):
            request = Request(url=f"https://{name}-{i}.com", priority=i % 10)
            await scheduler.enqueue_request(request)
            await asyncio.sleep(0.01)
        print(f"   生产者 {name} 完成 ({count} 个请求)")
    
    async def consumer(scheduler, name, count):
        """消费者"""
        consumed = 0
        for _ in range(count):
            request = await scheduler.next_request()
            if request:
                consumed += 1
                await asyncio.sleep(0.005)
            else:
                break
        print(f"   消费者 {name} 处理了 {consumed} 个请求")
    
    try:
        crawler = MockCrawler(use_redis=True)
        scheduler = Scheduler.create_instance(crawler)
        scheduler.dupe_filter = MockFilter()
        await scheduler.open()
        
        # 并发运行生产者和消费者
        tasks = [
            producer(scheduler, "producer-1", 5),
            producer(scheduler, "producer-2", 5),
            consumer(scheduler, "consumer-1", 3),
            consumer(scheduler, "consumer-2", 3),
            consumer(scheduler, "consumer-3", 4),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"   最终队列大小: {len(scheduler)}")
        
        await scheduler.close()
        print("   并发测试完成")
        
    except Exception as e:
        print(f"   并发测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试修复后的 Scheduler...")
    print("=" * 50)
    
    try:
        # 1. 测试内存调度器
        await test_memory_scheduler()
        print()
        
        # 2. 测试 Redis 调度器
        await test_redis_scheduler()
        print()
        
        # 3. 测试并发操作
        await test_concurrent_redis()
        
        print("=" * 50)
        print("所有 Scheduler 测试完成！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置日志级别避免过多输出
    import logging
    logging.getLogger('crawlo').setLevel(logging.WARNING)
    
    asyncio.run(main())