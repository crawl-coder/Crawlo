"""
极限场景测试：队列系统

测试队列在各种边界条件下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.network.request import Request


class TestExtremeMemoryQueueScenarios:
    """极端内存队列场景测试"""
    
    @pytest.mark.asyncio
    async def test_queue_massive_enqueue(self):
        """测试海量请求入队（10000 个）"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 入队 10000 个请求
        for i in range(10000):
            req = Request(f'http://example.com/page/{i}', priority=i % 10)
            await queue.put(req, priority=req.priority)
        
        # 验证队列大小
        size = await queue.qsize()
        assert size == 10000
        
        # 出队并验证优先级顺序
        last_priority = -1
        for _ in range(100):  # 只检查前 100 个
            req = await queue.get(timeout=1.0)
            if req:
                assert req.priority >= last_priority
                last_priority = req.priority
    
    @pytest.mark.asyncio
    async def test_queue_empty_get_timeout(self):
        """测试空队列 get 超时"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 空队列 get 应该返回 None 或超时
        req = await queue.get(timeout=0.1)
        assert req is None
    
    @pytest.mark.asyncio
    async def test_queue_rapid_enqueue_dequeue(self):
        """测试快速入队/出队（压力测试）"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 快速入队 1000 个
        for i in range(1000):
            await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        # 快速出队 1000 个
        count = 0
        for _ in range(1000):
            req = await queue.get(timeout=1.0)
            if req:
                count += 1
        
        assert count == 1000
    
    @pytest.mark.asyncio
    async def test_queue_priority_inversion(self):
        """测试优先级反转（小值应该先出队）"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 乱序入队
        priorities = [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]
        for p in priorities:
            await queue.put(Request(f'http://example.com/priority/{p}'), priority=p)
        
        # 出队应该按优先级升序
        last_priority = -1
        for _ in range(len(priorities)):
            req = await queue.get(timeout=1.0)
            if req:
                assert req.priority >= last_priority
                last_priority = req.priority
    
    @pytest.mark.asyncio
    async def test_queue_duplicate_urls(self):
        """测试重复 URL 入队"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 重复入队同一个 URL 100 次
        for _ in range(100):
            await queue.put(Request('http://example.com/duplicate'), priority=0)
        
        # 内存队列应该允许重复
        size = await queue.qsize()
        assert size == 100
    
    @pytest.mark.asyncio
    async def test_queue_concurrent_access(self):
        """测试并发访问队列"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 并发入队
        async def enqueue_batch(start, count):
            for i in range(start, start + count):
                await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        # 10 个并发任务，每个入队 100 个
        tasks = [enqueue_batch(i * 100, 100) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # 验证总数
        size = await queue.qsize()
        assert size == 1000


class TestExtremeRedisQueueScenarios:
    """极端 Redis 队列场景测试"""
    
    @pytest.mark.asyncio
    async def test_redis_queue_without_redis(self):
        """测试无 Redis 时的优雅降级"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        
        # 尝试连接不存在的 Redis
        try:
            queue = RedisPriorityQueue(
                redis_url='redis://localhost:65535/0',  # 不存在的端口
                queue_name='test:extreme',
                project_name='test',
                spider_name='test_spider'
            )
            
            # 应该连接失败
            with pytest.raises((ConnectionError, OSError)):
                await queue.connect(max_retries=1, delay=0)
        except Exception as e:
            # 任何其他异常也应该有清晰错误
            assert 'redis' in str(e).lower() or 'connection' in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_redis_queue_put_batch_empty(self):
        """测试 put_batch 空列表"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        
        queue = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:batch_empty',
            project_name='test',
            spider_name='test_spider'
        )
        
        # 空列表应返回 0
        result = await queue.put_batch([])
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_redis_queue_put_batch_massive(self):
        """测试 put_batch 大量请求"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        
        queue = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:batch_massive',
            project_name='test',
            spider_name='test_spider'
        )
        
        try:
            await queue.connect()
            
            # 批量入队 1000 个请求
            requests = [
                (Request(f'http://example.com/batch/{i}'), i % 10)
                for i in range(1000)
            ]
            
            success = await queue.put_batch(requests, batch_size=50)
            
            # 应该全部成功（假设 Redis 正常）
            assert success == 1000
            
        except ConnectionError:
            pytest.skip("Redis not available")
    
    @pytest.mark.asyncio
    async def test_redis_queue_put_batch_huge_batch_size(self):
        """测试 put_batch 超大 batch_size"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        
        queue = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:batch_huge',
            project_name='test',
            spider_name='test_spider'
        )
        
        try:
            await queue.connect()
            
            # 100 个请求，batch_size=10000（远超实际需求）
            requests = [
                (Request(f'http://example.com/huge/{i}'), 0)
                for i in range(100)
            ]
            
            success = await queue.put_batch(requests, batch_size=10000)
            assert success == 100
            
        except ConnectionError:
            pytest.skip("Redis not available")
    
    @pytest.mark.asyncio
    async def test_redis_queue_dirty_data_cleanup(self):
        """测试脏数据自动清理"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        import pickle
        
        queue = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:dirty_data',
            project_name='test',
            spider_name='test_spider'
        )
        
        try:
            await queue.connect()
            
            # 手动插入脏数据
            redis = queue._redis
            key = f"{queue.key_manager.namespace}:url:test_dirty"
            
            # 插入无效数据
            await redis.hset(
                queue.key_manager.get_requests_data_key(),
                key,
                b'invalid pickle data'
            )
            await redis.zadd(queue.queue_name, {key: 0})
            
            # 尝试获取，应该自动清理脏数据
            req = await queue.get(timeout=1.0)
            
            # 脏数据应该被清理，不会无限循环
            # 可能需要等待一下
            await asyncio.sleep(0.1)
            
            # 验证脏数据已被清理
            zset_size = await redis.zcard(queue.queue_name)
            assert zset_size == 0  # 脏数据应该被清理
            
        except ConnectionError:
            pytest.skip("Redis not available")
    
    @pytest.mark.asyncio
    async def test_redis_queue_serialization_formats(self):
        """测试不同序列化格式"""
        from crawlo.queue.redis_priority_queue import RedisPriorityQueue
        
        # 测试 pickle 格式
        queue_pickle = RedisPriorityQueue(
            redis_url='redis://localhost:6379/0',
            queue_name='test:pickle',
            project_name='test',
            spider_name='test_spider',
            serialization_format='pickle'
        )
        
        try:
            await queue_pickle.connect()
            
            req = Request('http://example.com/pickle')
            await queue_pickle.put(req, priority=0)
            
            restored = await queue_pickle.get(timeout=1.0)
            assert restored is not None
            assert restored.url == 'http://example.com/pickle'
            
        except ConnectionError:
            pytest.skip("Redis not available")


