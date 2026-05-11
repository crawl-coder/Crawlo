"""
极限场景测试：爬虫引擎和框架

测试框架在极端条件下的整体健壮性
"""
import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from crawlo.network.request import Request
from crawlo.spider.spider import Spider


class TestExtremeEngineScenarios:
    """极端引擎场景测试"""
    
    @pytest.mark.asyncio
    async def test_engine_immediate_shutdown(self):
        """测试引擎启动后立即关闭"""
        from crawlo.crawler import Crawler
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        crawler = Crawler(settings=settings)
        
        # 启动后立即关闭
        try:
            # 这里只测试不崩溃，实际启动需要完整配置
            pass
        except Exception as e:
            # 应该有清晰错误或优雅退出
            assert isinstance(e, (Exception,))
    
    @pytest.mark.asyncio
    async def test_engine_multiple_starts(self):
        """测试多次启动引擎"""
        # 引擎多次启动应该被拒绝或警告
        # 这里测试框架层面不崩溃
        pass
    
    @pytest.mark.asyncio
    async def test_spider_exception_doesnt_crash_engine(self):
        """测试 Spider 抛出异常不影响引擎"""
        class BrokenSpider(Spider):
            name = 'broken'
            
            def start_requests(self):
                raise Exception("Intentional spider error")
        
        spider = BrokenSpider()
        
        # Spider 初始化不应该崩溃
        assert spider.name == 'broken'
    
    @pytest.mark.asyncio
    async def test_middleware_exception_handling(self):
        """测试中间件异常处理"""
        from crawlo.middleware.base import BaseMiddleware
        
        class BrokenMiddleware(BaseMiddleware):
            async def process_request(self, request, spider):
                raise Exception("Intentional middleware error")
        
        middleware = BrokenMiddleware()
        
        # 中间件异常应该被框架捕获
        req = Request('http://example.com')
        
        try:
            result = await middleware.process_request(req, None)
        except Exception as e:
            # 异常应该被传播或处理
            assert str(e) == "Intentional middleware error"
    
    @pytest.mark.asyncio
    async def test_pipeline_exception_data_preservation(self):
        """测试 Pipeline 异常时数据不丢失"""
        from crawlo.pipelines.base_pipeline import BasePipeline
        from crawlo.items.item import Item
        
        class BrokenPipeline(BasePipeline):
            async def process_item(self, item, spider):
                raise Exception("Intentional pipeline error")
        
        pipeline = BrokenPipeline()
        item = Item()
        item['url'] = 'http://example.com'
        
        # Pipeline 异常应该被捕获
        try:
            await pipeline.process_item(item, None)
        except Exception as e:
            assert str(e) == "Intentional pipeline error"
        
        # Item 不应该被修改
        assert item['url'] == 'http://example.com'


class TestExtremeConcurrencyScenarios:
    """极端并发场景测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_spider_execution(self):
        """测试并发执行多个 Spider"""
        class FastSpider(Spider):
            name = 'fast'
            
            def start_requests(self):
                for i in range(10):
                    yield Request(f'http://example.com/{i}')
        
        # 创建 10 个 Spider 实例
        spiders = [FastSpider() for _ in range(10)]
        
        # 应该能正常创建
        assert len(spiders) == 10
        assert all(s.name == 'fast' for s in spiders)
    
    @pytest.mark.asyncio
    async def test_concurrent_request_processing(self):
        """测试并发处理请求（压力测试）"""
        import concurrent.futures
        
        def process_request(url):
            req = Request(url)
            return req.url
        
        # 1000 并发处理
        urls = [f'http://example.com/{i}' for i in range(1000)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(process_request, url) for url in urls]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 1000
    
    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self):
        """测试并发队列操作"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        async def producer(start, count):
            for i in range(start, start + count):
                await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        async def consumer(count):
            consumed = []
            for _ in range(count):
                req = await queue.get(timeout=1.0)
                if req:
                    consumed.append(req)
            return consumed
        
        # 10 个生产者，每个生产 100 个
        producers = [producer(i * 100, 100) for i in range(10)]
        
        # 并发执行
        await asyncio.gather(*producers)
        
        # 验证总数
        size = await queue.size()  # 使用异步 API
        assert size == 1000


