"""测试 GenericSQLPipeline 基类 + MySQLPipeline 重构"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.pipelines.generic_sql import GenericSQLPipeline
from crawlo.pipelines.sql.mysql import MySQLPipeline
from crawlo.pipelines import GenericSQLPipeline as GSP


# ── Mock helpers ──

class MockSettings(dict):
    def get_int(self, key, default=0):
        return int(self.get(key, default))
    def get_bool(self, key, default=False):
        return bool(self.get(key, default))
    def get_float(self, key, default=0.0):
        return float(self.get(key, default))

class MockSpider:
    name = 'test_spider'
    custom_settings = {}

class MockStats:
    def inc_value(self, key, count=1):
        pass

class MockCrawler:
    def __init__(self, settings=None):
        self.settings = settings or MockSettings({'MYSQL_TABLE': 'test_table'})
        self.spider = MockSpider()
        self.stats = MockStats()


# ── Test: GenericSQLPipeline 核心逻辑 ──

async def test_config_parsing():
    """测试配置解析"""
    settings = MockSettings({
        'MYSQL_TABLE': 'my_table',
        'MYSQL_BATCH_SIZE': 50,
        'MYSQL_USE_BATCH': True,
        'MYSQL_INSERT_IGNORE': True,
        'MYSQL_EXECUTE_MAX_RETRIES': 5,
    })
    crawler = MockCrawler(settings)

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'

        async def _initialize_pool(self): pass
        async def _create_helper(self): pass
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data): return 1
        async def _do_batch_insert(self, batch): return len(batch)
        async def _do_batch_insert_no_tx(self, batch): return len(batch)
        async def _check_table_exists(self): pass

    p = TestPipeline(crawler)
    # 默认 settings 下 table_name 继承自 MYSQL_TABLE（因为 TEST_TABLE 不存在）
    assert p.batch_size == 100  # 默认值
    assert p.max_retries == 3   # 默认值
    assert p._PREFIX == 'TEST'
    print("[PASS] config parsing with defaults")


async def test_sanitize_table_name():
    """测试表名清理"""
    assert GenericSQLPipeline._sanitize_table_name('my table') == 'my_table'
    assert GenericSQLPipeline._sanitize_table_name('hello-world') == 'hello_world'
    try:
        GenericSQLPipeline._sanitize_table_name('')
        assert False, "Should raise"
    except ValueError:
        pass
    print("[PASS] table name sanitization")


async def test_parse_columns():
    """测试列配置解析"""
    assert GenericSQLPipeline._parse_columns(()) == ()
    assert GenericSQLPipeline._parse_columns(None) == () or not GenericSQLPipeline._parse_columns(None)
    assert GenericSQLPipeline._parse_columns(['a', 'b']) == ('a', 'b')
    assert GenericSQLPipeline._parse_columns('single') == ('single',)
    print("[PASS] column parsing")


async def test_single_insert_flow():
    """测试单条插入流程"""
    settings = MockSettings({'MYSQL_TABLE': 'test'})
    crawler = MockCrawler(settings)

    insert_calls = []

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'
        async def _initialize_pool(self): self.pool = MagicMock()
        async def _create_helper(self): self._helper = MagicMock()
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data):
            insert_calls.append(data)
            return 1
        async def _do_batch_insert(self, batch): return len(batch)
        async def _do_batch_insert_no_tx(self, batch): return len(batch)
        async def _check_table_exists(self): pass

    p = TestPipeline(crawler)
    p._initialized = True
    p.pool = MagicMock()

    from crawlo.items import Item
    item = Item(url='http://test', name='test', value=123)
    result = await p.process_item(item, MockSpider())
    assert result is item
    assert len(insert_calls) == 1
    assert insert_calls[0]['name'] == 'test'
    assert insert_calls[0]['value'] == 123
    print("[PASS] single insert flow")


async def test_batch_insert_flow():
    """测试批量插入流程"""
    settings = MockSettings({
        'TEST_TABLE': 'batch_test',
        'TEST_BATCH_SIZE': 3,
        'TEST_USE_BATCH': True,
    })
    crawler = MockCrawler(settings)

    batch_inserted = []

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'
        async def _initialize_pool(self): self.pool = MagicMock()
        async def _create_helper(self): self._helper = MagicMock()
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data): return 1
        async def _do_batch_insert(self, batch):
            batch_inserted.append(len(batch))
            return len(batch)
        async def _do_batch_insert_no_tx(self, batch):
            batch_inserted.append(len(batch))
            return len(batch)
        async def _check_table_exists(self): pass

    p = TestPipeline(crawler)
    p._initialized = True
    p.pool = MagicMock()

    from crawlo.items import Item
    for i in range(3):
        await p.process_item(Item(url=f'http://test/{i}', id=i), MockSpider())
    assert len(batch_inserted) == 1 and batch_inserted[0] == 3
    print("[PASS] batch insert triggers at batch_size=3")


async def test_retry_logic():
    """测试重试逻辑"""
    settings = MockSettings({
        'TEST_TABLE': 'retry_test',
        'TEST_EXECUTE_MAX_RETRIES': 3,
        'TEST_EXECUTE_RETRY_DELAY': 0.01,
    })
    crawler = MockCrawler(settings)

    attempts = []

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'
        async def _initialize_pool(self): self.pool = MagicMock()
        async def _create_helper(self): self._helper = MagicMock()
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data):
            attempts.append(1)
            if len(attempts) < 3:
                # 使用 MySQL 错误码 2006（连接丢失，可重试）
                raise OSError(2006, "MySQL server has gone away")
            return 1
        async def _do_batch_insert(self, batch): return len(batch)
        async def _do_batch_insert_no_tx(self, batch): return len(batch)
        async def _check_table_exists(self): pass

    p = TestPipeline(crawler)
    p._initialized = True
    p.pool = MagicMock()

    from crawlo.items import Item
    result = await p._insert_single(Item(url='http://test', id=1))
    assert len(attempts) == 3
    print("[PASS] retry logic: 2 fail + 1 success = 3 attempts")


async def test_cleanup_flush():
    """测试清理时刷新残留缓冲"""
    settings = MockSettings({
        'TEST_TABLE': 'cleanup_test',
        'TEST_BATCH_SIZE': 10,
        'TEST_USE_BATCH': True,
    })
    crawler = MockCrawler(settings)
    flush_called = []

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'
        async def _initialize_pool(self): self.pool = MagicMock()
        async def _create_helper(self): self._helper = MagicMock()
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data): return 1
        async def _do_batch_insert(self, batch):
            flush_called.append(len(batch))
            return len(batch)
        async def _do_batch_insert_no_tx(self, batch):
            flush_called.append(len(batch))
            return len(batch)
        async def _check_table_exists(self): pass

    p = TestPipeline(crawler)
    p._initialized = True
    p.pool = MagicMock()

    from crawlo.items import Item
    await p.process_item(Item(url='http://test/1', id=1), MockSpider())
    await p.process_item(Item(url='http://test/2', id=2), MockSpider())

    await p._cleanup_resources()
    assert len(flush_called) == 1 and flush_called[0] == 2
    print("[PASS] cleanup flushes remaining buffer")


async def test_config_prefix():
    """测试不同数据库前缀读取配置"""
    settings = MockSettings({
        'MYSQL_TABLE': 'mysql_table',
        'ORACLE_TABLE': 'oracle_table',
    })
    crawler = MockCrawler(settings)

    class OracleStylePipeline(GenericSQLPipeline):
        _PREFIX = 'ORACLE'
        async def _initialize_pool(self): pass
        async def _create_helper(self): pass
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data): pass
        async def _do_batch_insert(self, batch): pass
        async def _do_batch_insert_no_tx(self, batch): pass
        async def _check_table_exists(self): pass

    p = OracleStylePipeline(crawler)
    assert p._PREFIX == 'ORACLE'
    # ORACLE_TABLE 配置了 → 应使用 oracle_table
    assert p.table_name == 'oracle_table'
    print("[PASS] config prefix isolation")


async def test_hooks():
    """测试 before/after_insert 钩子"""
    settings = MockSettings({'TEST_TABLE': 'hook_test'})
    crawler = MockCrawler(settings)

    hook_log = []

    class TestPipeline(GenericSQLPipeline):
        _PREFIX = 'TEST'
        async def _initialize_pool(self): self.pool = MagicMock()
        async def _create_helper(self): self._helper = MagicMock()
        async def _close_pool(self, pool): pass
        async def _do_insert(self, data): return 1
        async def _do_batch_insert(self, batch): return len(batch)
        async def _do_batch_insert_no_tx(self, batch): return len(batch)
        async def _check_table_exists(self): pass
        async def _before_insert(self, item):
            hook_log.append('before')
            data = dict(item)
            data['processed'] = True
            return data
        async def _after_insert(self, item, rowcount):
            hook_log.append(f'after:{rowcount}')

    p = TestPipeline(crawler)
    p._initialized = True
    p.pool = MagicMock()

    from crawlo.items import Item
    await p._insert_single(Item(url='http://test', id=1))
    assert hook_log == ['before', 'after:1']
    print("[PASS] before/after insert hooks")


async def main():
    print(f"Python {sys.version}")
    print("=" * 60)
    print("Testing GenericSQLPipeline + MySQLPipeline refactor")
    print("=" * 60)

    tests = [
        test_config_parsing,
        test_sanitize_table_name,
        test_parse_columns,
        test_single_insert_flow,
        test_batch_insert_flow,
        test_retry_logic,
        test_cleanup_flush,
        test_config_prefix,
        test_hooks,
    ]

    passed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{len(tests)} passed")
    print(f"{'=' * 60}")
    return passed == len(tests)


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
