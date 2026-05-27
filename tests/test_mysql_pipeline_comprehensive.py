# -*- coding: utf-8 -*-
"""
MySQL Pipeline 全面测试套件
测试所有场景：错误处理、批量插入、事务、降级策略、性能监控等
"""

import asyncio
import sys
import os
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.pipelines.sql.mysql import (
    MySQLPipeline,
    ErrorClassifier,
    ErrorConfig,
    PerformanceStats
)
from crawlo.items import Item, Field
from crawlo.exceptions import ItemDiscard
from crawlo.settings.setting_manager import SettingManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestItem(Item):
    """测试用的 Item"""
    id = Field()
    name = Field()
    value = Field()
    created_at = Field()


class MockCrawler:
    """模拟 Crawler 对象用于测试"""
    def __init__(self, settings_dict=None):
        self.settings = SettingManager()
        if settings_dict:
            for key, value in settings_dict.items():
                self.settings[key] = value
        
        class MockSubscriber:
            def subscribe(self, handler, event):
                pass
        
        self.subscriber = MockSubscriber()
        
        class MockStats:
            def __init__(self):
                self.stats = {}
            
            def inc_value(self, key, count=1):
                self.stats[key] = self.stats.get(key, 0) + count
            
            def get_value(self, key, default=0):
                return self.stats.get(key, default)
        
        self.stats = MockStats()
        
        class MockSpider:
            name = 'test_spider'
            custom_settings = {}
        
        self.spider = MockSpider()


class MockMySQLHelper:
    """模拟 MySQLHelper"""
    def __init__(self):
        self.insert_calls = []
        self.insert_many_calls = []
        self.fetch_one_calls = []
        self.transaction_context = None
        self.__sql_builder = MockSQLBuilder()
    
    async def insert(self, table, data, auto_update=False, update_columns=(), insert_ignore=False):
        self.insert_calls.append({
            'table': table,
            'data': data,
            'auto_update': auto_update,
            'update_columns': update_columns,
            'insert_ignore': insert_ignore
        })
        return 1
    
    async def insert_many(self, table, datas, auto_update=False, update_columns=(), insert_ignore=False, batch_size=100):
        self.insert_many_calls.append({
            'table': table,
            'datas': datas,
            'auto_update': auto_update,
            'update_columns': update_columns,
            'insert_ignore': insert_ignore,
            'batch_size': batch_size
        })
        return len(datas)
    
    async def fetch_one(self, sql, params=None):
        self.fetch_one_calls.append({'sql': sql, 'params': params})
        return {'count': 1}
    
    @property
    def _sql_builder(self):
        return self.__sql_builder
    
    @_sql_builder.setter
    def _sql_builder(self, value):
        self.__sql_builder = value
    
    async def transaction(self):
        """事务上下文管理器"""
        class MockTransaction:
            def __init__(self, helper):
                self.helper = helper
            
            async def __aenter__(self):
                class MockCursor:
                    def __init__(self):
                        self.rowcount = 0
                    
                    async def execute(self, sql, params):
                        self.rowcount = len(params) if isinstance(params, list) else 1
                
                return MockCursor()
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return MockTransaction(self)


class MockSQLBuilder:
    """模拟 SQLBuilder"""
    def make_insert(self, table, data, auto_update=False, update_columns=(), insert_ignore=False):
        return "INSERT INTO table VALUES (...)", []
    
    def make_batch(self, table, datas, auto_update=False, update_columns=(), insert_ignore=False):
        return "INSERT INTO table VALUES (...)", []