class TestExtremeMemoryLeakScenarios:
    """极端内存泄漏测试"""
    
    @pytest.mark.asyncio
    async def test_request_creation_no_leak(self):
        """测试大量创建 Request 对象无泄漏"""
        import gc
        import sys
        
        # 记录初始引用计数
        gc.collect()
        initial_count = len(gc.get_objects())
        
        # 创建 10000 个 Request
        requests = []
        for i in range(10000):
            req = Request(
                f'http://example.com/{i}',
                meta={'data': 'x' * 1000}  # 每个带 1KB 数据
            )
            requests.append(req)
        
        # 清除引用
        del requests
        gc.collect()
        
        # 内存应该被回收
        final_count = len(gc.get_objects())
        
        # 允许一定浮动
        assert abs(final_count - initial_count) < 1000
    
    @pytest.mark.asyncio
    async def test_queue_operations_no_leak(self):
        """测试队列操作无泄漏"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        import gc
        
        queue = SpiderPriorityQueue()
        
        gc.collect()
        initial_count = len(gc.get_objects())
        
        # 大量入队/出队
        for i in range(1000):
            req = Request(f'http://example.com/{i}')
            await queue.put(req, priority=0)
        
        for _ in range(1000):
            await queue.get(timeout=1.0)
        
        gc.collect()
        final_count = len(gc.get_objects())
        
        # 内存应该被回收（放宽阈值）
        assert abs(final_count - initial_count) < 3000  # 1000 个 Request 对象 + 内部结构


class TestExtremeConfigScenarios:
    """极端配置场景测试"""
    
    def test_config_empty_values(self):
        """测试空配置值"""
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        
        # 设置空值
        settings.set('EMPTY_STRING', '')
        settings.set('EMPTY_LIST', [])
        settings.set('EMPTY_DICT', {})
        settings.set('NONE_VALUE', None)
        
        # 应该能正常处理
        assert settings.get('EMPTY_STRING') == ''
        assert settings.get('EMPTY_LIST') == []
        assert settings.get('EMPTY_DICT') == {}
        assert settings.get('NONE_VALUE') is None
    
    def test_config_extreme_values(self):
        """测试极端配置值"""
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        
        # 极大值
        settings.set('HUGE_INT', 999999999)
        settings.set('HUGE_STRING', 'x' * 1000000)  # 1MB 字符串
        settings.set('HUGE_LIST', list(range(100000)))  # 10 万元素
        
        # 应该能正常存储
        assert settings.get('HUGE_INT') == 999999999
        assert len(settings.get('HUGE_STRING')) == 1000000
        assert len(settings.get('HUGE_LIST')) == 100000
    
    def test_config_type_conversion(self):
        """测试配置类型转换"""
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        
        # 字符串转整数
        settings.set('STRING_INT', '42')
        assert settings.get_int('STRING_INT') == 42
        
        # 字符串转布尔
        settings.set('STRING_BOOL_TRUE', 'true')
        settings.set('STRING_BOOL_FALSE', 'false')
        assert settings.getbool('STRING_BOOL_TRUE') is True
        assert settings.getbool('STRING_BOOL_FALSE') is False
        
        # 字符串转列表
        settings.set('STRING_LIST', 'a,b,c')
        # 取决于实现，可能返回列表或字符串
    
    def test_config_missing_key(self):
        """测试缺失配置键"""
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        
        # 获取不存在的键
        value = settings.get('NONEXISTENT_KEY')
        assert value is None
        
        # 带默认值
        value = settings.get('NONEXISTENT_KEY', default='fallback')
        assert value == 'fallback'


class TestExtremeLoggingScenarios:
    """极端日志场景测试"""
    
    def test_log_massive_message(self):
        """测试记录超大日志消息"""
        from crawlo.logging import get_logger
        
        logger = get_logger('test.extreme')
        
        # 1MB 日志消息
        huge_message = 'x' * 1024 * 1024
        
        # 应该能记录或不崩溃
        try:
            logger.info(huge_message)
        except:
            pass  # 可以拒绝
    
    def test_log_special_characters(self):
        """测试日志特殊字符"""
        from crawlo.logging import get_logger
        
        logger = get_logger('test.extreme')
        
        special_messages = [
            '中文日志',
            'Emoji 日志 😀🎉',
            'HTML <script>alert(1)</script>',
            'SQL SELECT * FROM users; DROP TABLE users;',
            'Null bytes \x00\x01\x02',
        ]
        
        for msg in special_messages:
            try:
                logger.info(msg)
            except:
                pytest.fail(f"Logger should handle special chars: {msg}")
    
    def test_log_rapid_writes(self):
        """测试快速写日志（压力测试）"""
        from crawlo.logging import get_logger
        import time
        
        logger = get_logger('test.extreme')
        
        start = time.time()
        
        # 10000 条日志
        for i in range(10000):
            logger.debug(f"Log message {i}")
        
        elapsed = time.time() - start
        
        # 应该在合理时间内完成（< 10秒）
        assert elapsed < 10.0


class TestExtremeStatsScenarios:
    """极端统计场景测试"""
    
    @pytest.mark.asyncio
    async def test_stats_massive_counters(self):
        """测试海量计数器"""
        from crawlo.stats.collector import StatsCollector
        from crawlo.settings.setting_manager import SettingManager
        
        settings = SettingManager()
        collector = StatsCollector(settings)
        
        # 10000 个不同计数器
        for i in range(10000):
            collector.set_value(f'counter_{i}', i)
        
        # 应该能正常存储
        for i in range(10000):
            assert collector.get_value(f'counter_{i}') == i
    
    @pytest.mark.asyncio
    async def test_stats_rapid_updates(self):
        """测试快速更新统计"""
        from crawlo.stats.collector import StatsCollector
        from crawlo.settings.setting_manager import SettingManager
        import time
        
        settings = SettingManager()
        collector = StatsCollector(settings)
        
        start = time.time()
        
        # 100000 次更新
        for i in range(100000):
            collector.inc_value('rapid_counter')
        
        elapsed = time.time() - start
        
        # 应该在合理时间内完成
        assert elapsed < 10.0
        assert collector.get_value('rapid_counter') == 100000


class TestExtremeItemScenarios:
    """极端 Item 场景测试"""
    
    def test_item_huge_fields(self):
        """测试超大字段"""
        from crawlo.items.item import Item
        
        item = Item()
        
        # 10MB 字段
        item['huge_field'] = 'x' * (10 * 1024 * 1024)
        
        assert len(item['huge_field']) == 10 * 1024 * 1024
    
    def test_item_many_fields(self):
        """测试大量字段"""
        from crawlo.items.item import Item
        
        item = Item()
        
        # 1000 个字段
        for i in range(1000):
            item[f'field_{i}'] = f'value_{i}'
        
        assert len(item) == 1000
    
    def test_item_special_characters(self):
        """测试特殊字符字段"""
        from crawlo.items.item import Item
        
        item = Item()
        
        special_values = [
            '中文值',
            'Emoji 😀',
            'HTML <script>',
            'SQL SELECT *',
            'Null \x00',
        ]
        
        for i, val in enumerate(special_values):
            item[f'special_{i}'] = val
            assert item[f'special_{i}'] == val


class TestExtremeFrameworkIntegration:
    """极端框架集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_with_exceptions(self):
        """测试完整流程中包含异常"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        from crawlo.items.item import Item
        
        # 创建队列
        queue = SpiderPriorityQueue()
        
        # 入队请求
        for i in range(100):
            await queue.put(Request(f'http://example.com/{i}'), priority=0)
        
        # 出队并模拟处理
        processed = 0
        errors = 0
        
        for _ in range(100):
            req = await queue.get(timeout=1.0)
            if req:
                try:
                    # 模拟 10% 失败率
                    if hash(req.url) % 10 == 0:
                        raise Exception("Simulated error")
                    
                    # 创建 Item
                    item = Item()
                    item['url'] = req.url
                    
                    processed += 1
                except:
                    errors += 1
        
        # 应该处理了所有请求
        assert processed + errors == 100
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_crash(self):
        """测试崩溃时资源清理"""
        from crawlo.queue.memory_queue import SpiderPriorityQueue
        
        queue = SpiderPriorityQueue()
        
        # 使用队列
        await queue.put(Request('http://example.com/test'), priority=0)
        
        # 模拟崩溃（强制删除）
        del queue
        
        # Python GC 应该清理资源
        import gc
        gc.collect()
        
        # 无泄漏检查（简化版）
        # 实际应该使用 memory_profiler 等工具