class TestExtremeBackpressureScenarios:
    """极端背压场景测试"""
    
    @pytest.mark.asyncio
    async def test_backpressure_queue_full(self):
        """测试队列满时的背压行为"""
        from crawlo.queue.queue_manager import QueueManager
        from crawlo.config import Config
        
        config = Config()
        config.set('QUEUE_TYPE', 'memory')
        config.set('QUEUE_MAXSIZE', 10)  # 很小的队列
        
        manager = QueueManager(config=config)
        await manager.initialize()
        
        queue = manager.get_queue()
        
        # 填满队列
        for i in range(10):
            await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        # 尝试继续入队，应该触发背压
        # 不同队列类型行为不同，这里只测试不崩溃
        try:
            await queue.put(Request('http://example.com/overflow'), priority=0)
        except Exception as e:
            # 如果有异常，应该是背压相关
            assert 'queue' in str(e).lower() or 'full' in str(e).lower() or 'backpressure' in str(e).lower()
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_backpressure_threshold_trigger(self):
        """测试背压阈值触发"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 设置背压阈值
        queue.backpressure_threshold = 0.8
        queue.maxsize = 100
        
        # 填充到 80%
        for i in range(80):
            await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        # 应该有背压警告（通过日志）
        # 这里只测试不崩溃
        assert await queue.qsize() == 80


class TestExtremeQueueEdgeCases:
    """极端队列边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_queue_priority_negative_values(self):
        """测试负数优先级"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 负数优先级
        await queue.put(Request('http://example.com/neg1'), priority=-10)
        await queue.put(Request('http://example.com/neg2'), priority=-5)
        await queue.put(Request('http://example.com/pos1'), priority=5)
        
        # 负数优先级应该更小（更高优先级）
        req1 = await queue.get(timeout=1.0)
        req2 = await queue.get(timeout=1.0)
        
        assert req1.priority <= req2.priority
    
    @pytest.mark.asyncio
    async def test_queue_priority_extreme_values(self):
        """测试极端优先级值"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 极大/极小优先级
        await queue.put(Request('http://example.com/min'), priority=-999999)
        await queue.put(Request('http://example.com/max'), priority=999999)
        await queue.put(Request('http://example.com/zero'), priority=0)
        
        # 应该按顺序出队
        req1 = await queue.get(timeout=1.0)
        assert req1.priority == -999999
    
    @pytest.mark.asyncio
    async def test_queue_close_reopen(self):
        """测试队列关闭后重新打开"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 使用队列
        await queue.put(Request('http://example.com/before'), priority=0)
        await queue.close()
        
        # 关闭后重新使用（如果支持）
        # 不同实现可能不同，这里只测试不崩溃
        try:
            await queue.put(Request('http://example.com/after'), priority=0)
        except:
            pass  # 可以接受拒绝