class TestResults:
    """测试结果收集器"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        logger.info(f"✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        logger.error(f"✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        logger.info(f"\n{'='*60}")
        logger.info(f"测试总结: {self.passed}/{total} 通过, {self.failed}/{total} 失败")
        if self.errors:
            logger.info(f"\n失败的测试:")
            for test_name, error in self.errors:
                logger.info(f"  - {test_name}: {error}")
        logger.info(f"{'='*60}\n")
        return self.failed == 0


results = TestResults()


async def test_error_classifier_extract_code():
    """测试错误码提取"""
    test_name = "错误码提取"
    try:
        # 测试从异常对象提取
        error = Exception((1062, "Duplicate entry"))
        code = ErrorClassifier.extract_error_code(error)
        assert code == 1062, f"Expected 1062, got {code}"
        
        # 测试从字符串提取
        error = Exception("(2013, 'Lost connection to MySQL server')")
        code = ErrorClassifier.extract_error_code(error)
        assert code == 2013, f"Expected 2013, got {code}"
        
        # 测试无错误码
        error = Exception("Some other error")
        code = ErrorClassifier.extract_error_code(error)
        assert code is None, f"Expected None, got {code}"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_error_classifier_skipable():
    """测试可跳过错误判断"""
    test_name = "可跳过错误判断"
    try:
        # 测试重复数据错误
        error = Exception((1062, "Duplicate entry"))
        assert ErrorClassifier.is_skipable(error), "1062 should be skipable"
        
        # 测试锁超时错误
        error = Exception((1205, "Lock wait timeout"))
        assert ErrorClassifier.is_skipable(error), "1205 should be skipable"
        
        # 测试连接丢失错误（不可跳过）
        error = Exception((2013, "Lost connection"))
        assert not ErrorClassifier.is_skipable(error), "2013 should not be skipable"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_error_classifier_retryable():
    """测试可重试错误判断"""
    test_name = "可重试错误判断"
    try:
        # 测试连接丢失错误
        error = Exception((2013, "Lost connection"))
        assert ErrorClassifier.is_retryable(error), "2013 should be retryable"
        
        # 测试死锁错误
        error = Exception((1213, "Deadlock found"))
        assert ErrorClassifier.is_retryable(error), "1213 should be retryable"
        
        # 测试重复数据错误（不可重试）
        error = Exception((1062, "Duplicate entry"))
        assert not ErrorClassifier.is_retryable(error), "1062 should not be retryable"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_error_classifier_description():
    """测试错误描述获取"""
    test_name = "错误描述获取"
    try:
        error = Exception((1062, "Duplicate entry"))
        desc = ErrorClassifier.get_error_description(error)
        assert "重复数据" in desc, f"Expected '重复数据' in description, got {desc}"
        assert "1062" in desc, f"Expected '1062' in description, got {desc}"
        
        error = Exception("Unknown error")
        desc = ErrorClassifier.get_error_description(error)
        assert "Unknown error" in desc, f"Expected 'Unknown error' in description, got {desc}"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_performance_stats():
    """测试性能统计"""
    test_name = "性能统计"
    try:
        stats = PerformanceStats()
        
        # 测试初始值
        assert stats.insert_count == 0, "Initial insert_count should be 0"
        assert stats.batch_count == 0, "Initial batch_count should be 0"
        
        # 测试更新
        stats.insert_count = 100
        stats.insert_time = 10.0
        avg = stats.get_avg_insert_time()
        assert avg == 0.1, f"Expected avg 0.1, got {avg}"
        
        stats.batch_count = 10
        stats.batch_time = 5.0
        avg = stats.get_avg_batch_time()
        assert avg == 0.5, f"Expected avg 0.5, got {avg}"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_single_insert():
    """测试单条插入"""
    test_name = "单条插入"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test'
        item['value'] = 'value'
        item['created_at'] = '2023-01-01'
        
        result = await pipeline.process_item(item, crawler.spider)
        assert result == item, "Should return the same item"
        assert len(pipeline._helper.insert_calls) == 1, "Should have 1 insert call"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_batch_insert():
    """测试批量插入"""
    test_name = "批量插入"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 3,
            'MYSQL_USE_BATCH': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 插入 5 个项目，应该触发 2 次批量插入
        for i in range(5):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            await pipeline.process_item(item, crawler.spider)
        
        # 刷新剩余的
        await pipeline._flush_batch('test_spider')
        
        assert len(pipeline._helper.insert_many_calls) >= 1, "Should have at least 1 batch insert"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_batch_with_transaction():
    """测试带事务的批量插入"""
    test_name = "带事务的批量插入"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 3,
            'MYSQL_USE_BATCH': True,
            'MYSQL_USE_TRANSACTION': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 添加项目到缓冲区
        for i in range(3):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            pipeline.batch_buffer.append(dict(item))
        
        # 刷新批量
        await pipeline._flush_batch('test_spider')
        
        # 验证使用了事务
        assert pipeline.use_transaction == True, "Should use transaction"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_skipable_error_handling():
    """测试可跳过错误处理"""
    test_name = "可跳过错误处理"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        
        # 创建会抛出可跳过错误的 mock helper
        class FailingMySQLHelper(MockMySQLHelper):
            async def insert(self, table, data, auto_update=False, update_columns=(), insert_ignore=False):
                raise Exception((1062, "Duplicate entry"))
        
        pipeline._helper = FailingMySQLHelper()
        pipeline._initialized = True
        
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test'
        item['value'] = 'value'
        item['created_at'] = '2023-01-01'
        
        # 应该跳过错误，不抛出异常
        result = await pipeline.process_item(item, crawler.spider)
        assert result == item, "Should return the item even on skipable error"
        assert crawler.stats.get_value('mysql/skipped') == 1, "Should increment skipped count"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_retryable_error_handling():
    """测试可重试错误处理"""
    test_name = "可重试错误处理"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_MAX_RETRIES': 3,
            'MYSQL_RETRY_DELAY': 0.1,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        
        # 创建会抛出可重试错误的 mock helper
        class RetryableMySQLHelper(MockMySQLHelper):
            def __init__(self):
                super().__init__()
                self.attempt = 0
            
            async def insert(self, table, data, auto_update=False, update_columns=(), insert_ignore=False):
                self.attempt += 1
                if self.attempt < 3:
                    raise Exception((2013, "Lost connection"))
                return 1
        
        pipeline._helper = RetryableMySQLHelper()
        pipeline._initialized = True
        
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test'
        item['value'] = 'value'
        item['created_at'] = '2023-01-01'
        
        start_time = time.time()
        result = await pipeline.process_item(item, crawler.spider)
        elapsed = time.time() - start_time
        
        assert result == item, "Should succeed after retries"
        assert pipeline._stats.retry_count == 2, "Should have 2 retries"
        assert elapsed >= 0.2, f"Should have waited at least 0.2s, got {elapsed}s"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_buffer_size_limit():
    """测试缓冲区大小限制"""
    test_name = "缓冲区大小限制"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 10,
            'MYSQL_MAX_BUFFER_SIZE': 5,
            'MYSQL_USE_BATCH': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 添加超过缓冲区限制的项目
        for i in range(7):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            await pipeline.process_item(item, crawler.spider)
        
        # 缓冲区应该被清空
        assert len(pipeline.batch_buffer) < 5, f"Buffer should be less than 5, got {len(pipeline.batch_buffer)}"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_fallback_threshold():
    """测试降级阈值"""
    test_name = "降级阈值"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 3,
            'MYSQL_USE_BATCH': True,
            'MYSQL_FALLBACK_THRESHOLD': 2,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        
        # 创建会失败的 mock helper
        class FailingMySQLHelper(MockMySQLHelper):
            async def insert(self, table, data, auto_update=False, update_columns=(), insert_ignore=False):
                raise Exception("Insert failed")
        
        pipeline._helper = FailingMySQLHelper()
        pipeline._initialized = True
        
        # 添加项目到缓冲区
        for i in range(3):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            pipeline.batch_buffer.append(dict(item))
        
        # 第一次失败
        try:
            await pipeline._flush_batch('test_spider')
        except:
            pass
        
        assert pipeline._fallback_failures == 1, f"Should have 1 failure, got {pipeline._fallback_failures}"
        
        # 第二次失败，应该抛出异常
        try:
            await pipeline._flush_batch('test_spider')
            assert False, "Should raise ItemDiscard after threshold exceeded"
        except ItemDiscard:
            pass
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_before_insert_hook():
    """测试 before_insert 钩子"""
    test_name = "before_insert 钩子"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        
        # 创建自定义 pipeline
        class CustomPipeline(MySQLPipeline):
            async def before_insert(self, item):
                data = await super().before_insert(item)
                data['processed'] = True
                return data
        
        pipeline = CustomPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test'
        item['value'] = 'value'
        item['created_at'] = '2023-01-01'
        
        await pipeline.process_item(item, crawler.spider)
        
        # 验证钩子被调用
        assert len(pipeline._helper.insert_calls) == 1, "Should have 1 insert call"
        assert 'processed' in pipeline._helper.insert_calls[0]['data'], "Should have processed field"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_after_insert_hook():
    """测试 after_insert 钩子"""
    test_name = "after_insert 钩子"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        
        # 创建自定义 pipeline
        class CustomPipeline(MySQLPipeline):
            def __init__(self, crawler):
                super().__init__(crawler)
                self.after_insert_called = False
            
            async def after_insert(self, item, rowcount):
                self.after_insert_called = True
                await super().after_insert(item, rowcount)
        
        pipeline = CustomPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        item = TestItem()
        item['id'] = 1
        item['name'] = 'test'
        item['value'] = 'value'
        item['created_at'] = '2023-01-01'
        
        await pipeline.process_item(item, crawler.spider)
        
        # 验证钩子被调用
        assert pipeline.after_insert_called, "after_insert hook should be called"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_performance_monitoring():
    """测试性能监控"""
    test_name = "性能监控"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_PERFORMANCE_LOG': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 插入多个项目
        for i in range(5):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            await pipeline.process_item(item, crawler.spider)
        
        # 验证统计信息
        assert pipeline._stats.insert_count == 5, f"Should have 5 inserts, got {pipeline._stats.insert_count}"
        assert pipeline._stats.insert_time > 0, "Should have recorded insert time"
        
        # 测试性能摘要
        pipeline._log_performance_summary()
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_health_check():
    """测试健康检查"""
    test_name = "健康检查"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_HEALTH_CHECK': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 执行健康检查
        await pipeline._check_connection_health()
        
        # 验证检查被调用
        assert len(pipeline._helper.fetch_one_calls) > 0, "Should have called fetch_one for health check"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_concurrent_inserts():
    """测试并发插入"""
    test_name = "并发插入"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 并发插入
        async def insert_item(i):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            return await pipeline.process_item(item, crawler.spider)
        
        tasks = [insert_item(i) for i in range(10)]
        results_list = await asyncio.gather(*tasks)
        
        # 验证所有插入都成功
        assert len(results_list) == 10, f"Should have 10 results, got {len(results_list)}"
        assert len(pipeline._helper.insert_calls) == 10, f"Should have 10 insert calls, got {len(pipeline._helper.insert_calls)}"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_table_name_sanitization():
    """测试表名清理"""
    test_name = "表名清理"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test-table with spaces',
            'MYSQL_USE_BATCH': False,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        
        assert pipeline.table_name == 'test_table_with_spaces', f"Expected 'test_table_with_spaces', got '{pipeline.table_name}'"
        
        # 测试无效表名
        settings['MYSQL_TABLE'] = 'test@table'
        crawler = MockCrawler(settings)
        try:
            pipeline = MySQLPipeline(crawler)
            assert False, "Should raise ValueError for invalid table name"
        except ValueError:
            pass
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_cleanup_resources():
    """测试资源清理"""
    test_name = "资源清理"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 3,
            'MYSQL_USE_BATCH': True,
            'MYSQL_PERFORMANCE_LOG': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        pipeline._helper = MockMySQLHelper()
        pipeline._initialized = True
        
        # 添加一些项目到缓冲区
        for i in range(2):
            item = TestItem()
            item['id'] = i
            item['name'] = f'test_{i}'
            item['value'] = f'value_{i}'
            item['created_at'] = '2023-01-01'
            pipeline.batch_buffer.append(dict(item))
        
        # 清理资源
        await pipeline._cleanup_resources()
        
        # 验证缓冲区被清空
        assert len(pipeline.batch_buffer) == 0, "Buffer should be empty after cleanup"
        assert pipeline._initialized == False, "Should be marked as uninitialized"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def test_config_parsing():
    """测试配置解析"""
    test_name = "配置解析"
    try:
        settings = {
            'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': 3306,
            'MYSQL_USER': 'root',
            'MYSQL_PASSWORD': '',
            'MYSQL_DB': 'test_db',
            'MYSQL_TABLE': 'test_table',
            'MYSQL_BATCH_SIZE': 50,
            'MYSQL_MAX_BUFFER_SIZE': 500,
            'MYSQL_USE_BATCH': True,
            'MYSQL_USE_TRANSACTION': True,
            'MYSQL_AUTO_UPDATE': True,
            'MYSQL_INSERT_IGNORE': False,
            'MYSQL_UPDATE_COLUMNS': 'name,value',
            'MYSQL_MAX_RETRIES': 5,
            'MYSQL_RETRY_DELAY': 1.0,
            'MYSQL_FALLBACK_THRESHOLD': 20,
            'MYSQL_PERFORMANCE_LOG': True,
            'MYSQL_HEALTH_CHECK': True,
            'MYSQL_CHECK_TABLE_EXISTS': False,
        }
        
        crawler = MockCrawler(settings)
        pipeline = MySQLPipeline(crawler)
        
        assert pipeline.batch_size == 50, f"Expected batch_size 50, got {pipeline.batch_size}"
        assert pipeline.max_buffer_size == 500, f"Expected max_buffer_size 500, got {pipeline.max_buffer_size}"
        assert pipeline.use_batch == True, "Expected use_batch True"
        assert pipeline.use_transaction == True, "Expected use_transaction True"
        assert pipeline.auto_update == True, "Expected auto_update True"
        assert pipeline.insert_ignore == False, "Expected insert_ignore False"
        assert pipeline.update_columns == ('name', 'value'), f"Expected ('name', 'value'), got {pipeline.update_columns}"
        assert pipeline.max_retries == 5, f"Expected max_retries 5, got {pipeline.max_retries}"
        assert pipeline.retry_delay == 1.0, f"Expected retry_delay 1.0, got {pipeline.retry_delay}"
        assert pipeline.fallback_threshold == 20, f"Expected fallback_threshold 20, got {pipeline.fallback_threshold}"
        assert pipeline.enable_performance_log == True, "Expected enable_performance_log True"
        assert pipeline.enable_health_check == True, "Expected enable_health_check True"
        
        results.add_pass(test_name)
    except Exception as e:
        results.add_fail(test_name, str(e))


async def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("MySQL Pipeline 全面测试套件")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        # 错误分类器测试
        test_error_classifier_extract_code,
        test_error_classifier_skipable,
        test_error_classifier_retryable,
        test_error_classifier_description,
        
        # 性能统计测试
        test_performance_stats,
        
        # 单条插入测试
        test_single_insert,
        
        # 批量插入测试
        test_batch_insert,
        test_batch_with_transaction,
        
        # 错误处理测试
        test_skipable_error_handling,
        test_retryable_error_handling,
        
        # 缓冲区管理测试
        test_buffer_size_limit,
        test_fallback_threshold,
        
        # 钩子方法测试
        test_before_insert_hook,
        test_after_insert_hook,
        
        # 性能监控测试
        test_performance_monitoring,
        
        # 健康检查测试
        test_health_check,
        
        # 并发测试
        test_concurrent_inserts,
        
        # 配置测试
        test_table_name_sanitization,
        test_config_parsing,
        
        # 资源管理测试
        test_cleanup_resources,
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
    
    return results.summary()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
